import os
import json
import sys
from dotenv import load_dotenv
load_dotenv()
sys.stdout.reconfigure(encoding='utf-8')
from ai_evaluator import _build_grading_prompt, _grade_with_failover, _normalize_breakdown

STUDENT_OCR_PATH = r"c:\Users\hp\answersheet_eval\.ocr_cache\c2551e0db975a8965b640fac39d95c2c_hw.txt"
MODEL_OCR_PATH = r"c:\Users\hp\answersheet_eval\.ocr_cache\4867f0111fbd7cfd2db2dcc04839e233_pr.txt"

def reproduce():
    if not os.path.exists(STUDENT_OCR_PATH): return
    with open(STUDENT_OCR_PATH, "r", encoding="utf-8") as f:
        student_text = f.read()
    with open(MODEL_OCR_PATH, "r", encoding="utf-8") as f:
        model_text = f.read()

    print("Building prompt...")
    prompt = _build_grading_prompt(student_text, model_text[:5000], "PART A\n1. IP (3 marks)")

    print("Sending to LLM...")
    try:
        raw_breakdown, grading_api = _grade_with_failover(prompt)
        print(f"Grading API used: {grading_api}")
        breakdown = _normalize_breakdown(raw_breakdown, grading_api)
        with open("repro_results.json", "w", encoding="utf-8") as f:
            json.dump(breakdown, f, indent=2)
        print("Success! Results saved.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    reproduce()
