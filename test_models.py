import os
os.environ["GEMINI_API_KEY"] = "AIzaSyA1cTVbWHQsw4m_wzLHypXfomSc_ZtZoWk"
from google import genai

client = genai.Client()
try:
    models = client.models.list()
    for m in models:
        print(m.name)
except Exception as e:
    print("Error listing models:", e)
