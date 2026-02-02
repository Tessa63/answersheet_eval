from ocr_service import extract_text_from_file
import os

# The specific image user uploaded
img_path = r"c:/Users/hp/answersheet_eval/uploads/student_answer.pdf"

import pytesseract
from pdf2image import convert_from_path
import numpy as np
from PIL import Image

def test():
    if not os.path.exists(img_path):
        print(f"Image not found at {img_path}")
        return

    print(f"--- Processing {img_path} with Pytesseract ---")
    
    # Simple conversion
    images = convert_from_path(img_path, dpi=300)
    text = ""
    for img in images:
        text += pytesseract.image_to_string(img) + "\n"
        
    print("\n--- RAW OCR OUTPUT (TESSERACT) ---")
    print(text)
    print("----------------------")

if __name__ == "__main__":
    test()
