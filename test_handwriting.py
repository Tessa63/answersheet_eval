import os
import sys

# Add current directory to path so we can import ocr_service
sys.path.append(r"c:\Users\hp\answersheet_eval")

try:
    import easyocr
    print("EasyOCR imported successfully.")
except ImportError:
    print("Error: EasyOCR not installed. Please install it using: pip install easyocr")
    sys.exit(1)

import ocr_service

def test_file(filename):
    path = os.path.join(r"c:\Users\hp\answersheet_eval\uploads", filename)
    if not os.path.exists(path):
        print(f"File not found: {path}")
        return

    print(f"\nProcessing {filename}...")
    try:
        text = ocr_service.extract_text_from_file(path)
        print(f"--- Extracted Text from {filename} ---")
        print(text[:500]) # Print first 500 chars
        print("--------------------------------------")
    except Exception as e:
        print(f"Failed to process {filename}: {e}")

if __name__ == "__main__":
    test_file("answer.pdf")
    test_file("answer.jpeg")
