"""
Test that scoring properly scales to question paper max marks.
"""
from scoring import SemanticScorer

def test_qp_scoring():
    scorer = SemanticScorer()
    
    # Schema: each question has different max marks (like a real question paper)
    schema = {
        "1": {"max_marks": 6, "type": "mandatory", "group": "1"},
        "2": {"max_marks": 10, "type": "mandatory", "group": "2"},
        "3": {"max_marks": 4, "type": "mandatory", "group": "3"},
    }
    
    model_segments = {
        "1": "Decision tree pruning is a technique to reduce the size of decision trees by removing sections that provide little power to classify instances. Pruning reduces the complexity of the final classifier and hence improves predictive accuracy by the reduction of overfitting.",
        "2": "Supervised learning is a type of machine learning where the model is trained on labeled data. The algorithm learns from the training data and makes predictions. Examples include linear regression, decision trees, and neural networks. It requires input-output pairs for training.",
        "3": "Overfitting occurs when a model learns the training data too well, including noise and outliers, resulting in poor generalization to new data.",
    }
    
    # Test 1: Good answers
    student_good = {
        "1": "Pruning in decision trees means cutting branches that dont help classification. It reduces complexity and prevents overfitting, improving accuracy on new data.",
        "2": "Supervised learning trains models using labeled data with input-output pairs. The algorithm learns patterns from training examples. Common algorithms include linear regression, decision trees, and neural networks.",
        "3": "Overfitting happens when the model memorizes training data including noise, so it performs badly on unseen data.",
    }
    
    print("\n=== TEST 1: Good Answers ===")
    results = scorer.evaluate_exam(student_good, model_segments, question_schema=schema)
    print(f"Total: {results['total_score']} / {results['max_score']}")
    for item in results['breakdown']:
        print(f"  Q{item['question']}: {item['score']}/{item['max_marks']} - {item['feedback']}")
    
    # Good answers should score well relative to max marks
    for item in results['breakdown']:
        ratio = item['score'] / item['max_marks'] if item['max_marks'] > 0 else 0
        assert ratio > 0.5, f"Q{item['question']}: Expected >50% but got {ratio*100:.0f}% ({item['score']}/{item['max_marks']})"
        print(f"  [OK] Q{item['question']}: {ratio*100:.0f}% -- PASS")
    
    # Test 2: Partial answers
    student_partial = {
        "1": "Pruning means removing parts of a tree.",
        "2": "Supervised learning is when you train a model.",
        "3": "Overfitting is bad for models.",
    }
    
    print("\n=== TEST 2: Partial Answers ===")
    results2 = scorer.evaluate_exam(student_partial, model_segments, question_schema=schema)
    print(f"Total: {results2['total_score']} / {results2['max_score']}")
    for item in results2['breakdown']:
        ratio = item['score'] / item['max_marks'] if item['max_marks'] > 0 else 0
        print(f"  Q{item['question']}: {item['score']}/{item['max_marks']} ({ratio*100:.0f}%) - {item['feedback']}")
    
    # Test 3: Empty/no answers
    student_empty = {
        "1": "",
        "2": "",
    }
    
    print("\n=== TEST 3: Empty Answers ===")
    results3 = scorer.evaluate_exam(student_empty, model_segments, question_schema=schema)
    print(f"Total: {results3['total_score']} / {results3['max_score']}")
    for item in results3['breakdown']:
        print(f"  Q{item['question']}: {item['score']}/{item['max_marks']} - {item['feedback']}")
        if item['feedback'] in ("Empty answer", "Not Attempted"):
            assert item['score'] == 0, f"Q{item['question']}: empty answer should score 0"
            print(f"  [OK] Q{item['question']}: 0 marks -- PASS")
    
    print("\n=== All Tests Passed! ===")

if __name__ == "__main__":
    test_qp_scoring()
