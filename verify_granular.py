import os
from ai_evaluator import evaluate_exam
from dotenv import load_dotenv

load_dotenv()

def test_granular():
    # Test with the High Scored sheet
    student = "uploads/student_Answersheet (1)_organized.pdf"
    model = "uploads/model_Model answer.pdf"
    question = "uploads/question_Question paper.pdf"
    
    print("Testing Granular Evaluation...")
    result = evaluate_exam(student, model, question)
    print("\n--- RESULTS ---")
    print(f"Total: {result['total_score']}/{result['max_score']}")
    print(f"Method: {result['grading_api']}")
    for item in result['breakdown']:
        print(f"Q{item['question']}: {item['score']} marks - {item['feedback'][:50]}...")

if __name__ == "__main__":
    test_granular()
