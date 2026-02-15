"""Test different preprocessing + OCR strategies on the handwritten student PDF."""
import sys
sys.path.insert(0, r"c:\Users\hp\answersheet_eval")

from pdf2image import convert_from_path
import pytesseract
import numpy as np
import cv2
from ocr_service import remove_red_ink, POPPLER_PATH

STUDENT = r"c:\Users\hp\answersheet_eval\uploads\student_Ans1.pdf"

# Convert just page 2 (has the actual math content, not the header)
if POPPLER_PATH:
    images = convert_from_path(STUDENT, poppler_path=POPPLER_PATH, dpi=300, first_page=2, last_page=2)
else:
    images = convert_from_path(STUDENT, dpi=300, first_page=2, last_page=2)

img = np.array(images[0])

# Remove red ink first
no_red = remove_red_ink(img)

# Strategy 1: Minimal preprocessing - just grayscale + threshold
gray = cv2.cvtColor(no_red, cv2.COLOR_BGR2GRAY)
_, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

print("=" * 60)
print("STRATEGY 1: Grayscale + Otsu Threshold (PSM 6)")
print("=" * 60)
text = pytesseract.image_to_string(binary, config='--psm 6 --oem 3')
print(text[:600])

print("\n" + "=" * 60)
print("STRATEGY 2: Adaptive Threshold (PSM 4 - line detection)")
print("=" * 60)
adaptive = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 12)
text2 = pytesseract.image_to_string(adaptive, config='--psm 4 --oem 3')
print(text2[:600])

print("\n" + "=" * 60)
print("STRATEGY 3: EasyOCR on same preprocessed image")
print("=" * 60)
import easyocr
reader = easyocr.Reader(['en'])
results = reader.readtext(binary, detail=0, paragraph=True)
text3 = "\n".join(results)
print(text3[:600])

print("\n" + "=" * 60)
print("STRATEGY 4: EasyOCR on raw color (no preprocessing)")
print("=" * 60)
results4 = reader.readtext(no_red, detail=0, paragraph=True)
text4 = "\n".join(results4)
print(text4[:600])
