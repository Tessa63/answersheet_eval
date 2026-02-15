"""
Diagnostic Script: Inspect what the OCR pipeline produces for the latest uploaded files.
This will show us exactly what text the system sees and where the scoring fails.
"""
import sys
sys.path.insert(0, r"c:\Users\hp\answersheet_eval")

from ocr_service import extract_text_from_file
from pdf_parser import parse_exam_file
from text_utils import clean_text, correct_spelling
from question_paper import parse_question_paper_file

STUDENT = r"c:\Users\hp\answersheet_eval\uploads\student_Ans1.pdf"
MODEL = r"c:\Users\hp\answersheet_eval\uploads\model_IE1 Answer Key.pdf"
QUESTION = r"c:\Users\hp\answersheet_eval\uploads\question_Exam First Internal ExaminationJanuary 2025  (1).pdf"

print("="*60)
print("STEP 1: Question Paper OCR")
print("="*60)
q_schema = parse_question_paper_file(QUESTION)
print(f"\nFinal Schema: {q_schema}")
print(f"Number of questions detected: {len(q_schema)}")

print("\n" + "="*60)
print("STEP 2: Model Answer OCR")
print("="*60)
model_raw = extract_text_from_file(MODEL)
print(f"\nRaw Model Text (first 1000 chars):\n{model_raw[:1000]}")
print(f"\nTotal model text length: {len(model_raw)} chars")

print("\n" + "="*60)
print("STEP 3: Model Answer Parsing")
print("="*60)
model_segments = parse_exam_file(model_raw)
print(f"Model segments found: {list(model_segments.keys())}")
for k, v in model_segments.items():
    preview = v[:150].replace('\n', ' ')
    print(f"  Q{k}: {preview}...")

print("\n" + "="*60)
print("STEP 4: Student Answer OCR")
print("="*60)
student_raw = extract_text_from_file(STUDENT)
print(f"\nRaw Student Text (first 1000 chars):\n{student_raw[:1000]}")
print(f"\nTotal student text length: {len(student_raw)} chars")

print("\n" + "="*60)
print("STEP 5: Student Answer Parsing")
print("="*60)
student_segments = parse_exam_file(student_raw)
print(f"Student segments found: {list(student_segments.keys())}")
for k, v in student_segments.items():
    preview = v[:150].replace('\n', ' ')
    print(f"  Q{k}: {preview}...")

print("\n" + "="*60)
print("STEP 6: Text Cleaning + Spell Correction")
print("="*60)
# Build model vocab
all_model_text = ""
for k in model_segments:
    m_clean = clean_text(model_segments[k])
    model_segments[k] = m_clean
    all_model_text += " " + m_clean

model_vocab = set(all_model_text.split())
print(f"Model vocabulary size: {len(model_vocab)} words")
print(f"Sample model words: {list(model_vocab)[:20]}")

for k in student_segments:
    s_clean = clean_text(student_segments[k])
    s_corrected = correct_spelling(s_clean, custom_dictionary=model_vocab, cutoff=0.6)
    student_segments[k] = s_corrected
    print(f"\nQ{k} cleaned: {s_clean[:100]}...")
    print(f"Q{k} corrected: {s_corrected[:100]}...")

print("\n" + "="*60)
print("DONE - Review the output above to identify issues")
print("="*60)
