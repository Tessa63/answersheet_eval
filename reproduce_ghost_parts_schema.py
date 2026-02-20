
from pdf_parser import ExamParser

def test_schema_aware_splitting():
    parser = ExamParser()
    
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
    
    # 1. Test WITHOUT Schema (Default behavior might still match default regex if I didn't change default strictness? 
    # Actually I changed default strictness to be 'loose' if expected_keys is None in parse_text_to_questions?
    # No, I kept it same? 
    # Let's check: in _extract_sub_parts, if expected_keys is None, I check against roman numerals or a-h.
    # So WITHOUT Schema, it WILL likely find 2a, 2b.
    
    print("\n--- Test WITHOUT Schema ---")
    q_no_schema = parser.parse_text_to_questions(text)
    print(f"Keys (No Schema): {sorted(q_no_schema.keys())}")
    
    # 2. Test WITH Schema
    # Schema says: Q2, Q3, Q9, Q9a, Q9b. 
    # Wait, usually schema from QP might just say Q9? 
    # If QP describes Q9 as one question, then we expect 9a/9b to NOT be extracted?
    # The user said: "2a or 2b in answer sheet ... parts are only in 16 mark question thats are 7,8,9,10"
    # So 7,8,9,10 HAVE parts. 2 DOES NOT.
    
    schema_keys = ['2', '3', '9', '9a', '9b'] 
    # Note: If QP parser finds 9a, 9b, then we pass them. 
    # If QP parser only finds '9', then we might suppress 9a, 9b?
    # The user implied 7,8,9,10 have (a,b). So the QP parser SHOULD find them.
    
    print("\n--- Test WITH Schema ---")
    q_with_schema = parser.parse_text_to_questions(text, expected_keys=schema_keys)
    print(f"Keys (With Schema): {sorted(q_with_schema.keys())}")
    
    # Assertions
    if '2a' in q_with_schema:
         print("FAIL: 2a found despite not being in schema.")
    else:
         print("PASS: 2a correctly ignored.")
         
    if '9a' in q_with_schema:
         print("PASS: 9a correctly found (it is in schema).")
    else:
         print("FAIL: 9a missed.")

if __name__ == "__main__":
    test_schema_aware_splitting()
