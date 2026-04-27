import os
os.environ["GEMINI_API_KEY"] = "AIzaSyDykJ2G2-0hLCCrRyVbDqmPzsKHuQzLxQ4"
from google import genai

client = genai.Client()
try:
    models = client.models.list()
    for m in models:
        print(m.name)
except Exception as e:
    print("Error listing models:", e)
