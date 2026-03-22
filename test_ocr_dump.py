from ocr_service import extract_text_from_file
import os

pdf_path = None
# Find the largest student PDF to test
for f in os.listdir("uploads"):
    if f.startswith("student_") and f.endswith(".pdf"):
        pdf_path = os.path.join("uploads", f)
        break

if pdf_path:
    print(f"Testing OCR on: {pdf_path}")
    text = extract_text_from_file(pdf_path)
    with open("ocr_dump.txt", "w", encoding="utf-8") as out:
        out.write(text)
    print(f"Extraction complete. Wrote {len(text)} chars.")
else:
    print("No student PDF found")
