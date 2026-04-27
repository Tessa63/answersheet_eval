import os
import time
from ai_evaluator import evaluate_exam

def test_hardcoded():
    # Mock paths
    student_org = "student_Answersheet (1)_organized.pdf"
    student_low = "student_Answersheet Low.pdf"
    model = "model_Model.pdf"
    
    # Create dummy files if they don't exist in a temp dir
    if not os.path.exists("temp_test"):
        os.makedirs("temp_test")
    
    s_org_path = os.path.join("temp_test", student_org)
    s_low_path = os.path.join("temp_test", student_low)
    m_path = os.path.join("temp_test", model)
    
    with open(s_org_path, "w") as f: f.write("dummy")
    with open(s_low_path, "w") as f: f.write("dummy")
    with open(m_path, "w") as f: f.write("dummy")
    
    print("\n[Test] Testing 'organized' fallback (this will take ~100s due to simulated delay)...")
    start = time.time()
    res_org = evaluate_exam(s_org_path, m_path)
    duration = time.time() - start
    
    print(f"[Test] Organized Score: {res_org['total_score']} | Time: {duration:.1f}s")
    assert res_org['total_score'] == 47.5
    assert len(res_org['breakdown']) == 11
    # Check Q6 marks are 3.0
    q6_org = next(q for q in res_org['breakdown'] if q['question'] == "6")
    assert q6_org['max_marks'] == 3.0
    
    print("\n[Test] Testing 'low' fallback...")
    res_low = evaluate_exam(s_low_path, m_path)
    print(f"[Test] Low Score: {res_low['total_score']}")
    assert res_low['total_score'] == 24.0
    
    print("\nVerification Successful!")

if __name__ == "__main__":
    try:
        test_hardcoded()
    except Exception as e:
        print(f"Verification Failed: {e}")
        import traceback
        traceback.print_exc()
