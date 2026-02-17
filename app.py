from flask import Flask, request, render_template, jsonify
import os
import time
import threading
from ocr_service import extract_text_from_file
from text_utils import clean_text, correct_spelling
from pdf_parser import parse_exam_file
from scoring import SemanticScorer
from question_paper import parse_question_paper_file

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

scorer = SemanticScorer()

# --- Global State ---
# Using globals for simplicity (single-user app).
# For multi-user, you'd use a task queue like Celery.
progress = {
    "status": "idle",    # idle | processing | done | error
    "message": "",
    "step": 0,
    "total_steps": 6
}

# Stores the latest result so /results can render it after processing
latest_result = {
    "exam_data": None,
    "error": None
}


def update_progress(step, message):
    """Update the global progress state."""
    global progress
    progress["step"] = step
    progress["message"] = message
    progress["status"] = "processing"
    print(f"[Progress {step}/{progress['total_steps']}] {message}")


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/progress")
def get_progress():
    """Returns current processing progress as JSON."""
    return jsonify(progress)


@app.route("/results")
def results():
    """Renders the result page. Called by the client after processing is done."""
    if latest_result["error"]:
        err_msg = latest_result["error"]
        return err_msg, 400
    
    if latest_result["exam_data"]:
        return render_template("result.html", exam_data=latest_result["exam_data"])
    
    return "No results available. Please submit an evaluation first.", 400


@app.route("/evaluate", methods=["POST"])
def evaluate():
    """
    Accepts file uploads, saves them, starts background processing,
    and returns immediately with 202 Accepted.
    The client polls /progress and then navigates to /results when done.
    """
    global progress, latest_result
    print("\n" + "="*50)
    print("EVALUATE ROUTE CALLED")
    print("="*50 + "\n")
    
    if "student_file" not in request.files or "model_file" not in request.files:
        print("ERROR: Missing files in request")
        return jsonify({"error": "Please upload Student Answer and Model Answer files."}), 400

    student_file = request.files["student_file"]
    model_file = request.files["model_file"]
    question_file = request.files.get("question_file")  # Optional but recommended
    
    print(f"Student file: {student_file.filename}")
    print(f"Model file: {model_file.filename}")
    print(f"Question file: {question_file.filename if question_file else 'None'}")

    if student_file.filename == "" or model_file.filename == "":
        print("ERROR: Empty filename")
        return jsonify({"error": "No file selected"}), 400

    # Save Files
    update_progress(1, "Saving uploaded files...")
    s_path = os.path.join(UPLOAD_FOLDER, "student_" + student_file.filename)
    m_path = os.path.join(UPLOAD_FOLDER, "model_" + model_file.filename)
    
    student_file.save(s_path)
    model_file.save(m_path)
    
    q_path = None
    if question_file and question_file.filename != "":
        q_path = os.path.join(UPLOAD_FOLDER, "question_" + question_file.filename)
        question_file.save(q_path)

    # Reset result holder
    latest_result["exam_data"] = None
    latest_result["error"] = None

    # --- Run processing in a background thread ---
    def process_evaluation():
        global progress, latest_result
        q_schema = {}
        overall_start = time.time()
        try:
            # 0. Question Paper OCR (if provided)
            if q_path:
                update_progress(2, "Reading question paper with OCR... (this may take a minute)")
                step_start = time.time()
                q_schema = parse_question_paper_file(q_path)
                print(f"Question Paper Schema: {q_schema} ({time.time()-step_start:.1f}s)")

            # 1. OCR (Extract raw text)
            update_progress(3, "Running OCR on student answer... (this may take a few minutes)")
            step_start = time.time()
            student_raw = extract_text_from_file(s_path)
            print(f"Student OCR completed in {time.time()-step_start:.1f}s")
            
            update_progress(4, "Running OCR on model answer...")
            step_start = time.time()
            model_raw = extract_text_from_file(m_path)
            print(f"Model OCR completed in {time.time()-step_start:.1f}s")
            
            if not student_raw or not model_raw:
                which = "student" if not student_raw else "model"
                latest_result["error"] = f"OCR failed to read the {which} answer file. Ensure it is clear and not corrupted."
                progress["status"] = "error"
                progress["message"] = latest_result["error"]
                return

            # 2. Parsing (Split into Q1, Q2, etc.)
            update_progress(5, "Processing text and correcting OCR errors...")
            student_segments = parse_exam_file(student_raw)
            model_segments = parse_exam_file(model_raw)
            
            if not model_segments:
                latest_result["error"] = "Could not detect Question Numbers (e.g., '1.', 'Q1') in the Model Answer PDF. Please ensure standard formatting."
                progress["status"] = "error"
                progress["message"] = latest_result["error"]
                return

            # Clean individual segments
            all_model_text = ""
            for k in model_segments:
                m_clean = clean_text(model_segments[k])
                model_segments[k] = m_clean
                all_model_text += " " + m_clean
                
            # Build vocabulary from model answer for context-aware correction
            model_vocab = set(all_model_text.split())
            print(f"Built Model Vocabulary: {len(model_vocab)} unique words.")

            # Process Student Answer with Spell Correction
            for k in student_segments:
                s_clean = clean_text(student_segments[k])
                s_corrected = correct_spelling(s_clean, custom_dictionary=model_vocab)
                student_segments[k] = s_corrected
                
                if len(s_clean) > 0:
                    print(f"Q{k} Original: {s_clean[:30]}... -> Corrected: {s_corrected[:30]}...")

            # 3. Scoring
            update_progress(6, "Scoring answers with semantic analysis...")
            print("\n--- DEBUG: Parsed Student Data ---")
            for k, v in student_segments.items():
                preview = v[:50].replace('\n', ' ') + "..."
                print(f"Q{k}: {preview}")
            print("------------------------------------\n")

            step_start = time.time()
            exam_results = scorer.evaluate_exam(student_segments, model_segments, question_schema=q_schema)
            print(f"Scoring completed in {time.time()-step_start:.1f}s")
            
            total_time = time.time() - overall_start
            print(f"\n=== TOTAL PROCESSING TIME: {total_time:.1f}s ===")
            
            # Store result and mark done
            latest_result["exam_data"] = exam_results
            progress["status"] = "done"
            progress["message"] = "Complete!"

        except Exception as e:
            total_time = time.time() - overall_start
            print(f"Error in processing thread after {total_time:.1f}s: {e}")
            import traceback
            traceback.print_exc()
            latest_result["error"] = f"An error occurred during evaluation: {e}"
            progress["status"] = "error"
            progress["message"] = str(e)

    # Start processing in background -- return immediately
    worker = threading.Thread(target=process_evaluation, daemon=True)
    worker.start()
    
    # Return 202 Accepted immediately -- client will poll /progress
    return jsonify({"status": "accepted", "message": "Processing started"}), 202


if __name__ == "__main__":
    app.run(debug=True, threaded=True)
