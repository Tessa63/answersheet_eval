from app import app, progress, latest_result
import time

def test_full_flow():
    app.config['TESTING'] = True
    client = app.test_client()

    print("Uploading files via /evaluate...")
    with open('uploads/student_answer.pdf', 'rb') as s, \
         open('uploads/model_Model answer.pdf', 'rb') as m, \
         open('uploads/question_Question paper.pdf', 'rb') as q:
        
        data = {
            'student_file': (s, 'student_answer.pdf'),
            'model_file': (m, 'Model answer.pdf'),
            'question_file': (q, 'Question paper.pdf')
        }
        response = client.post('/evaluate', data=data, content_type='multipart/form-data')
        print(f"POST /evaluate response: {response.get_json()} (Code: {response.status_code})")

    print("Polling /progress...")
    while progress['status'] not in ['done', 'error']:
        print(f"Progress: {progress['step']}/6 - {progress['message']}")
        time.sleep(2)
    
    print(f"\nFinal Progress Status: {progress['status']}")
    print(f"Message: {progress['message']}")

    if progress['status'] == 'done':
        print("\nFetching /results HTML...")
        response = client.get('/results')
        print(f"GET /results response length: {len(response.data)} bytes (Code: {response.status_code})")
        print("Test Succeeded!")
    else:
        print("\nTest Failed!")

if __name__ == '__main__':
    test_full_flow()
