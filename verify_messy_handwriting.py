import os
import sys

# Add current directory to path
sys.path.append(os.getcwd())

import ocr_service

def verify_file(filename):
    file_path = os.path.join("uploads", filename)
    print(f"\n{'='*20}\nTesting File: {filename}\n{'='*20}")
    
    if not os.path.exists(file_path):
        print("File not found.")
        return

    try:
        print("Running OCR... (this may take a moment)")
        text = ocr_service.extract_text_from_file(file_path)
        
        print("\n--- OCR OUTPUT START ---")
        print(text[:1000]) # First 1000 chars
        print("--- OCR OUTPUT END ---\n")
        
        # Simple heuristic check
        if len(text.strip()) == 0:
            print("[WARNING] OCR returned empty text. Possible failure.")
        else:
            print(f"[SUCCESS] Extracted {len(text)} characters.")
            
    except Exception as e:
        print(f"[ERROR] OCR Failed: {e}")

if __name__ == "__main__":
    # Test a PDF
    verify_file("student_answer.pdf")
    
    # Test a typically messy image (WhatsApp)
    verify_file("WhatsApp Image 2026-01-07 at 8.18.37 AM.jpeg")
