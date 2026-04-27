import os
from google import genai
from google.genai import types

os.environ["GEMINI_API_KEY"] = "AIzaSyDykJ2G2-0hLCCrRyVbDqmPzsKHuQzLxQ4"
client = genai.Client()

prompt = "Output a simple message."
response = client.models.generate_content(
    model="gemini-2.0-flash",
    contents=prompt,
    config=types.GenerateContentConfig(
        response_mime_type="application/json",
        system_instruction="You are a helpful assistant. Output JSON with a 'message' field.",
        temperature=0.0
    )
)
print("gemini-2.5-flash response:", response.text)
