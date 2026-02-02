from flask import Flask, request, render_template
import os
from ocr_service import extract_text_from_file
from text_utils import clean_text, correct_spelling
from pdf_parser import parse_exam_file
from scoring import SemanticScorer

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

scorer = SemanticScorer()

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/evaluate", methods=["POST"])
def evaluate():
    if "student_file" not in request.files or "model_file" not in request.files:
        return "Please upload both files.", 400

    student_file = request.files["student_file"]
    model_file = request.files["model_file"]

    if student_file.filename == "" or model_file.filename == "":
        return "No file selected", 400

    # Save Files
    s_path = os.path.join(UPLOAD_FOLDER, "student_" + student_file.filename)
    m_path = os.path.join(UPLOAD_FOLDER, "model_" + model_file.filename)
    
    student_file.save(s_path)
    model_file.save(m_path)

    try:
        # 1. OCR (Extract raw text)
        print("Extracting Student Text...")
        student_raw = extract_text_from_file(s_path)
        
        print("Extracting Model Text...")
        model_raw = extract_text_from_file(m_path)
        
        if not student_raw or not model_raw:
             return "OCR failed to read one of the files. Ensure they are clear.", 400

        # 2. Parsing (Split into Q1, Q2, etc.)
        # Note: We clean the text lightly *inside* the parser or pass raw?
        # Let's pass raw to parser, then clean the content.
        student_segments = parse_exam_file(student_raw)
        model_segments = parse_exam_file(model_raw)
        
        if not model_segments:
            return "Could not detect Question Numbers (e.g., '1.', 'Q1') in the Model Answer PDF. Please ensure standard formatting.", 400

        # Clean individual segments
        
        # 1. First, process Model Answer to build a vocabulary
        all_model_text = ""
        for k in model_segments:
            # Clean and store
            m_clean = clean_text(model_segments[k])
            model_segments[k] = m_clean
            all_model_text += " " + m_clean
            
        # Build vocabulary from model answer for context-aware correction
        model_vocab = set(all_model_text.split())
        print(f"Built Model Vocabulary: {len(model_vocab)} unique words.")

        # 2. Process Student Answer with Spell Correction
        for k in student_segments:
            s_clean = clean_text(student_segments[k])
            # Use Model Vocabulary to correct OCR errors (cutoff=0.6 found via testing)
            s_corrected = correct_spelling(s_clean, custom_dictionary=model_vocab, cutoff=0.6)
            student_segments[k] = s_corrected
            
            # Debug log
            if len(s_clean) > 0:
                print(f"Q{k} Original: {s_clean[:30]}... -> Corrected: {s_corrected[:30]}...")

        # 3. Scoring
        print("\n--- DEBUG: Parsed Student Data ---")
        for k, v in student_segments.items():
            preview = v[:50].replace('\n', ' ') + "..."
            print(f"Q{k}: {preview}")
        print("------------------------------------\n")

        exam_results = scorer.evaluate_exam(student_segments, model_segments)

        return render_template(
            "result.html",
            exam_data=exam_results
        )

    except Exception as e:
        print(f"Error: {e}")
        return f"An error occurred: {e}", 500

if __name__ == "__main__":
    app.run(debug=True)
