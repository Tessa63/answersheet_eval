import urllib.request
try:
    req = urllib.request.urlopen('http://localhost:11434/api/tags', timeout=2)
    print("Ollama is running!")
    print(req.read().decode('utf-8'))
except Exception as e:
    print("Ollama is not running:", e)
