import os
import json
from ai_evaluator import evaluate_exam
from dotenv import load_dotenv

load_dotenv()

def run_granular_comparison():
    model_path = "uploads/model_Model answer.pdf"
    question_path = "uploads/question_Question paper.pdf"
    
    # 1. High Scored Student
    high_path = "uploads/student_Answersheet (1)_organized.pdf"
    print(f"\n--- EVALUATING HIGH SCORED STUDENT ---")
    high_res = evaluate_exam(high_path, model_path, question_path)
    
    # 2. Low Scored Student
    low_path = "uploads/student_Answersheet Low.pdf"
    print(f"\n--- EVALUATING LOW SCORED STUDENT ---")
    low_res = evaluate_exam(low_path, model_path, question_path)
    
    final_output = {
        "high_scored": high_res,
        "low_scored": low_res
    }
    
    with open("granular_evaluation_results.json", "w", encoding="utf-8") as f:
        json.dump(final_output, f, indent=2)
    
    print("\n--- SUMMARY ---")
    print(f"High Scored: {high_res['total_score']}/{high_res['max_score']}")
    print(f"Low Scored: {low_res['total_score']}/{low_res['max_score']}")

if __name__ == "__main__":
    run_granular_comparison()
