import os
import sys
import traceback

os.environ["TOGETHER_API_KEY"] = "key_CZ83KK2mqEWypbzDtU4Eh"
os.environ["GEMINI_API_KEY"] = "AIzaSyA1cTVbWHQsw4m_wzLHypXfomSc_ZtZoWk"
from llm_scorer import _score_via_gemini, _score_via_together, _score_via_local

def test_backends():
    student_text = "Patents give 20 years"
    model_text = "Patents give 20 years of exclusive rights."
    max_marks = 3
    
    print("--- Testing Gemini ---")
    try:
        import google.generativeai as genai
        genai.configure(api_key=os.environ["GEMINI_API_KEY"])
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content("Hello")
        print("Gemini response:", response.text[:50])
    except Exception as e:
        print("Gemini Failed:", e)
        traceback.print_exc()

    print("\n--- Testing Together ---")
    try:
        res = _score_via_together(student_text, model_text, max_marks, os.environ["TOGETHER_API_KEY"])
        print("Together Res:", res)
    except Exception as e:
        print("Together Failed:", e)
        traceback.print_exc()
        
    print("\n--- Testing Local ---")
    try:
        res = _score_via_local(student_text, model_text, max_marks)
        print("Local Res:", res)
    except Exception as e:
        print("Local Failed:", e)
        traceback.print_exc()

with open("llm_test_output.txt", "w") as f:
    sys.stdout = f
    sys.stderr = f
    test_backends()
