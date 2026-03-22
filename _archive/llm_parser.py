import os
import json
import re

def _clean_json_response(text):
    text = text.strip()
    # Strip markdown code blocks if present
    if text.startswith('```'):
        text = re.sub(r'^```(?:json)?\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
    return text

def get_schema_from_llm(ocr_text: str) -> dict | None:
    """
    Given the OCR text of a question paper, uses an LLM to extract 
    the strict JSON schema of the exam.
    Returns the parsed dict or None if failure via all backends.
    """
    prompt = f"""You are an expert Question Paper Parser. I will give you OCR text from an exam.
Your job is to read carefully and determine the number of questions, the max marks for EACH question, and if it's a mandatory or challenge question.
Pay VERY close attention to section headers (e.g. "Answer any 5 questions, each carries 3 marks" => means the next 5 questions are 3 marks each).

OUTPUT FORMAT:
Return ONLY a valid JSON dictionary. No explanations, no markdown formatting.
The keys should be the simple question numbers ("1", "2", "3a").
The values must be a dictionary with:
- "max_marks": integer (e.g. 5)
- "type": "mandatory" (default), "optional" (if it's an OR choice), or "challenge" (if marked as challenge/bonus)
- "group": string representing the logical group (for OR choices, e.g. "7" and "8" might both belong to group "7" if it's "7 OR 8"). Default is same as question number.
Also include a special key "_total_marks" which is the total marks for the paper (integer).

Example output:
{{
  "1": {{"max_marks": 3, "type": "mandatory", "group": "1"}},
  "2": {{"max_marks": 3, "type": "mandatory", "group": "2"}},
  "3": {{"max_marks": 7, "type": "optional", "group": "3"}},
  "4": {{"max_marks": 7, "type": "optional", "group": "3"}},
  "5": {{"max_marks": 5, "type": "challenge", "group": "5"}},
  "_total_marks": 20
}}

QUESTION PAPER OCR TEXT:
\"\"\"
{ocr_text}
\"\"\"
"""
    
    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    groq_key = os.environ.get("GROQ_API_KEY", "").strip()
    together_key = os.environ.get("TOGETHER_API_KEY", "").strip()
    
    # 1. Try Gemini
    if gemini_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(prompt)
            return json.loads(_clean_json_response(response.text))
        except Exception as e:
            print(f"[LLMParser] Gemini failed: {e}")
            
    # 2. Try Groq
    if groq_key:
        try:
            from groq import Groq
            client = Groq(api_key=groq_key)
            response = client.chat.completions.create(
                model="llama3-70b-8192",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            return json.loads(_clean_json_response(response.choices[0].message.content))
        except Exception as e:
            print(f"[LLMParser] Groq failed: {e}")
            
    # 3. Try Together AI
    if together_key:
        try:
            import httpx
            resp = httpx.post(
                "https://api.together.xyz/v1/chat/completions",
                headers={"Authorization": f"Bearer {together_key}", "Content-Type": "application/json"},
                json={
                    "model": "meta-llama/Llama-3-70b-chat-hf", 
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1
                },
                timeout=60,
            )
            raw = resp.json()["choices"][0]["message"]["content"]
            return json.loads(_clean_json_response(raw))
        except Exception as e:
            print(f"[LLMParser] Together AI failed: {e}")

    # No valid keys or all failed
    print("[LLMParser] All LLM parsing backends failed or no API keys configured.")
    return None
