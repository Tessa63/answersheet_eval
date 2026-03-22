import os
from google import genai
from google.genai import types

os.environ["GEMINI_API_KEY"] = "AIzaSyA1cTVbWHQsw4m_wzLHypXfomSc_ZtZoWk"
client = genai.Client()

print("Uploading files...")
try:
    q_file = client.files.upload(file="c:/Users/hp/answersheet_eval/uploads/question_Question paper.pdf")
    m_file = client.files.upload(file="c:/Users/hp/answersheet_eval/uploads/model_Model answer.pdf")
    s_file = client.files.upload(file="c:/Users/hp/answersheet_eval/uploads/student_answer.pdf")

    print(f"Files uploaded successfully: {q_file.name}, {m_file.name}, {s_file.name}")

    print("Generating content...")
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=[
            "You are an expert examiner grading a student's answer sheet.",
            "File 1 is the Question Paper. File 2 is the Model Answer key. File 3 is the Student's handwritten Answer Sheet.",
            "Please evaluate the student's answer sheet based on the provided question paper and model answers.",
            "Return a JSON array of objects, where each object represents a graded question and has the following keys: 'question_number', 'max_marks', 'student_answer_summary', 'justification', 'score_awarded'.",
            q_file, m_file, s_file
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.2
        )
    )
    print("\n--- RESPONSE ---")
    print(response.text)
except Exception as e:
    print(f"Error: {e}")
