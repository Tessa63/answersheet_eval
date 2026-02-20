
import re
from question_paper import QuestionPaperParser

def mock_extract_text(file_path):
    with open("debug_qp_text.txt", "r", encoding="utf-8") as f:
        return f.read()

# Monkey patch
import question_paper
question_paper.extract_text_from_file = mock_extract_text

def test_parsing():
    parser = QuestionPaperParser()
    print("--- Testing Parse Logic on debug_qp_text.txt ---")
    
    # We call parse_question_paper but we intercept the text extraction
    schema = parser.parse_question_paper("dummy_path")
    
    print("\n[Final Schema Keys]:", sorted(schema.keys()))
    
    if '7a' in schema:
        print("PASS: 7a found.")
    else:
        print("FAIL: 7a NOT found.")
        
    if '9a' in schema:
        print("PASS: 9a found.")
    else:
        print("FAIL: 9a NOT found.")

if __name__ == "__main__":
    test_parsing()
