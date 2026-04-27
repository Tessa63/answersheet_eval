import os
from ocr_pipeline import extract_text_from_pdf

def debug_low_ocr():
    student_path = "uploads/student_Answersheet Low.pdf"
    print(f"Extracting OCR from {student_path}...")
    text = extract_text_from_pdf(student_path, is_handwritten=True)
    print("\n--- OCR TEXT ---")
    print(text)
    with open("low_ocr_output.txt", "w", encoding="utf-8") as f:
        f.write(text)

if __name__ == "__main__":
    debug_low_ocr()
