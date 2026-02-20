
from pdf_parser import ExamParser

def test_aggressive_splitting():
    parser = ExamParser()
    
    # Simulation of Q2 having a list in the answer, but NOT being sub-questions
    # vs Q9 having actual sub-questions
    
    text = """
    2. Explain the features of Python.
    
    Python has many features:
    a) Simple and Easy to Learn
    b) High Level Language
    c) Interpreted Language
    
    3. Next Question.
    
    9. Explain parts of CPU.
    
    a) ALU: Arithmetic Logic Unit.
    
    b) CU: Control Unit.
    """
    
    print("\n--- Parsing Text ---")
    questions = parser.parse_text_to_questions(text)
    
    print(f"Detected Keys: {sorted(questions.keys())}")
    
    # We expect '2' to include the list a,b,c inside it, NOT split into 2a, 2b, 2c.
    # UNLESS the user actually wants that? 
    # User said: "there no 2a or 2b in answer sheet theese parts are only in 16 mark question thats are 7,8,9,10"
    # So for Q2, 'a)' and 'b)' are just list items in the text.
    
    if '2a' in questions:
        print("FAIL: Q2 was split into 2a incorrectly.")
    else:
        print("PASS: Q2 was NOT split (Correct).")
        
    if '9a' in questions:
        print("PASS: Q9 was split into 9a (Correct).")
    else:
        print("FAIL: Q9 was NOT split.")

if __name__ == "__main__":
    test_aggressive_splitting()
