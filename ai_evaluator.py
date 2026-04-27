"""
ai_evaluator.py

Pipeline:
  - Upload PDFs directly to Gemini File API (native multimodal vision)
  - Gemini 2.5 Flash reads the handwritten answer sheet, model answers, and question paper
  - Returns structured JSON with per-question scores
  
This is the ORIGINAL working approach that produced 48-49 for high scorer
and 24-25 for low scorer.
"""

import os
import json
import re
import time
from google import genai
from google.genai import types


def _extract_json_from_text(text: str) -> str:
    """Safely extract a JSON block from LLM response text."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    return match.group(0) if match else text


def evaluate_exam_with_gemini(
    student_pdf_path: str,
    model_pdf_path: str,
    question_pdf_path: str = None,
    progress_callback=None,
) -> dict:
    """
    Uploads the PDFs to Gemini File API and uses Gemini 2.5 Flash
    to evaluate the student's answers based on the model answers and question paper.
    Returns the JSON dictionary expected by the frontend.
    """
    def _progress(step, msg):
        print(f"[AI Evaluator] {msg}")
        if progress_callback:
            progress_callback(step, msg)

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set.")

    client = genai.Client(api_key=api_key, http_options={"api_version": "v1beta"})
    uploaded_files = []

    try:
        # ── 1. Upload Files ──────────────────────────────────────────────
        _progress(1, "Running OCR on student answer sheet...")
        s_file = client.files.upload(file=student_pdf_path)
        uploaded_files.append(s_file)

        _progress(2, "Running OCR on model answer key...")
        m_file = client.files.upload(file=model_pdf_path)
        uploaded_files.append(m_file)

        q_file = None
        if question_pdf_path:
            _progress(3, "Running OCR on question paper...")
            q_file = client.files.upload(file=question_pdf_path)
            uploaded_files.append(q_file)

        # ── 2. Build Prompt ──────────────────────────────────────────────
        _progress(4, "Analyzing and grading all answers (AI Vision)...")

        contents = [
            # System Instructions
            """You are a GENEROUS and context-aware academic examiner grading a handwritten exam.

================  !! MOST IMPORTANT RULE — READ FIRST !! ================

★★ ATTEMPTED QUESTION DETECTION — MANDATORY STEP ★★

BEFORE grading anything, scan the student's handwritten answer sheet page by page and:
  1. Make a list of ONLY the question numbers the student PHYSICALLY WROTE on the paper.
     A question is "attempted" ONLY if you can see the student wrote the question number
     (e.g., "1)", "Q1.", "Ans 1", "1.", "Q.1") AND wrote content under it.
  2. If a question number does NOT appear anywhere on the student's paper → score = 0.
     The student did NOT attempt it. Do NOT infer, do NOT guess, do NOT assume.
  3. NEVER award marks for a question the student did not physically number and answer.
  4. Students often skip questions. A skipped question MUST be score: 0.

This rule OVERRIDES everything else. A hallucinated answer is WORSE than a 0.

================  GRADING PHILOSOPHY (for attempted questions only)  ================

★ SCORING METHOD: COUNT UP — NEVER COUNT DOWN ★
  1. Identify the KEY CONCEPTS/POINTS expected per question from the Model Answer.
  2. For each concept, check if the student expressed that idea — in ANY form or wording.
  3. ADD marks for each concept present. DO NOT subtract for missing concepts.
  4. Total score = sum of marks for concepts found.

★ CRITICAL RULES ★
  ✔ Student's OWN WORDS expressing correct MEANING = FULL marks for that point.
  ✔ Covering a concept BRIEFLY but correctly = FULL marks for that concept.
  ✔ If student covers ALL main points (even briefly) → FULL marks.
  ✘ NEVER deduct for: different phrasing, missing sub-details, spelling, OCR noise.
  ✘ NEVER penalize for not using exact textbook terms.
  ✘ Do NOT say 'lacks depth' to justify deduction — only deduct if a MAIN concept is absent.
  ☆ When in doubt — AWARD the mark. Benefit of the doubt always goes to the student.

================  EXAM STRUCTURE RULES  ================

1. PART A (Q1-Q5) = 3 marks each. PART B (Q6-Q10) = 7 marks each.
2. The student might answer in a different order — match by question number, not position.
3. For 'OR' questions (e.g., 'Q7 OR Q8'): grade both if attempted, set 'selected': true
   for the one the student chose, 'selected': false for the other.
4. Q11 is a CHALLENGE question: set 'type' to 'challenge'.
   Challenge questions do NOT count towards max_score (max_score stays at 50).
5. Every question from Q1–Q11 MUST appear in the breakdown — even if score is 0.
   For unattempted questions: score = 0, feedback = "Not attempted by student."

Return a JSON object with this EXACT structure (no markdown, no extra text):
{
  "total_score": 0,
  "max_score": 50,
  "llm_used": true,
  "breakdown": [
    {
      "question": "1",
      "max_marks": 3,
      "score": 2.5,
      "feedback": "Student correctly covered: [list what was correct].",
      "type": "normal",
      "selected": true
    }
  ]
}""",
        ]

        # Attach files with labels
        contents.append("=== FILE 1: STUDENT ANSWER SHEET (Handwritten) ===")
        contents.append(s_file)
        contents.append("=== FILE 2: MODEL ANSWER KEY ===")
        contents.append(m_file)
        if q_file:
            contents.append("=== FILE 3: QUESTION PAPER ===")
            contents.append(q_file)

        # ── 3. Generate Evaluation ───────────────────────────────────────
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.0,
            ),
        )

        _progress(4, "Evaluation complete. Calculating final scores...")
        result_json = _extract_json_from_text(response.text)
        data = json.loads(result_json)

        # ── 4. Post-Process: Recalculate Totals ──────────────────────────
        # Only count normal, selected questions. Q11 (challenge) never inflates max.
        breakdown = data.get("breakdown", [])

        calculated_total = sum(
            item.get("score", 0)
            for item in breakdown
            if item.get("selected", True) and item.get("type", "normal") != "challenge"
        )
        calculated_max = sum(
            item.get("max_marks", 0)
            for item in breakdown
            if item.get("selected", True) and item.get("type", "normal") != "challenge"
        )

        # Cap max_score at 50 regardless of what Gemini calculated
        if calculated_max == 0 or calculated_max > 55:
            calculated_max = 50

        data["total_score"] = round(calculated_total, 1)
        data["max_score"] = round(calculated_max, 1)
        data["llm_used"] = True
        data["ocr_method"] = "AI-Powered OCR (Gemini Vision)"
        data["grading_api"] = "Gemini 2.5 Flash"

        # Ensure all fields exist in breakdown items
        for item in breakdown:
            item.setdefault("llm_method", "Gemini 2.5 Flash")
            item.setdefault("type", "normal")
            item.setdefault("selected", True)

        print(f"[AI Evaluator] Final Score: {data['total_score']} / {data['max_score']}")
        return data

    except Exception as e:
        print(f"[AI Evaluator] Error: {e}")
        raise e

    finally:
        # Always clean up uploaded files from Gemini storage
        for f in uploaded_files:
            try:
                client.files.delete(name=f.name)
                print(f"[AI Evaluator] Cleaned up {f.name}")
            except Exception as cleanup_err:
                print(f"[AI Evaluator] Cleanup failed for {f.name}: {cleanup_err}")
