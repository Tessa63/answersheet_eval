"""
Quick verification: test the updated parser with the OCR output from the first diagnostic.
Uses cached OCR if available, otherwise re-runs OCR.
"""
import os, sys, glob
sys.path.append(r"c:\Users\hp\answersheet_eval")

from pdf_parser import parse_exam_file

UPLOADS = r"c:\Users\hp\answersheet_eval\uploads"

# Check if we have cached OCR output
student_ocr_file = r"c:\Users\hp\answersheet_eval\debug_student_ocr.txt"
model_ocr_file = r"c:\Users\hp\answersheet_eval\debug_model_ocr.txt"

if os.path.exists(student_ocr_file) and os.path.exists(model_ocr_file):
    print("Using cached OCR output...")
    with open(student_ocr_file, "r", encoding="utf-8") as f:
        student_raw = f.read()
    with open(model_ocr_file, "r", encoding="utf-8") as f:
        model_raw = f.read()
else:
    print("Need to run OCR first (this will take a few minutes)...")
    from ocr_service import extract_text_from_file
    
    student_files = glob.glob(os.path.join(UPLOADS, "student_*"))
    model_files = glob.glob(os.path.join(UPLOADS, "model_*"))
    
    s_path = student_files[0]
    m_path = model_files[0]
    
    student_raw = extract_text_from_file(s_path)
    model_raw = extract_text_from_file(m_path)
    
    # Save for future use
    with open(student_ocr_file, "w", encoding="utf-8") as f:
        f.write(student_raw)
    with open(model_ocr_file, "w", encoding="utf-8") as f:
        f.write(model_raw)

# First parse model to get expected keys
print("\n=== MODEL ANSWER PARSING (standard) ===")
model_segments = parse_exam_file(model_raw)
print(f"Model keys: {sorted(model_segments.keys())}")
for k, v in sorted(model_segments.items()):
    print(f"  Q{k}: [{len(v)} chars] {v[:80].replace(chr(10), ' ')}...")

# Then parse student WITH expected keys
expected_keys = list(model_segments.keys())
print(f"\n=== STUDENT ANSWER PARSING (with expected_keys={sorted(expected_keys)}) ===")
student_segments = parse_exam_file(student_raw, expected_keys=expected_keys)
print(f"\nStudent keys: {sorted(student_segments.keys())}")
for k, v in sorted(student_segments.items()):
    print(f"  Q{k}: [{len(v)} chars] {v[:80].replace(chr(10), ' ')}...")

# Alignment check
print(f"\n=== KEY ALIGNMENT ===")
s_keys = set(student_segments.keys())
m_keys = set(model_segments.keys())
print(f"Student keys: {sorted(s_keys)}")
print(f"Model keys:   {sorted(m_keys)}")
print(f"Common:       {sorted(s_keys & m_keys)}")
print(f"In model not student: {sorted(m_keys - s_keys)}")
print(f"In student not model: {sorted(s_keys - m_keys)}")
print(f"\nMatch rate: {len(s_keys & m_keys)}/{len(m_keys)} ({100*len(s_keys & m_keys)/max(len(m_keys),1):.0f}%)")
