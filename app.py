from dotenv import load_dotenv
load_dotenv()

from flask import Flask, request, render_template, jsonify
import os
import time
import threading
from typing import Dict, Any
from ai_evaluator import evaluate_exam_with_gemini

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Hybrid pipeline:
#   Phase 1-3: Local OCR    (TrOCR for handwriting, EasyOCR+Tesseract for printed)
#   Phase 4:   API Grading  (Gemini 2.5 Flash → 2.0 Flash → 1.5 Flash, auto failover)
#              Ultimate fallback: Local Semantic Evaluator (offline)

# --- Global State ---
# Using globals for simplicity (single-user app).
# For multi-user, you'd use a task queue like Celery.
progress: Dict[str, Any] = {
    "status": "idle",    # idle | processing | done | error
    "message": "",
    "step": 0,
    "total_steps": 4     # 3 OCR phases + 1 grading phase
}

# Stores the latest result so /results can render it after processing
latest_result: Dict[str, Any] = {
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
        overall_start = time.time()
        try:
            progress["total_steps"] = 4  # 3 OCR + 1 grading

            # Pass a callback so the evaluator can update progress for each phase
            def on_progress(step, message):
                update_progress(step, message)

            exam_results = evaluate_exam_with_gemini(
                s_path, m_path, q_path,
                progress_callback=on_progress
            )

            total_time = time.time() - overall_start
            print(f"\n=== TOTAL PROCESSING TIME: {total_time:.1f}s ===")

            latest_result["exam_data"] = exam_results
            progress["status"] = "done"
            progress["message"] = f"Complete! (Graded by {exam_results.get('grading_api', 'AI')})"

        except Exception as e:
            total_time = time.time() - overall_start
            print(f"Error in evaluator thread after {total_time:.1f}s: {e}")
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
