from ocr_service import ocr_page_dual_engine
from pdf2image import convert_from_path
import numpy as np

pdf_path = "uploads/student_Ans1.pdf"
print("Converting page 1...")
images = convert_from_path(pdf_path, dpi=150, first_page=1, last_page=1)
img_np = np.array(images[0])

print("Running OCR...")
text = ocr_page_dual_engine(img_np)

print("OCR TEXT:")
print("="*40)
print(text)
print("="*40)
