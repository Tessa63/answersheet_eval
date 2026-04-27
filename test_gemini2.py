import os
import time

os.environ["GEMINI_API_KEY"] = "AIzaSyDykJ2G2-0hLCCrRyVbDqmPzsKHuQzLxQ4"
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
