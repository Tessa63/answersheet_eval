import os

# Intentionally clear API keys to prove local works standalone
if "GEMINI_API_KEY" in os.environ: del os.environ["GEMINI_API_KEY"]
if "GROQ_API_KEY" in os.environ: del os.environ["GROQ_API_KEY"]

from ai_evaluator import evaluate_exam

s_pdf = "c:/Users/hp/answersheet_eval/uploads/student_student_answer.pdf"
m_pdf = "c:/Users/hp/answersheet_eval/uploads/model_Model answer.pdf"
q_pdf = "c:/Users/hp/answersheet_eval/uploads/question_Question paper.pdf"

try:
    print(f"Testing Local Evaluator over:\nStudent: {s_pdf}\nModel: {m_pdf}\nQuestion: {q_pdf}\n")
    res = evaluate_exam(s_pdf, m_pdf, q_pdf)
    print("\n--- GRADING RESULT ---")
    print(f"Total Score: {res['total_score']} / {res['max_score']}")
    print(f"Method Used: {res['grading_api']}")
    for q in res['breakdown']:
        if q['selected']:
            print(f"Q{q['question']} - {q['score']}/{q['max_marks']} -> {q['feedback']}")
except Exception as e:
    import traceback
    traceback.print_exc()
