from scoring import SemanticScorer

def test_scoring_upgrade():
    scorer = SemanticScorer()
    
    # 1. Define Schema with OR logic and Variable Marks
    schema = {
        "1": {"max_marks": 5, "type": "mandatory", "group": "1"},
        "2": {"max_marks": 10, "type": "mandatory", "group": "2"},
        "3": {"max_marks": 15, "type": "optional", "group": "group_3_4"}, # OR Group
        "4": {"max_marks": 15, "type": "optional", "group": "group_3_4"}  # OR Group
    }
    
    # 2. Mock Model Answers
    model_segments = {
        "1": "Photosynthesis is the process by which green plants make food.",
        "2": "Newton's laws of motion are three physical laws that lay the foundation for classical mechanics.",
        "3": "Mitochondria is the powerhouse of the cell.",
        "4": "The nucleus controls the activities of the cell."
    }
    
    # 3. Mock Student Answers
    # Student answers Q1 (Correct), Q2 (Bad), and BOTH Q3 and Q4 (Q3 good, Q4 better?)
    student_segments = {
        "1": "Photosynthesis is how plants make food using sunlight.",
        "2": "Gravity is a force.",
        "3": "Powerhouse of cell.",
        "4": "Nucleus is the brain of the cell controlling everything."
    }
    
    print("\n--- Running Evaluation ---")
    results = scorer.evaluate_exam(student_segments, model_segments, question_schema=schema)
    
    print(f"Total Score: {results['total_score']} / {results['max_score']}")
    
    print("\nBreakdown:")
    for item in results['breakdown']:
        status = "SELECTED" if item.get('selected') != False else "IGNORED" 
        print(f"Q{item['question']} [{status}]: {item['score']}/{item['max_marks']} -> {item['feedback']}")
        
    # Assertions
    # Q1: 5 marks max. Should be close to 5.
    q1 = next(x for x in results['breakdown'] if x['question'] == '1')
    assert q1['max_marks'] == 5
    assert q1['score'] > 3 # Good answer
    
    # Q2: 10 marks max. Bad answer.
    q2 = next(x for x in results['breakdown'] if x['question'] == '2')
    assert q2['max_marks'] == 10
    assert q2['score'] < 5
    
    # Q3/Q4: OR Group. Q4 is longer/better? Both should be evaluated, best selected.
    q3 = next(x for x in results['breakdown'] if x['question'] == '3')
    q4 = next(x for x in results['breakdown'] if x['question'] == '4')
    
    assert q3['max_marks'] == 15
    assert q4['max_marks'] == 15
    
    # Check selection logic
    selected_items = [x for x in results['breakdown'] if x.get('selected') != False and x['question'] in ['3', '4']]
    assert len(selected_items) == 1
    
    best_score = max(q3['score'], q4['score'])
    assert selected_items[0]['score'] == best_score
    
    print("\nVerification Passed!")

if __name__ == "__main__":
    test_scoring_upgrade()
