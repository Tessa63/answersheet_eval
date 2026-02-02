import os
import sys

# Add current directory to path
sys.path.append(r"c:\Users\hp\answersheet_eval")

# Mocking Flask request/files is hard, let's just test the logic pipeline directly.
from ocr_service import extract_text_from_file
from pdf_parser import parse_exam_file
from scoring import SemanticScorer

def test_pipeline():
    print("--- Starting End-to-End Pipeline Test ---")
    
    # 1. OCR
    # We use existing answer.pdf (Student) and a "dummy" model answer if none exists
    student_path = r"c:\Users\hp\answersheet_eval\uploads\answer.pdf"
    
    # Check if we have a model answer file. If not, I'll create a text string.
    # User said teacher gives PDF usually. Let's assume we have text or use the parser on a string.
    
    print("1. Extracting Student Text...")
    if os.path.exists(student_path):
        student_text = extract_text_from_file(student_path)
    else:
        print("Student file not found, skipping OCR test.")
        student_text = "Q1. Decision trees are flowcharts. Q2. Pruning reduces overfitting."

    # Creating a Mock Model Text that mimics what OCR would give from a clean PDF
    model_text = """
    Q1. A decision tree is a flowchart-like tree structure where an internal node represents feature(or attribute), the branch represents a decision rule, and each leaf node represents the outcome. 
    Q2. Pruning is a technique in machine learning and search algorithms that reduces the size of decision trees by removing sections of the tree that provide little power to classify instances.
    Q5a. Supervised learning uses labeled data.
    Q5b. Unsupervised learning uses unlabeled data.
    """
    
    print("\n2. Parsing...")
    print("Parsing Student Text (preview):", student_text[:100].replace('\n', ' '))
    student_segments = parse_exam_file(student_text)
    print("Student Segments Found:", student_segments.keys())
    
    model_segments = parse_exam_file(model_text)
    print("Model Segments Found:", model_segments.keys())
    
    print("\n3. Scoring...")
    scorer = SemanticScorer()
    results = scorer.evaluate_exam(student_segments, model_segments)
    
    print("\n--- Results ---")
    print(f"Total Score: {results['total_score']} / {results['max_score']}")
    for res in results['breakdown']:
        print(f"[{res['question']}] Score: {res['score']} - {res['feedback']}")
        if 'details' in res:
             print(f"   Details: {res['details']}")

if __name__ == "__main__":
    test_pipeline()
