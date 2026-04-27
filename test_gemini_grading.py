import os, sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv()
from ai_evaluator import _build_grading_prompt, _grade_with_gemini_chain

student = "Q1: IP stands for Intellectual Property. It protects creative works and inventions."
model   = "Q1 (3 marks): Intellectual Property (IP) refers to creations of the mind such as inventions, literary works, symbols, names, and images used in commerce."
q_paper = "Q1. What is Intellectual Property? (3 marks)"

prompt = _build_grading_prompt(student, model, q_paper)
print(f"Prompt length: {len(prompt)} chars")
result, label = _grade_with_gemini_chain(prompt)
print(f"SUCCESS via: {label}")
print(f"Questions graded: {len(result)}")
for q in result:
    qn = q.get("question","?")
    sc = q.get("score","?")
    mx = q.get("max_marks","?")
    fb = str(q.get("feedback",""))[:80]
    print(f"  Q{qn}: {sc}/{mx} - {fb}")
