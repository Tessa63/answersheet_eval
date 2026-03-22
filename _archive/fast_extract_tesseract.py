import os
import time
import numpy as np
from pdf2image import convert_from_path
from ocr_service import POPPLER_PATH, remove_red_ink, ocr_page_tesseract_only

def main():
    m_path = "uploads/model_WhatsApp Image 2026-03-13 at 9.39.41 AM.pdf"
    print("Converting PDF to images...")
    if POPPLER_PATH:
        images = convert_from_path(m_path, poppler_path=POPPLER_PATH, dpi=150)
    else:
        images = convert_from_path(m_path, dpi=150)
        
    text = ""
    for i, img in enumerate(images, 1):
        print(f"OCR page {i}/{len(images)} [FAST]...")
        img_np = np.array(img)
        no_red_img = remove_red_ink(img_np)
        page_text = ocr_page_tesseract_only(no_red_img)
        text += page_text + "\n---PAGE_BREAK---\n"
        
    with open("dumped_model_fast.txt", "w", encoding="utf-8") as f:
        f.write(text)
    print("Done. Saved to dumped_model_fast.txt")

if __name__ == '__main__':
    main()
