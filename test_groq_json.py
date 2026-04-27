import os
import json
from dotenv import load_dotenv
load_dotenv()
from ai_evaluator import _grade_with_built_in

prompt = """Grade the following student exam answers based on the official model answer key.

=== STUDENT'S HANDWRITTEN ANSWER (OCR) ===
Question 1. IP protection is needed because it protects inventions.

=== MODEL ANSWER (official answer key) ===
Q1: Intellectual property protection is necessary to protect inventions and encourage innovation.

Return ONLY the JSON object starting with {
"questions": ["""

try:
    res, method = _grade_with_built_in(prompt)
    print("SUCCESS!")
    print(json.dumps(res, indent=2))
except Exception as e:
    print("FAILED:", e)
