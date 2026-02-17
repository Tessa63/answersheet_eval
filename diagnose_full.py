"""
Diagnostic script to understand what the OCR pipeline is producing.
Run this to see exactly what text is being extracted and parsed.
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from ocr_service import extract_text_from_file
from pdf_parser import parse_exam_file
from question_paper import parse_question_paper_file

UPLOADS = "uploads"

# 1. Check Question Paper parsing
print("=" * 60)
print("1. QUESTION PAPER PARSING")
print("=" * 60)
q_file = os.path.join(UPLOADS, "question_Exam First Internal ExaminationJanuary 2025  (1).pdf")
if os.path.exists(q_file):
    schema = parse_question_paper_file(q_file)
    print(f"\nFinal Schema: {schema}")
else:
    print(f"Question paper not found: {q_file}")

# 2. Check Student OCR
print("\n" + "=" * 60)
print("2. STUDENT ANSWER OCR")
print("=" * 60)
s_file = os.path.join(UPLOADS, "student_Ans1.pdf")
if os.path.exists(s_file):
    student_raw = extract_text_from_file(s_file)
    print(f"\nRaw text length: {len(student_raw)} chars")
    print(f"\nFirst 1000 chars:\n{student_raw[:1000]}")
    print(f"\n...Last 500 chars:\n{student_raw[-500:]}")
    
    # Parse into segments
    student_segments = parse_exam_file(student_raw)
    print(f"\nParsed {len(student_segments)} student segments:")
    for k, v in sorted(student_segments.items()):
        print(f"  Q{k}: {len(v)} chars - '{v[:80]}...'")
else:
    print(f"Student file not found: {s_file}")

# 3. Check Model Answer OCR
print("\n" + "=" * 60)
print("3. MODEL ANSWER OCR")
print("=" * 60)
m_file = os.path.join(UPLOADS, "model_IE1 Answer Key.pdf")
if os.path.exists(m_file):
    model_raw = extract_text_from_file(m_file)
    print(f"\nRaw text length: {len(model_raw)} chars")
    print(f"\nFirst 1000 chars:\n{model_raw[:1000]}")
    print(f"\n...Last 500 chars:\n{model_raw[-500:]}")
    
    # Parse into segments
    model_segments = parse_exam_file(model_raw)
    print(f"\nParsed {len(model_segments)} model segments:")
    for k, v in sorted(model_segments.items()):
        print(f"  Q{k}: {len(v)} chars - '{v[:80]}...'")
else:
    print(f"Model file not found: {m_file}")

print("\n" + "=" * 60)
print("DIAGNOSIS COMPLETE")
print("=" * 60)
