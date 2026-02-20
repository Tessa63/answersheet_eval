import sys
from scoring import SemanticScorer

def test_aggregation():
    scorer = SemanticScorer()
    
    print("\n--- Testing Sub-part Aggregation ---")
    
    # Model has Question 1
    model_segments = {
        "1": "Photosynthesis is the process used by plants to convert light energy into chemical energy. It occurs in chloroplasts."
    }
    
    # Student has Question 1a and 1b (split)
    student_segments = {
        "1a": "Photosynthesis is the process used by plants.",
        "1b": "It converts light energy into chemical energy and occurs in chloroplasts.",
        "2": "Something else."
    }
    
    # Mock Schema
    schema = {
        "1": {"max_marks": 10, "type": "mandatory", "group": "1"}
    }
    
    print("Evaluating...")
    results = scorer.evaluate_exam(student_segments, model_segments, question_schema=schema)
    
    # We expect determining Q1 score based on COMBINED 1a + 1b
    # If it works, Q1 score should be high.
    # If it fails (matches only 1a), score might be lower (partial).
    
    q1_result = next((r for r in results["breakdown"] if r["question"] == "1"), None)
    
    if q1_result:
        print(f"Q1 Score: {q1_result['score']}/{q1_result['max_marks']}")
        print(f"Feedback: {q1_result['feedback']}")
        
        if "aggregated" in q1_result.get("feedback", ""):
            print("SUCCESS: Aggregation detected in feedback.")
        else:
            print("FAILURE: No aggregation mentioned in feedback.")
            
        if q1_result['score'] > 8:
             print("SUCCESS: High score indicates full context was used.")
        else:
             print(f"WARNING: Score {q1_result['score']} seems low for a perfect split answer.")

if __name__ == "__main__":
    test_aggregation()
