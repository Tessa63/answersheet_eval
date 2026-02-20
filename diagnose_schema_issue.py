
import os
from question_paper import parse_question_paper_file
from ocr_service import extract_text_from_file
from pdf_parser import parse_exam_file, ExamParser

def diagnose():
    print("--- DIAGNOSING SCHEMA ISSUE ---")
    
    # Locate files
    upload_dir = "uploads"
    qp_file = None
    model_file = None
    student_file = None
    
    for f in os.listdir(upload_dir):
        if "question_" in f and f.endswith(".pdf"):
            qp_file = os.path.join(upload_dir, f)
        if "model_" in f and f.endswith(".pdf"):
            model_file = os.path.join(upload_dir, f)
        if "student_" in f and f.endswith(".pdf"):
            student_file = os.path.join(upload_dir, f)
            
    print(f"QP File: {qp_file}")
    
    # 1. Parse QP
    if qp_file:
        q_schema = parse_question_paper_file(qp_file)
        print(f"\n[QP Schema Keys]: {sorted(q_schema.keys())}")
        
        # Check for 7a, 7b...
        has_parts = any(k in q_schema for k in ['7a','7b','8a','8b','9a','9b'])
        if has_parts:
            print("PASS: QP Schema contains sub-parts.")
        else:
            print("FAIL: QP Schema MISSING sub-parts for 7,8,9. This will cause them to be dropped from Model/Student.")
    else:
        q_schema = {}
        print("SKIP: No QP file found.")

    # 2. Parse Model using Schema
    if model_file:
        print(f"\nModel File: {model_file}")
        text = extract_text_from_file(model_file)
        print(f"Model Text Len: {len(text)}")
        
        expected = list(q_schema.keys()) if q_schema else None
        model_segments = parse_exam_file(text, expected_keys=expected)
        print(f"[Model Keys]: {sorted(model_segments.keys())}")
        
        # Check if 7a, 7b exist
        if '7a' in model_segments: 
             print("PASS: Model has 7a.")
        else:
             print("FAIL: Model missing 7a.")
             
    # 3. Parse Student using Schema + Model Keys
    if student_file:
        print(f"\nStudent File: {student_file}")
        st_text = extract_text_from_file(student_file)
        
        expected_st = list(model_segments.keys()) if model_file else []
        if q_schema:
            for k in q_schema:
                if k not in expected_st and not k.startswith("_"):
                    expected_st.append(k)
                    
        st_segments = parse_exam_file(st_text, expected_keys=expected_st)
        print(f"[Student Keys]: {sorted(st_segments.keys())}")

if __name__ == "__main__":
    try:
        diagnose()
    except Exception as e:
        print(f"CRASH: {e}")
        import traceback
        traceback.print_exc()
