import os
import json
from google import genai
from google.genai import types

def evaluate_exam_with_gemini(student_pdf_path: str, model_pdf_path: str, question_pdf_path: str = None) -> dict:
    """
    Uploads the PDFs to Gemini File API and uses Gemini 2.5 Flash 
    to evaluate the student's answers based on the model answers and question paper.
    Returns the JSON dictionary expected by the frontend.
    """
    api_key = os.environ.get("GEMINI_API_KEY", "AIzaSyA1cTVbWHQsw4m_wzLHypXfomSc_ZtZoWk")
    os.environ["GEMINI_API_KEY"] = api_key
    client = genai.Client()

    uploaded_files = []
    try:
        # 1. Upload files
        print("[AI Evaluator] Uploading Student Answer...")
        s_file = client.files.upload(file=student_pdf_path)
        uploaded_files.append(s_file)

        print("[AI Evaluator] Uploading Model Answer...")
        m_file = client.files.upload(file=model_pdf_path)
        uploaded_files.append(m_file)

        contents = [
            "You are an expert grading assistant. You are given a student's answer sheet (which might be handwritten), the official model answers, and the question paper.",
            "Your task is to grade the student's answer sheet fairly and accurately.",
            "1. First, identify all questions and their maximum marks from the Question Paper (if provided) or infer from the Model Answers.",
            "2. Read the student's answer sheet. Identify which answer corresponds to which question. (Note: the student might answer them out of order).",
            "3. Compare the student's answer against the core concepts in the Model Answer.",
            "4. Assign a score out of the maximum marks for that question based on conceptual correctness. Be strict and consistent: Give 100% marks for a full conceptual match, 50% for a partial match, and 0% for incorrect/missing concepts.",
            "5. Carefully read the Question Paper to identify 'OR' questions. An 'OR' choice is often between two full question numbers (e.g., 'Question 7 OR Question 8', or 'Question 9 OR Question 10'). The student will answer only one of them. For the question they answered, grade it and set 'selected': true. For the question they did NOT answer, set 'selected': false and 'score': 0. Both questions must appear in your breakdown, but only one can be 'selected': true.",
            "6. Identify if a question is a 'challenge' question (for example, Question 11). If it is a challenge question, set its 'type' to 'challenge' rather than 'normal'. Challenge questions do not count towards the regular exam total.",
            "Return a JSON object with this exact structure:",
            """
            {
              "total_score": 0,
              "max_score": 0,
              "llm_used": true,
              "breakdown": [
                {
                  "question": "1",
                  "max_marks": 5,
                  "score": 4.5,
                  "feedback": "Student correctly identified X, but missed Y. The explanation is clear.",
                  "type": "normal",
                  "selected": true
                }
              ]
            }
            """
        ]

        if question_pdf_path:
            print("[AI Evaluator] Uploading Question Paper...")
            q_file = client.files.upload(file=question_pdf_path)
            uploaded_files.append(q_file)
            contents.append("File 1: Student Answer")
            contents.append(s_file)
            contents.append("File 2: Model Answer")
            contents.append(m_file)
            contents.append("File 3: Question Paper")
            contents.append(q_file)
        else:
            contents.append("File 1: Student Answer")
            contents.append(s_file)
            contents.append("File 2: Model Answer")
            contents.append(m_file)

        print("[AI Evaluator] Generating evaluation using Gemini 2.5 Flash...")
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.0
            )
        )
        
        print("[AI Evaluator] Evaluation generation complete.")
        result_json = response.text
        
        data = json.loads(result_json)
        
        # Post-process: Calculate totals to ensure accuracy
        # Exclude challenge questions and unselected OR alternatives from the exam totals
        calculated_total = sum(item.get("score", 0) for item in data.get("breakdown", []) if item.get("selected", True) and item.get("type", "normal") != "challenge")
        calculated_max = sum(item.get("max_marks", 0) for item in data.get("breakdown", []) if item.get("selected", True) and item.get("type", "normal") != "challenge")
        
        data["total_score"] = round(calculated_total, 1)
        data["max_score"] = round(calculated_max, 1)
        data["llm_used"] = True
        
        for item in data.get("breakdown", []):
            item["llm_method"] = "Gemini 2.5 Flash"
            if "type" not in item:
                item["type"] = "normal"
            if "selected" not in item:
                item["selected"] = True

        return data

    except Exception as e:
        print(f"[AI Evaluator] Error: {e}")
        raise e
    finally:
        # Cleanup files from Gemini storage
        for f in uploaded_files:
            try:
                client.files.delete(name=f.name)
                print(f"[AI Evaluator] Cleaned up file {f.name} from Gemini API.")
            except Exception as e:
                print(f"[AI Evaluator] Could not delete file {f.name}: {e}")
