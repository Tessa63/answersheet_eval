import os
import sys
from text_utils import clean_text, correct_spelling
import ocr_service

# Mock Model Answer (since we don't want to run OCR on the model PDF again to save time, 
# and we know what it contains for this specific question)
# In reality, this comes from the uploaded file.
model_answer_content = """
Decision tree pruning is a technique to reduce the size of decision trees by removing sections of the tree that are non-critical and redundant to classify instances. Pruning reduces the complexity of the final classifier, and hence improves predictive accuracy by the reduction of overfitting.
Pruning methods can be divided into two types: Pre-pruning and Post-pruning.
Pre-pruning halts the construction of the tree early.
Post-pruning removes branches from a fully grown tree.
"""

def verify_full_pipeline(student_filename):
    print(f"Testing Pipeline on {student_filename}")
    path = os.path.join("uploads", student_filename)
    
    if not os.path.exists(path):
        print("File not found.")
        return

    # 1. Run Improved OCR
    print("Running Improved OCR (CLAHE)...")
    try:
        raw_text = ocr_service.extract_text_from_file(path)
    except Exception as e:
        print(f"OCR Error: {e}")
        return

    print(f"Raw OCR Output Length: {len(raw_text)}")
    print(f"Sample Raw: {raw_text[:200]}...")

    # 2. Build Model Vocabulary
    model_vocab = set(clean_text(model_answer_content).split())
    print(f"Model Vocabulary Size: {len(model_vocab)}")

    # 3. Clean and Correct Student Text
    print("Cleaning and Correcting...")
    cleaned = clean_text(raw_text)
    corrected = correct_spelling(cleaned, custom_dictionary=model_vocab, cutoff=0.6)

    print("\n" + "="*40)
    print("FINAL PROCESSED OUTPUT")
    print("="*40)
    print(corrected)
    print("="*40)

    # 4. Check for success
    if "decision" in corrected and "pruning" in corrected:
        print("[PASS] Recovered key domain terms!")
    else:
        print("[FAIL] Could not recover key terms.")

if __name__ == "__main__":
    verify_full_pipeline("student_answer.pdf")
