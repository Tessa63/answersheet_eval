import pytesseract
from PIL import Image
import re
import os
import sys
from pdf2image import convert_from_path

UPLOAD_FOLDER = "uploads"

# Get latest uploaded file
files = sorted(
    [os.path.join(UPLOAD_FOLDER, f) for f in os.listdir(UPLOAD_FOLDER)],
    key=os.path.getmtime,
    reverse=True
)

if not files:
    raise Exception("No uploaded file found")

file_path = files[0]

text = ""

# -------- PDF HANDLING --------
if file_path.lower().endswith(".pdf"):
    images = convert_from_path(
        file_path,
        poppler_path=r"C:\poppler\poppler-23.11.0\Library\bin"
    )
    for img in images:
        text += pytesseract.image_to_string(img)

# -------- IMAGE HANDLING --------
else:
    img = Image.open(file_path)
    text = pytesseract.image_to_string(img)

# -------- CLEAN TEXT --------
text = text.lower()
text = re.sub(r'[^a-z\s]', ' ', text)
text = re.sub(r'\s+', ' ', text).strip()

with open("student_answer.txt", "w", encoding="utf-8") as f:
    f.write(text)

print("OCR TEXT:", text[:300])
