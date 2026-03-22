"""
llm_scorer.py — LLM-based answer grading module
================================================
Priority order:
  1. Together AI  (set TOGETHER_API_KEY env var — free at api.together.ai)
  2. Groq API     (set GROQ_API_KEY env var — free at console.groq.com)
  3. Local HuggingFace DeepSeek-R1 1.5B  (works offline, slower)
  4. Returns None → caller falls back to SemanticScorer
"""

import os
import re
import time

# ---- Shared helpers -------------------------------------------------------

def _build_prompt(student_text: str, model_text: str, max_marks: int) -> str:
    return f"""You are a human evaluator grading a student's handwritten exam answer.

MODEL ANSWER:
\"\"\"{model_text.strip()}\"\"\"

STUDENT ANSWER:
\"\"\"{student_text.strip()}\"\"\"

MAXIMUM MARKS: {max_marks}

YOUR TASK:
1. Focus PURELY on the CONCEPTUAL UNDERSTANDING.
2. Ignore spelling mistakes, grammatical errors, and messy OCR text. The student's text natively comes from an OCR scanner, so words like "the" might look like "tthe" or "tne".
3. DO NOT look for exact keywords. If the student uses a synonym or explains the concept correctly in their own words, GIVE FULL MARKS.
4. Award partial marks (e.g. {max_marks * 0.5:.1f}/{max_marks}) if the student shows partial understanding of the concept.
5. Award 0 only if the answer is completely blank, or demonstrates zero understanding of the model answer's core concept.

Think critically and leniently. Think step-by-step.
On the FINAL LINE, you must output exactly:
SCORE: X.X/{max_marks}

Your grading:"""


def _parse_score(response_text: str, max_marks: int) -> float | None:
    m = re.search(r'SCORE\s*:\s*([\d.]+)\s*/\s*[\d.]+', response_text, re.IGNORECASE)
    if m:
        try:
            return min(float(m.group(1)), float(max_marks))
        except ValueError:
            pass
    candidates = re.findall(r'([\d.]+)\s*/\s*' + str(max_marks), response_text)
    if candidates:
        try:
            return min(float(candidates[-1]), float(max_marks))
        except ValueError:
            pass
    return None


def _extract_feedback(raw: str) -> str:
    part = re.split(r'SCORE\s*:', raw, flags=re.IGNORECASE)[0].strip()
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', part) if s.strip()]
    return " ".join(sentences[-2:]) if sentences else part[:200]


# ---- Backend 0: Google Gemini ---------------------------------------------
GEMINI_MODEL = "gemini-2.5-flash"

def _score_via_gemini(student_text: str, model_text: str, max_marks: int, api_key: str) -> dict | None:
    try:
        from google import genai
    except ImportError:
        print("[LLMScorer] google-genai not installed")
        return None

    try:
        client = genai.Client(api_key=api_key)
        prompt = _build_prompt(student_text, model_text, max_marks)
        t0 = time.time()
        time.sleep(2) # Throttle to avoid 15 RPM limit
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
        )
        elapsed = time.time() - t0
        raw = response.text or ""
        score = _parse_score(raw, max_marks)
        if score is None:
            return None
        print(f"[LLMScorer] Gemini: {score}/{max_marks}  ({elapsed:.1f}s)")
        return {"score": round(score, 1), "feedback": _extract_feedback(raw), "method": "gemini-llm"}
    except Exception as e:
        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
            print(f"[LLMScorer] Gemini quota exceeded, retrying in 15s...")
            time.sleep(15)
            try:
                response = client.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=prompt,
                )
                raw = response.text or ""
                score = _parse_score(raw, max_marks)
                if score is not None:
                    return {"score": round(score, 1), "feedback": _extract_feedback(raw), "method": "gemini-llm"}
            except Exception as e2:
                print(f"[LLMScorer] Gemini second error: {e2}")
        else:
            print(f"[LLMScorer] Gemini error: {e}")
        return None


# ---- Backend 1: Together AI -----------------------------------------------

TOGETHER_MODEL = "deepseek-ai/DeepSeek-R1-Distill-Llama-70B-free"
TOGETHER_API_URL = "https://api.together.xyz/v1/chat/completions"


def _score_via_together(student_text: str, model_text: str, max_marks: int, api_key: str) -> dict | None:
    try:
        import httpx
    except ImportError:
        print("[LLMScorer] httpx not available")
        return None

    prompt = _build_prompt(student_text, model_text, max_marks)
    try:
        t0 = time.time()
        resp = httpx.post(
            TOGETHER_API_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": TOGETHER_MODEL, "messages": [{"role": "user", "content": prompt}],
                  "max_tokens": 512, "temperature": 0.1},
            timeout=60,
        )
        elapsed = time.time() - t0
        if resp.status_code != 200:
            print(f"[LLMScorer] Together AI error {resp.status_code}: {resp.text[:300]}")
            return None
        raw = resp.json()["choices"][0]["message"]["content"] or ""
        score = _parse_score(raw, max_marks)
        if score is None:
            print(f"[LLMScorer] Together AI: could not parse score from: {raw[:200]}")
            return None
        print(f"[LLMScorer] Together AI: {score}/{max_marks}  ({elapsed:.1f}s)")
        return {"score": round(score, 1), "feedback": _extract_feedback(raw), "method": "together-llm"}
    except Exception as e:
        print(f"[LLMScorer] Together AI error: {e}")
        return None


# ---- Backend 2: Groq API --------------------------------------------------

GROQ_MODEL = "deepseek-r1-distill-llama-70b"


