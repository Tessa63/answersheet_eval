from flask import Flask, request, render_template, jsonify
import os
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

# --- Global Progress State ---
progress = {
    "status": "idle",    # idle | processing | done | error
    "message": "",
    "step": 0,
    "total_steps": 6
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


@app.route("/evaluate", methods=["POST"])
def evaluate():
    global progress
    print("\n" + "="*50)
    print("EVALUATE ROUTE CALLED")
    print("="*50 + "\n")
    
    if "student_file" not in request.files or "model_file" not in request.files:
        print("ERROR: Missing files in request")
        return "Please upload Student Answer and Model Answer files.", 400

    student_file = request.files["student_file"]
    model_file = request.files["model_file"]
    question_file = request.files.get("question_file") # Optional but recommended
    
    print(f"Student file: {student_file.filename}")
    print(f"Model file: {model_file.filename}")
    print(f"Question file: {question_file.filename if question_file else 'None'}")

    if student_file.filename == "" or model_file.filename == "":
        print("ERROR: Empty filename")
        return "No file selected", 400

    # Save Files
    update_progress(1, "Saving uploaded files...")
    s_path = os.path.join(UPLOAD_FOLDER, "student_" + student_file.filename)
    m_path = os.path.join(UPLOAD_FOLDER, "model_" + model_file.filename)
    
    student_file.save(s_path)
    model_file.save(m_path)
    
    q_schema = {}
    if question_file and question_file.filename != "":
        q_path = os.path.join(UPLOAD_FOLDER, "question_" + question_file.filename)
        question_file.save(q_path)
        update_progress(2, "Reading question paper with OCR... (this may take a minute)")
        q_schema = parse_question_paper_file(q_path)
        print("Question Paper Schema:", q_schema)

    # --- Run heavy processing in a thread with timeout ---
    result_holder = {"result": None, "error": None}

    def process_evaluation():
        try:
            # 1. OCR (Extract raw text)
            update_progress(3, "Running OCR on student answer... (this may take a minute)")
            student_raw = extract_text_from_file(s_path)
            
            update_progress(4, "Running OCR on model answer...")
            model_raw = extract_text_from_file(m_path)
            
            if not student_raw or not model_raw:
                result_holder["error"] = ("OCR failed to read one of the files. Ensure they are clear.", 400)
                return

            # 2. Parsing (Split into Q1, Q2, etc.)
            update_progress(5, "Processing text and correcting OCR errors...")
            student_segments = parse_exam_file(student_raw)
            model_segments = parse_exam_file(model_raw)
            
            if not model_segments:
                result_holder["error"] = ("Could not detect Question Numbers (e.g., '1.', 'Q1') in the Model Answer PDF. Please ensure standard formatting.", 400)
                return

            # Clean individual segments
            # 1. First, process Model Answer to build a vocabulary
            all_model_text = ""
            for k in model_segments:
                m_clean = clean_text(model_segments[k])
                model_segments[k] = m_clean
                all_model_text += " " + m_clean
                
            # Build vocabulary from model answer for context-aware correction
            model_vocab = set(all_model_text.split())
            print(f"Built Model Vocabulary: {len(model_vocab)} unique words.")

            # 2. Process Student Answer with Spell Correction
            for k in student_segments:
                s_clean = clean_text(student_segments[k])
                s_corrected = correct_spelling(s_clean, custom_dictionary=model_vocab, cutoff=0.6)
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

            exam_results = scorer.evaluate_exam(student_segments, model_segments, question_schema=q_schema)
            result_holder["result"] = exam_results

        except Exception as e:
            print(f"Error in processing thread: {e}")
            import traceback
            traceback.print_exc()
            result_holder["error"] = (f"An error occurred: {e}", 500)

    # Start processing in a separate thread
    worker = threading.Thread(target=process_evaluation)
    worker.start()
    
    # Wait with a 15-minute timeout (3 OCR passes on CPU can be very slow)
    TIMEOUT_SECONDS = 900
    worker.join(timeout=TIMEOUT_SECONDS)
    
    if worker.is_alive():
        # Thread is still running after timeout
        progress["status"] = "error"
        progress["message"] = "Processing timed out after 15 minutes."
        print("ERROR: Processing timed out!")
        return "Processing timed out. The files may be too large or complex. Try with fewer pages.", 504
    
    # Reset progress
    progress["status"] = "done"
    progress["message"] = "Complete!"
    
    if result_holder["error"]:
        err_msg, err_code = result_holder["error"]
        progress["status"] = "error"
        progress["message"] = err_msg
        return err_msg, err_code
    
    if result_holder["result"]:
        return render_template(
            "result.html",
            exam_data=result_holder["result"]
        )
    
    progress["status"] = "error"
    progress["message"] = "Unknown error"
    return "An unknown error occurred.", 500


if __name__ == "__main__":
    app.run(debug=True)
