import os
import json
from dotenv import load_dotenv
from ai_evaluator import _call_openrouter, _call_groq, _call_gemini, OPENROUTER_MODELS, GROQ_MODELS, GEMINI_MODELS

load_dotenv()

def verify():
    test_prompt = "Q1: Return a JSON object with a single field 'test': true."
    
    # 1. OpenRouter
    print("\n--- Testing OpenRouter (Primary) ---")
    try:
        res = _call_openrouter(OPENROUTER_MODELS[0][0], test_prompt)
        print(f"SUCCESS: {OPENROUTER_MODELS[0][1]}")
    except Exception as e:
        print(f"FAILED: {e}")

    # 2. Groq
    print("\n--- Testing Groq (Secondary) ---")
    try:
        res = _call_groq(GROQ_MODELS[0][0], test_prompt)
        print(f"SUCCESS: {GROQ_MODELS[0][1]}")
    except Exception as e:
        print(f"FAILED: {e}")

    # 3. Gemini
    print("\n--- Testing Gemini (Tertiary) ---")
    try:
        res = _call_gemini(GEMINI_MODELS[0][0], test_prompt)
        print(f"SUCCESS: {GEMINI_MODELS[0][1]}")
    except Exception as e:
        print(f"FAILED: {e}")

if __name__ == "__main__":
    verify()