def _score_via_groq(student_text: str, model_text: str, max_marks: int, api_key: str) -> dict | None:
    try:
        from groq import Groq
    except ImportError:
        print("[LLMScorer] groq package not installed")
        return None
    try:
        client = Groq(api_key=api_key)
        prompt = _build_prompt(student_text, model_text, max_marks)
        t0 = time.time()
        response = client.chat.completions.create(
            model=GROQ_MODEL, messages=[{"role": "user", "content": prompt}],
            max_tokens=512, temperature=0.1,
        )
        elapsed = time.time() - t0
        raw = response.choices[0].message.content or ""
        score = _parse_score(raw, max_marks)
        if score is None:
            return None
        print(f"[LLMScorer] Groq: {score}/{max_marks}  ({elapsed:.1f}s)")
        return {"score": round(score, 1), "feedback": _extract_feedback(raw), "method": "groq-llm"}
    except Exception as e:
        print(f"[LLMScorer] Groq error: {e}")
        return None


# ---- Backend 3: Local HuggingFace -----------------------------------------

_LOCAL_MODEL = None
_LOCAL_TOKENIZER = None
_LOCAL_MODEL_NAME = "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B"


def _load_local_model() -> bool:
    global _LOCAL_MODEL, _LOCAL_TOKENIZER
    if _LOCAL_MODEL is not None:
        return True
    try:
        from transformers import AutoTokenizer, AutoModelForCausalLM
        import torch
        print(f"[LLMScorer] Loading local model {_LOCAL_MODEL_NAME} (first run downloads ~3GB)...")
        _LOCAL_TOKENIZER = AutoTokenizer.from_pretrained(_LOCAL_MODEL_NAME, trust_remote_code=True)
        device = "cuda" if torch.cuda.is_available() else "cpu"
        _LOCAL_MODEL = AutoModelForCausalLM.from_pretrained(
            _LOCAL_MODEL_NAME, trust_remote_code=True,
            torch_dtype=torch.float16 if device == "cuda" else torch.float32,
            low_cpu_mem_usage=True,
        ).to(device)
        _LOCAL_MODEL.eval()
        print(f"[LLMScorer] Local model ready on {device.upper()}")
        return True
    except Exception as e:
        print(f"[LLMScorer] Failed to load local model: {e}")
        return False


def _score_via_local(student_text: str, model_text: str, max_marks: int) -> dict | None:
    if not _load_local_model():
        return None
    try:
        import torch
        prompt = _build_prompt(student_text, model_text, max_marks)
        inputs = _LOCAL_TOKENIZER(prompt, return_tensors="pt", truncation=True, max_length=1024)
        device = next(_LOCAL_MODEL.parameters()).device
        inputs = {k: v.to(device) for k, v in inputs.items()}
        t0 = time.time()
        with torch.no_grad():
            outputs = _LOCAL_MODEL.generate(
                **inputs, max_new_tokens=256, do_sample=False,
                temperature=1.0, pad_token_id=_LOCAL_TOKENIZER.eos_token_id,
            )
        elapsed = time.time() - t0
        raw = _LOCAL_TOKENIZER.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
        score = _parse_score(raw, max_marks)
        if score is None:
            return None
        print(f"[LLMScorer] Local DeepSeek-R1 1.5B: {score}/{max_marks}  ({elapsed:.1f}s)")
        return {"score": round(score, 1), "feedback": _extract_feedback(raw), "method": "local-llm"}
    except Exception as e:
        print(f"[LLMScorer] Local model error: {e}")
        return None


# ---- Public class ---------------------------------------------------------

class LLMScorer:
    """
    Priority: Together AI → Groq → Local HuggingFace → None (semantic fallback).
    Set TOGETHER_API_KEY or GROQ_API_KEY env vars to activate cloud backends.
    """

    def __init__(self):
        self.gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
        self.together_key = os.environ.get("TOGETHER_API_KEY", "").strip()
        self.groq_key = os.environ.get("GROQ_API_KEY", "").strip()
        self._groq_available = False
        try:
            import groq  # noqa
            self._groq_available = True
        except ImportError:
            pass

        if self.gemini_key:
            print(f"[LLMScorer] Gemini key detected — using {GEMINI_MODEL}")
        elif self.together_key:
            print(f"[LLMScorer] Together AI key detected — using {TOGETHER_MODEL}")
        elif self.groq_key and self._groq_available:
            print(f"[LLMScorer] Groq key detected — using {GROQ_MODEL}")
        else:
            print("[LLMScorer] No API key — will use local DeepSeek-R1 1.5B on first evaluation")

    def score_answer(self, student_text: str, model_text: str, max_marks: int = 5) -> dict | None:
        if not student_text or not model_text:
            return None
        s = student_text.strip()[:800]
        m = model_text.strip()[:800]

        if self.gemini_key:
            r = _score_via_gemini(s, m, max_marks, self.gemini_key)
            if r: return r

        if self.together_key:
            r = _score_via_together(s, m, max_marks, self.together_key)
            if r: return r

        if self.groq_key and self._groq_available:
            r = _score_via_groq(s, m, max_marks, self.groq_key)
            if r: return r

        return _score_via_local(s, m, max_marks)


# ---- Quick test -----------------------------------------------------------

if __name__ == "__main__":
    scorer = LLMScorer()
    r = scorer.score_answer(
        student_text="Patents give inventors exclusive rights for 20 years.",
        model_text="A patent grants the inventor exclusive rights to manufacture and sell the invention for 20 years.",
        max_marks=3
    )
    print("Result:", r)
