"""Quick test: Run new dual-engine OCR on first 2 pages of student handwriting."""
import sys
sys.path.insert(0, r"c:\Users\hp\answersheet_eval")

from ocr_service import extract_text_from_file
from pdf_parser import parse_exam_file

# Test just the student handwritten file  
STUDENT = r"c:\Users\hp\answersheet_eval\uploads\student_Ans1.pdf"

print("=" * 60)
print("DUAL-ENGINE OCR TEST ON STUDENT HANDWRITING")
print("=" * 60)

student_raw = extract_text_from_file(STUDENT)

print(f"\n{'=' * 60}")
print(f"RAW OCR TEXT (first 2000 chars):")
print(f"{'=' * 60}")
print(student_raw[:2000])

print(f"\n{'=' * 60}")
print(f"PARSED SEGMENTS:")
print(f"{'=' * 60}")
segments = parse_exam_file(student_raw)
print(f"Segment keys: {list(segments.keys())}")
for k, v in segments.items():
    preview = v[:200].replace('\n', ' ')
    print(f"\n  Q{k}: {preview}")
