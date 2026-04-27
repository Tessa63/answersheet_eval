import os
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

def test_json_mode():
    api_key = os.environ.get("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key, http_options={"api_version": "v1beta"})
    
    print("Calling Gemini 2.5 Flash with JSON mode...")
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents="Return a JSON object with a 'test': 'success' field.",
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.0
        )
    )
    print("Response:")
    print(response.text)

if __name__ == "__main__":
    test_json_mode()
