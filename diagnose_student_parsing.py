
import os
import glob
from ocr_service import extract_text_from_file
from pdf_parser import parse_exam_file

def diagnose_student_parsing():
    print("--- DIAGNOSING STUDENT PARSING ---")
    
    # Find latest student file
    files = glob.glob("uploads/student_*.pdf")
    if not files:
        print("No student file found in uploads/.")
        return
        
    # Pick the most recent one
    student_file = max(files, key=os.path.getctime)
    print(f"Analyzing file: {student_file}")
    
    # 1. OCR Extraction
    print("Running OCR (this might take a moment)...")
    text = extract_text_from_file(student_file)
    print(f"OCR Text Length: {len(text)}")
    print("-" * 40)
    print(text[:2000]) # Print first 2k chars to see start of answers
    print("-" * 40)
    
    # 2. Parse Attempt
    print("\nAttempting to parse...")
    segments = parse_exam_file(text)
    print(f"Keys Found: {sorted(segments.keys())}")
    
    for k in sorted(segments.keys()):
        content = segments[k].strip()
        preview = content[:50].replace('\n', ' ')
        print(f"[{k}]: {preview}...")

    # 3. Check for obvious misses
    # If text contains "3." but key '3' is missing, regex is failing.
    if '3' not in segments and '3' in text:
        print("\nWARNING: '3' found in text but not in keys. Regex might be mismatching.")
    
    # Dump to file for deeper inspection if needed
    with open("debug_student_ocr.txt", "w", encoding="utf-8") as f:
        f.write(text)
    print("\nSaved raw OCR text to debug_student_ocr.txt")

if __name__ == "__main__":
    diagnose_student_parsing()
