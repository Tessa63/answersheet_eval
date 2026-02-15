"""Quick comparison: Tesseract vs EasyOCR on student handwritten PDF."""
import sys
sys.path.insert(0, r"c:\Users\hp\answersheet_eval")

from pdf2image import convert_from_path
import pytesseract
import numpy as np
from ocr_service import preprocess_image, remove_red_ink, POPPLER_PATH

STUDENT = r"c:\Users\hp\answersheet_eval\uploads\student_Ans1.pdf"

# Convert just the first 2 pages
if POPPLER_PATH:
    images = convert_from_path(STUDENT, poppler_path=POPPLER_PATH, dpi=200, first_page=1, last_page=2)
else:
    images = convert_from_path(STUDENT, dpi=200, first_page=1, last_page=2)

print("=" * 60)
print("TESSERACT OUTPUT (Pages 1-2)")
print("=" * 60)

for i, img in enumerate(images, 1):
    img_np = np.array(img)
    # Remove red ink
    no_red = remove_red_ink(img_np)
    # Preprocess
    processed = preprocess_image(no_red)
    
    # Tesseract with custom config for handwriting
    text = pytesseract.image_to_string(processed, config='--psm 6 --oem 3')
    print(f"\n--- Page {i} ---")
    print(text[:500])
    print("...")
