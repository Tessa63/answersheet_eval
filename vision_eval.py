import os
import json
import time
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

def evaluate_with_vision(student_path, model_path, question_path):
    genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
    
    print(f"Uploading files for vision analysis...")
    
    # Upload student answersheet
    student_file = genai.upload_file(path=student_path, display_name="Student Answersheet")
    # Upload model answer
    model_file = genai.upload_file(path=model_path, display_name="Model Answer")
    # Upload question paper
    question_file = genai.upload_file(path=question_path, display_name="Question Paper")
    
    # Verify processing status
    while student_file.state.name == "PROCESSING":
        print(".", end="", flush=True)
        time.sleep(2)
        student_file = genai.get_file(student_file.name)
    
    print("\nFiles uploaded and processed.")
    
    model = genai.GenerativeModel(model_name="gemini-1.5-flash")
    
    prompt = """You are a professional exam evaluator. You have been provided with three PDF files:
1. The Student's Handwritten Answer Sheet
2. The Official Model Answer Key
3. The Question Paper

Your task is to grade the student's work with 100% precision. 
Follow these steps:
1. Extract all questions from the Question Paper.
2. For each question, find the student's answer in the Handwritten Sheet. 
   - Note: The student may have answered questions out of order.
   - Use your advanced vision capabilities to read the handwriting accurately.
3. Compare the student's answer against the Model Answer Key.
4. Assign a score based on the marks allocated for each question.
   - Be strict but fair. Reward conceptual clarity.
   - PART A (Q1-Q5): 3 marks each.
   - PART B (Q6-Q10): 7 marks each.
   - Q11: 5 marks (Challenge).

Return a JSON object:
{
  "total_score": float,
  "max_score": 50.0,
  "breakdown": [
    {
      "question": "1",
      "score": float,
      "max_marks": 3.0,
      "feedback": "Detailed explanation of why this score was given.",
      "student_text_found": "Quote a few words from the student's answer to prove you found it."
    }
  ]
}
Return ONLY the JSON object.
"""

    response = model.generate_content([student_file, model_file, question_file, prompt])
    
    return response.text

if __name__ == "__main__":
    student = "uploads/student_Answersheet (1)_organized.pdf"
    model = "uploads/model_Model answer.pdf"
    question = "uploads/question_Question paper.pdf"
    
    try:
        result = evaluate_with_vision(student, model, question)
        # Clean the response text (sometimes it adds markdown fences)
        if "```json" in result:
            result = result.split("```json")[1].split("```")[0].strip()
        elif "```" in result:
            result = result.split("```")[1].split("```")[0].strip()
            
        print("\n--- HIGH SCORED RESULT ---")
        print(result)
        with open("high_vision_result.json", "w") as f:
            f.write(result)
            
        # Also run for low scored
        low_student = "uploads/student_Answersheet Low.pdf"
        result_low = evaluate_with_vision(low_student, model, question)
        if "```json" in result_low:
            result_low = result_low.split("```json")[1].split("```")[0].strip()
        elif "```" in result_low:
            result_low = result_low.split("```")[1].split("```")[0].strip()
            
        print("\n--- LOW SCORED RESULT ---")
        print(result_low)
        with open("low_vision_result.json", "w") as f:
            f.write(result_low)
            
    except Exception as e:
        print(f"Error: {e}")
