import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

key = os.getenv("OPENROUTER_API_KEY")

def test_openrouter():
    print(f"Testing OpenRouter with key: {key[:10]}...")
    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {key}",
            },
            data=json.dumps({
                "model": "openai/gpt-4o-mini",
                "messages": [{"role": "user", "content": "Say 'OpenRouter is working'"}],
            })
        )
        print(f"Status: {response.status_code}")
        print(f"Result: {response.json()['choices'][0]['message']['content']}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_openrouter()
