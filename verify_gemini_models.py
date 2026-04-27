import os
import time
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    # Try hardcoded key found in test_gemini2.py fallback if not in .env
    api_key = "AIzaSyDykJ2G2-0hLCCrRyVbDqmPzsKHuQzLxQ4"

print(f"Using API Key: {api_key[:10]}...")

# ══════════════════════════════════════════════════════════════════════════
#  TEST CONFIGURATIONS
# ══════════════════════════════════════════════════════════════════════════

# These match ai_evaluator.py
gemini_models = [
    ("models/gemini-2.5-flash", "Gemini 2.5 Flash"),
    ("models/gemini-3-flash-preview", "Gemini 3 Flash Preview"),
    ("models/gemini-2.0-flash", "Gemini 2.0 Flash"),
    ("models/gemini-1.5-flash", "Gemini 1.5 Flash"),
]

def test_model(model_id, label, api_version='v1'):
    print(f"\n--- Testing {label} ({model_id}) [API {api_version}] ---")
    try:
        client = genai.Client(api_key=api_key, http_options={'api_version': api_version})
        response = client.models.generate_content(
            model=model_id,
            contents="Say 'Status: OK' if you are working."
        )
        print(f"SUCCESS: {response.text.strip()}")
        return True
    except Exception as e:
        print(f"FAILED: {e}")
        return False

# ══════════════════════════════════════════════════════════════════════════
#  EXECUTION
# ══════════════════════════════════════════════════════════════════════════

results = []
for m_id, label in gemini_models:
    # Try v1 first (as in ai_evaluator.py)
    success = test_model(m_id, label, api_version='v1')
    results.append((label, "v1", success))
    
    # If it failed, try v1beta as well just to check
    if not success:
        success_beta = test_model(m_id, label, api_version='v1beta')
        results.append((label, "v1beta", success_beta))

print("\n" + "="*40)
print("FINAL SUMMARY")
print("="*40)
for label, ver, res in results:
    status = "WORKING" if res else "NOT WORKING"
    print(f"{label:<20} | {ver:<8} | {status}")
print("="*40)
