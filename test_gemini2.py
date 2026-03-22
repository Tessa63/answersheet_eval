import os
import time

os.environ["GEMINI_API_KEY"] = "AIzaSyA1cTVbWHQsw4m_wzLHypXfomSc_ZtZoWk"
api_key = os.environ["GEMINI_API_KEY"]

try:
    from google import genai
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model='gemini-1.5-flash',
        contents='Test prompt',
    )
    print("Gemini Success:", response.text)
except Exception as e:
    import traceback
    print("Gemini Error:")
    traceback.print_exc()
