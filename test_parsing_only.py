
from pdf_parser import ExamParser

def test_parsing_issues():
    print("\n--- Testing Parsing Logic ---")
    parser = ExamParser()
    
    # Case 1: Implicit "a)" and "b)" following Q9
    text_implicit = """
    9. Explain Photosynthesis parts.
    
    a) Light reaction is the first stage.
    
    b) Dark reaction is the second stage.
    
    10. Next question.
    """
    questions_implicit = parser.parse_text_to_questions(text_implicit)
    print(f"Implicit a/b keys found: {list(questions_implicit.keys())}")
    for k, v in questions_implicit.items():
        print(f"Key {k}: {v[:50]}...")

if __name__ == "__main__":
    test_parsing_issues()
