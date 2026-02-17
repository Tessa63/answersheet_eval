"""Quick debug: see what OCR text the question paper produces and what the parser detects."""
from ocr_service import extract_text_from_file
from question_paper import QuestionPaperParser
import re

qp_path = r"c:\Users\hp\answersheet_eval\uploads\question_Exam First Internal ExaminationJanuary 2025  (1).pdf"

print("=== Step 1: OCR the question paper ===")
text = extract_text_from_file(qp_path)

print(f"\n=== FULL OCR TEXT ({len(text)} chars) ===")
print(text)
print("=== END OCR TEXT ===\n")

# Try the parser
print("\n=== Step 2: Parse with QuestionPaperParser ===")
parser = QuestionPaperParser()
schema = parser.parse_question_paper(qp_path)
print(f"\nFinal schema: {schema}")
