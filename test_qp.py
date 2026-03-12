import sys
from question_paper import parse_question_paper_file
from ocr_service import extract_text_from_file

def test_qp(pdf_path):
    print(f"Testing {pdf_path}")
    text = extract_text_from_file(pdf_path)
    print("--- OCR TEXT START ---")
    print(text)
    print("--- OCR TEXT END ---")
    print("\nParsing scheme:")
    schema = parse_question_paper_file(pdf_path)
    print(schema)

if __name__ == "__main__":
    test_qp(sys.argv[1])
