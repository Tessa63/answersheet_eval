"""
Dump the full raw OCR text from student and model to files for inspection.
"""
import os, sys, glob
sys.path.append(r"c:\Users\hp\answersheet_eval")

from ocr_service import extract_text_from_file

UPLOADS = r"c:\Users\hp\answersheet_eval\uploads"

student_files = glob.glob(os.path.join(UPLOADS, "student_*"))
model_files = glob.glob(os.path.join(UPLOADS, "model_*"))

s_path = student_files[0]
m_path = model_files[0]

print(f"Extracting student text from: {s_path}")
student_raw = extract_text_from_file(s_path)

print(f"Extracting model text from: {m_path}")
model_raw = extract_text_from_file(m_path)

# Save to files for inspection
with open("debug_student_ocr.txt", "w", encoding="utf-8") as f:
    f.write(student_raw)
print(f"\nStudent OCR saved to debug_student_ocr.txt ({len(student_raw)} chars)")

with open("debug_model_ocr.txt", "w", encoding="utf-8") as f:
    f.write(model_raw)
print(f"Model OCR saved to debug_model_ocr.txt ({len(model_raw)} chars)")

# Also check how many pages each PDF has
from pdf2image import convert_from_path

POPPLER_PATH = None
possible_poppler_paths = [
    r"C:\poppler\poppler-24.08.0\Library\bin",
    r"C:\poppler\Library\bin",
    r"C:\Program Files\poppler-0.68.0\bin",
]
for p in possible_poppler_paths:
    if os.path.isdir(p):
        POPPLER_PATH = p
        break

s_images = convert_from_path(s_path, poppler_path=POPPLER_PATH)
m_images = convert_from_path(m_path, poppler_path=POPPLER_PATH)
print(f"\nStudent PDF has {len(s_images)} pages")
print(f"Model PDF has {len(m_images)} pages")
