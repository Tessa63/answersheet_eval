"""Examine OCR text lines to understand the table row format."""
import re

# Read the saved OCR text from the previous run
# Let's just manually extract lines with question marks patterns
text = open(r"c:\Users\hp\answersheet_eval\debug_qp_text.txt", "r", encoding="utf-8").read() if False else ""

# We need to run OCR again but save the text
from ocr_service import extract_text_from_file
qp_path = r"c:\Users\hp\answersheet_eval\uploads\question_Exam First Internal ExaminationJanuary 2025  (1).pdf"
text = extract_text_from_file(qp_path)

# Save for future reference
with open(r"c:\Users\hp\answersheet_eval\debug_qp_text.txt", "w", encoding="utf-8") as f:
    f.write(text)

# Print each line with line number
lines = text.split('\n')
print(f"Total lines: {len(lines)}\n")

# Find lines that have both a digit and "CO" (these are table rows)
for i, line in enumerate(lines):
    if re.search(r'CO\d', line, re.IGNORECASE) or re.search(r'PART\s*[AB]', line, re.IGNORECASE):
        print(f"L{i:3d}: {line.rstrip()}")
