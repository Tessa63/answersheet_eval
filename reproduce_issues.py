
import re
from pdf_parser import ExamParser
from scoring import SemanticScorer

def test_parsing_issues():
    print("\n--- Testing Parsing Logic ---")
    parser = ExamParser()
    
    # Case 1: "9a" and "9b" explicitly
    text_explicit = """
    Q9. Explain the process of Photosynthesis.
    
    9a) Light dependent reactions occur in thylakoids.
    
    9b) Calvin cycle occurs in stroma.
    """
    questions = parser.parse_text_to_questions(text_explicit)
    print(f"Explicit 9a/9b keys found: {list(questions.keys())}")
    
    # Case 2: Implicit "a)" and "b)" following Q9
    text_implicit = """
    9. Explain Photosynthesis parts.
    
    a) Light reaction is the first stage.
    
    b) Dark reaction is the second stage.
    
    10. Next question.
    """
    questions_implicit = parser.parse_text_to_questions(text_implicit)
    print(f"Implicit a/b keys found: {list(questions_implicit.keys())}")
    
    # Check if 'a' and 'b' were attached to 9
    # Current behavior might be to ignore them or treat them as separate 'a', 'b'? 
    # Or maybe it parses 'a' as 'a' key?
    
def test_scoring_strictness():
    print("\n--- Testing Scoring Strictness ---")
    scorer = SemanticScorer()
    
    model_ans = "Photosynthesis is the process used by plants to convert light energy into chemical energy that can later be released to fuel the organisms activities."
    
    # Conceptually correct but different words
    student_ans = "Plants take in sunlight and turn it into food energy. This happens in the leaves."
    
    res = scorer.evaluate_single_answer(student_ans, model_ans)
    print(f"Model: {model_ans}")
    print(f"Student: {student_ans}")
    print(f"Score: {res['score']}/10")
    print(f"Details: {res['details']}")
    
    # Check if score is reasonable (expect > 5 typically for correct concept)
    if res['score'] < 5:
        print("FAIL: Score too low for valid concept.")
    else:
        print("PASS: Score fits acceptable range.")

if __name__ == "__main__":
    test_parsing_issues()
    test_scoring_strictness()
