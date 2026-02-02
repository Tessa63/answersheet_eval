import sys
import os

# Ensure we can import from the directory
sys.path.append(os.getcwd())

from scoring import SemanticScorer

def test_scoring():
    scorer = SemanticScorer()
    
    print("\n--- Test Case 1: Ideal Scenario ---")
    model_ans = "Photosynthesis is the process by which green plants use sunlight to synthesize nutrients from carbon dioxide and water. It involves chlorophyll."
    student_ans = "Photosynthesis is process where plants use sunlight for nutrients from co2 and water. Chlorophyll is used."
    res = scorer.evaluate_single_answer(student_ans, model_ans)
    print(f"Score: {res['score']}/10")
    print(f"Details: {res['details']}")

    print("\n--- Test Case 2: Messy OCR (No punctuation, typos) ---")
    # Simulating what OCR usually outputs: newlines instead of dots, some typos
    student_ans_messy = "photosynthsis process where plants use sun light \n for nutriens from co2 and water \n clorophyl is used"
    res = scorer.evaluate_single_answer(student_ans_messy, model_ans)
    print(f"Score: {res['score']}/10")
    print(f"Feedback: {res['feedback']}")
    print(f"Details: {res['details']}")
    
    print("\n--- Test Case 3: Partial Answer ---")
    student_ans_partial = "Plants use sunlight."
    res = scorer.evaluate_single_answer(student_ans_partial, model_ans)
    print(f"Score: {res['score']}/10")
    print(f"Feedback: {res['feedback']}")
    print(f"Details: {res['details']}")

    print("\n--- Test Case 4: Contextual Rephrasing (High Level) ---")
    student_ans_rephrase = "Green flora utilize solar radiation to create food from H2O and Carbon Dioxide. This mechanism relies on green pigment."
    res = scorer.evaluate_single_answer(student_ans_rephrase, model_ans)
    print(f"Score: {res['score']}/10")
    print(f"Feedback: {res['feedback']}")
    print(f"Details: {res['details']}")

if __name__ == "__main__":
    test_scoring()
