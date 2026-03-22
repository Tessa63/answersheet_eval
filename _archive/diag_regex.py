"""
Quick diagnosis of what the new regex does to student OCR text.
Shows what question keys get extracted now vs what we expect.
"""
import sys
sys.path.insert(0, r"c:\Users\hp\answersheet_eval")

from pdf_parser import ExamParser
from ocr_service import extract_text_from_file

STUDENT = r"c:\Users\hp\answersheet_eval\uploads\student_Ans1.pdf"

print("Testing student parsing with new regex...")
print()

# Read student OCR text
student_raw = extract_text_from_file(STUDENT)
print(f"Total OCR text: {len(student_raw)} chars")

# Test the new broad regex on the noisy text  
parser = ExamParser()
pat = parser.question_start_pattern

import re
# Find ALL matches
matches = list(pat.finditer(student_raw))
print(f"\nTotal question-marker matches found: {len(matches)}")
print("\nAll matches (number | context):")
for m in matches:
    ctx_start = max(0, m.start()-10)
    ctx_end = min(len(student_raw), m.end()+30)
    ctx = student_raw[ctx_start:ctx_end].replace('\n', '↵')
    print(f"  Q{m.group(1)} | '{ctx}'")

print()
# Now parse and show resulting keys
result = parser.parse_text_to_questions(student_raw)
print(f"Resulting question keys: {sorted(result.keys())}")
print(f"Total segments: {len(result)}")
for k, v in sorted(result.items()):
    print(f"  Q{k}: {len(v)} chars | {v[:50].replace(chr(10),' ')}...")
