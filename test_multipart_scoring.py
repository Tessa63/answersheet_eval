
from scoring import SemanticScorer

def test_multipart_aggregation():
    scorer = SemanticScorer()
    
    # Schema:
    # Q7 (Group 7, Optional). 7a (8 marks), 7b (8 marks).
    # Q8 (Group 7, Optional). 8 (16 marks).
    # Q9 (Group 9). 9a, 9b. (Mandatory? No, usually OR with 10).
    
    schema = {
        "7a": {"max_marks": 8, "group": "7", "type": "optional"},
        "7b": {"max_marks": 8, "group": "7", "type": "optional"},
        "8":  {"max_marks": 16, "group": "7", "type": "optional"},
    }
    
    model_segments = {
        "7a": "Photosynthesis is process of making food.",
        "7b": "Mitochondria is powerhouse of cell.",
        "8": "Newton's laws of motion explain forces."
    }
    
    # Case 1: Student answers 7a, 7b well. Q8 is empty.
    # Expectation: 7a, 7b selected. Total score high.
    student_segments_1 = {
        "7a": "Photosynthesis is how plants make food using sunlight.",
        "7b": "Mitochondria generates energy for the cell.",
    }
    
    print("\n--- Test Case 1: Student attempts 7a, 7b ---")
    results_1 = scorer.evaluate_exam(student_segments_1, model_segments, question_schema=schema)
    
    # Check if 7a, 7b are selected
    sel_7a = next((x for x in results_1['breakdown'] if x['question'] == '7a'), None)
    sel_7b = next((x for x in results_1['breakdown'] if x['question'] == '7b'), None)
    sel_8  = next((x for x in results_1['breakdown'] if x['question'] == '8'), None)
    
    print(f"7a Selected: {sel_7a['selected']} (Score: {sel_7a['score']})")
    print(f"7b Selected: {sel_7b['selected']} (Score: {sel_7b['score']})")
    print(f"8  Selected: {sel_8['selected']} (Score: {sel_8['score']})")
    
    if sel_7a['selected'] and sel_7b['selected'] and not sel_8['selected']:
        print("PASS: 7a/7b selected over 8.")
    else:
        print("FAIL: Selection logic wrong.")

    # Case 2: Student answers 8 well. 7a, 7b empty.
    student_segments_2 = {
        "8": "Newton's first law states object stays at rest. Second law F=ma. Third law action reaction."
    }
    
    print("\n--- Test Case 2: Student attempts 8 ---")
    results_2 = scorer.evaluate_exam(student_segments_2, model_segments, question_schema=schema)
    
    sel_7a_2 = next((x for x in results_2['breakdown'] if x['question'] == '7a'), None)
    sel_8_2  = next((x for x in results_2['breakdown'] if x['question'] == '8'), None)
    
    print(f"7a Selected: {sel_7a_2['selected']}")
    print(f"8  Selected: {sel_8_2['selected']} (Score: {sel_8_2['score']})")
    
    if sel_8_2['selected'] and not sel_7a_2['selected']:
        print("PASS: 8 selected over 7a/7b.")
    else:
        print("FAIL: Selection logic wrong.")

if __name__ == "__main__":
    test_multipart_aggregation()
