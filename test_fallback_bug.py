
from pdf_parser import parse_exam_file

def test_fallback_bug():
    # Text with NO question numbers, just content
    # Should trigger fallback
    text = """
    Muthoot Institute of Technology & Science
    INTERNAL EXAMINATION
    
    This is the answer for question 1. The quick brown fox jumps over the lazy dog.
    It is a very long answer covering multiple lines.
    
    This is the answer for question 2. It is also quite long and detailed.
    We expect the parser to pick this up even without '2.' prefix.
    
    This is the answer for question 3. Finally, the last answer.
    """
    
    # Expected keys
    expected = ['1', '2', '3']
    
    print("--- Testing Fallback Logic ---")
    segments = parse_exam_file(text, expected_keys=expected)
    
    print(f"Segments found: {sorted(segments.keys())}")
    
    if segments.get('1'):
        print(f"Q1 Content: {segments['1'][:50]}...")
    else:
        print("Q1 MISSING!")
        
    if segments.get('2'):
        print(f"Q2 Content: {segments['2'][:50]}...")
    
    # Check if Q1 content was truncated (due to 40% drop)
    if segments.get('1') and "answer for question 1" in segments['1']:
        print("PASS: Q1 content preserved.")
    else:
        print("FAIL: Q1 content lost (likely due to 40% drop bug).")

if __name__ == "__main__":
    test_fallback_bug()
