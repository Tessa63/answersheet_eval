"""Quick diagnostic - writes to file instead of relying on terminal"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

# Redirect all output to a log file
log_file = open("diagnose_log.txt", "w", encoding="utf-8")
sys.stdout = log_file
sys.stderr = log_file

from ocr_service import extract_text_from_file
from pdf_parser import parse_exam_file
from question_paper import parse_question_paper_file

UPLOADS = "uploads"

print("=" * 60)
print("1. QUESTION PAPER SCHEMA")
print("=" * 60)
q_file = os.path.join(UPLOADS, "question_Exam First Internal ExaminationJanuary 2025  (1).pdf")
if os.path.exists(q_file):
    schema = parse_question_paper_file(q_file)
    print(f"\nFinal Schema:")
    for k, v in sorted(schema.items(), key=lambda x: str(x[0])):
        print(f"  {k}: {v}")
else:
    print("NOT FOUND")

print("\n" + "=" * 60)
print("2. STUDENT ANSWER - PARSED SEGMENTS")
print("=" * 60)
s_file = os.path.join(UPLOADS, "student_Ans1.pdf")
if os.path.exists(s_file):
    student_raw = extract_text_from_file(s_file)
    print(f"Raw text length: {len(student_raw)} chars")
    print(f"\n--- FULL RAW TEXT ---")
    print(student_raw[:3000])
    print("... [truncated]")
    
    segments = parse_exam_file(student_raw)
    print(f"\n--- PARSED SEGMENTS ({len(segments)}) ---")
    for k, v in sorted(segments.items()):
        print(f"  Q{k}: {len(v)} chars - '{v[:100]}...'")
else:
    print("NOT FOUND")

print("\n" + "=" * 60)
print("3. MODEL ANSWER - PARSED SEGMENTS")
print("=" * 60)
m_file = os.path.join(UPLOADS, "model_IE1 Answer Key.pdf")
if os.path.exists(m_file):
    model_raw = extract_text_from_file(m_file)
    print(f"Raw text length: {len(model_raw)} chars")
    print(f"\n--- FULL RAW TEXT ---")
    print(model_raw[:3000])
    print("... [truncated]")
    
    segments = parse_exam_file(model_raw)
    print(f"\n--- PARSED SEGMENTS ({len(segments)}) ---")
    for k, v in sorted(segments.items()):
        print(f"  Q{k}: {len(v)} chars - '{v[:100]}...'")
else:
    print("NOT FOUND")

print("\nDONE")
log_file.close()
print("Diagnostic complete - see diagnose_log.txt", file=sys.__stdout__)
