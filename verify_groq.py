
import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

key = os.getenv("GROQ_API_KEY")
client = Groq(api_key=key)

try:
    print(f"Testing Groq with key: {key[:10]}...")
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": "Say 'Groq is working'"}],
    )
    print(f"Result: {completion.choices[0].message.content}")
except Exception as e:
    print(f"Error: {e}")
