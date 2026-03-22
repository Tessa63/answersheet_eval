"""
Full detailed evaluation of the IPR exam.
Reads all 3 sources, shows per-question content, and scores each.
"""
import sys
sys.path.append(r"c:\Users\hp\answersheet_eval")

from ocr_service import extract_text_from_file
from pdf_parser import PAGE_BREAK, parse_exam_file
from question_paper import parse_question_paper_file
from scoring import SemanticScorer

# == File Paths ==
QP_PDF     = r"c:\Users\hp\answersheet_eval\uploads\question_Question paper.pdf"
MODEL_PDF  = r"c:\Users\hp\answersheet_eval\uploads\model_WhatsApp Image 2026-03-13 at 9.39.41 AM.pdf"
STUDENT_PDF = r"c:\Users\hp\answersheet_eval\uploads\student_WhatsApp Image 2026-03-13 at 9.33.06 AM.pdf"

print("================================================================")
print(" FULL EVALUATION: IPR & CYBER LAWS (20MCA192)")
print("================================================================\n")

# 1. Question Paper
print("--- STEP 1: QUESTION PAPER SCHEMA ---")
q_schema = parse_question_paper_file(QP_PDF)
real_keys = sorted([k for k in q_schema if not k.startswith("_") and isinstance(q_schema.get(k), dict)],
                   key=lambda x: int(x) if x.isdigit() else 99)
print(f"Total marks: {q_schema.get('_total_marks')}")
for k in real_keys:
    v = q_schema[k]
    print(f"  Q{k}: {v['max_marks']} marks ({v['type']})")

# 2. Model Answer Parsing
print("\n--- STEP 2: MODEL ANSWER PARSING ---")
model_raw = extract_text_from_file(MODEL_PDF)
real_schema_keys = [k for k in q_schema if not k.startswith("_") and isinstance(q_schema.get(k), dict)]
schema_is_useful = len(real_schema_keys) >= 3
model_expected = real_schema_keys if schema_is_useful else None
model_segments = parse_exam_file(model_raw, expected_keys=model_expected)
print(f"Model keys found: {sorted(model_segments.keys())}")

# 3. Student Answer Parsing
print("\n--- STEP 3: STUDENT ANSWER PARSING ---")
student_raw = extract_text_from_file(STUDENT_PDF)
expected_keys = list(model_segments.keys())
for k in real_schema_keys:
    if k not in expected_keys:
        expected_keys.append(k)
student_segments = parse_exam_file(student_raw, expected_keys=expected_keys)
print(f"Student keys found: {sorted(student_segments.keys())}")

# 4. Print per-question content comparison
print("\n--- STEP 4: CONTENT COMPARISON ---")
for k in real_keys:
    m_text = model_segments.get(k, "[NO MODEL ANSWER]")
    s_text = student_segments.get(k, "[NOT FOUND IN STUDENT]")
    print(f"\n  Q{k} (max {q_schema[k]['max_marks']} marks):")
    print(f"    MODEL : {m_text[:150].replace(chr(10),' ')}...")
    print(f"    STUDENT: {s_text[:150].replace(chr(10),' ')}...")

# 5. Run scoring
print("\n--- STEP 5: EVALUATION ---")
scorer = SemanticScorer()
results = scorer.evaluate_exam(student_segments, model_segments, question_schema=q_schema)

print(f"\n================================================================")
print(f" FINAL SCORE: {results['total_score']} / {results['max_score']}")
pct = round(results['total_score'] / results['max_score'] * 100, 1) if results['max_score'] > 0 else 0
print(f" PERCENTAGE: {pct}%")
print(f"================================================================\n")

for r in results['breakdown']:
    sel = "✓" if r.get('selected') else "✗"
    bar_pct = r['score'] / r['max_marks'] if r['max_marks'] > 0 else 0
    bar = "█" * int(bar_pct * 10) + "░" * (10 - int(bar_pct * 10))
    print(f"  {sel} Q{r['question']:3s}: {r['score']:4.1f}/{r['max_marks']:2d}  [{bar}]  {r['feedback'][:70]}")
