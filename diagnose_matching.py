"""
Diagnostic: trace exactly what OCR extracts, how questions are parsed,
and where the matching fails.
"""
import os, sys, glob
sys.path.append(r"c:\Users\hp\answersheet_eval")

from ocr_service import extract_text_from_file
from pdf_parser import parse_exam_file
from question_paper import parse_question_paper_file

UPLOADS = r"c:\Users\hp\answersheet_eval\uploads"

# Find the most recently used files
student_files = glob.glob(os.path.join(UPLOADS, "student_*"))
model_files = glob.glob(os.path.join(UPLOADS, "model_*"))
qp_files = glob.glob(os.path.join(UPLOADS, "question_*"))

print("=== FILES FOUND ===")
print(f"Student: {student_files}")
print(f"Model:   {model_files}")
print(f"QP:      {qp_files}")

if not student_files or not model_files:
    print("ERROR: No student or model files found in uploads/")
    sys.exit(1)

s_path = student_files[0]
m_path = model_files[0]
q_path = qp_files[0] if qp_files else None

# 1. OCR
print("\n=== STEP 1: OCR EXTRACTION ===")
print(f"\n--- Student OCR ({s_path}) ---")
student_raw = extract_text_from_file(s_path)
print(f"Student raw text length: {len(student_raw)} chars")
print("FIRST 2000 CHARS:")
print(student_raw[:2000])
print("...")

print(f"\n--- Model OCR ({m_path}) ---")
model_raw = extract_text_from_file(m_path)
print(f"Model raw text length: {len(model_raw)} chars")
print("FIRST 2000 CHARS:")
print(model_raw[:2000])
print("...")

# 2. Question Paper Schema
if q_path:
    print(f"\n=== STEP 2: QUESTION PAPER SCHEMA ({q_path}) ===")
    q_schema = parse_question_paper_file(q_path)
    for k, v in q_schema.items():
        print(f"  {k}: {v}")
else:
    print("\n=== STEP 2: NO QUESTION PAPER ===")
    q_schema = {}

# 3. PDF Parsing
print("\n=== STEP 3: QUESTION PARSING ===")
student_segments = parse_exam_file(student_raw)
model_segments = parse_exam_file(model_raw)

print(f"\nStudent segments ({len(student_segments)} questions):")
for k, v in sorted(student_segments.items()):
    preview = v[:100].replace('\n', ' ')
    print(f"  Q{k}: [{len(v)} chars] {preview}...")

print(f"\nModel segments ({len(model_segments)} questions):")
for k, v in sorted(model_segments.items()):
    preview = v[:100].replace('\n', ' ')
    print(f"  Q{k}: [{len(v)} chars] {preview}...")

# 4. Key alignment check
print("\n=== STEP 4: KEY ALIGNMENT ===")
s_keys = set(student_segments.keys())
m_keys = set(model_segments.keys())
print(f"Student keys: {sorted(s_keys)}")
print(f"Model keys:   {sorted(m_keys)}")
print(f"Common keys:  {sorted(s_keys & m_keys)}")
print(f"In model but NOT in student: {sorted(m_keys - s_keys)}")
print(f"In student but NOT in model: {sorted(s_keys - m_keys)}")
