import re

class ExamParser:
    def __init__(self):
        # Matches: "Q1", "Q.1", "1)", "1.", "1 _", "Ans 1", "Question 1"
        self.question_start_pattern = re.compile(
            r'(?:^|\n)\s*(?:Q|Question|Ans|Answer)?\s*[\.\-]?\s*(\d+[a-z]?)\s*[\.\:\-\)\_\ ]',
            re.IGNORECASE
        )

    def parse_text_to_questions(self, text):
        """
        Splits text into a dict { '1': 'text...', '2': 'text...' }
        Filters out bogus question numbers from OCR noise.
        """
        if not text:
            return {}

        questions = {}
        
        split_data = self.question_start_pattern.split(text)
        
        if len(split_data) < 2:
            if text.strip():
                 questions["1"] = text.strip()
            return questions

        # Iterate pairs: [preamble, num1, content1, num2, content2, ...]
        for i in range(1, len(split_data), 2):
            q_num_str = split_data[i].strip().lower()
            content = split_data[i+1].strip() if i+1 < len(split_data) else ""
            
            # --- FILTER OUT BOGUS QUESTION NUMBERS ---
            # 1. Extract pure number part
            pure_num = re.sub(r'[a-z]', '', q_num_str)
            
            # 2. Skip if not a valid number
            if not pure_num or not pure_num.isdigit():
                continue
            
            num = int(pure_num)
            
            # 3. Only accept reasonable question numbers (1-20 for exams)
            if num < 1 or num > 20:
                continue
            
            # 4. Skip very short content (likely OCR noise)
            if len(content) < 10:
                continue
                
            # 5. If this question already exists, append content (handles
            #    cases where OCR splits one answer across matches)
            if q_num_str in questions:
                questions[q_num_str] += " " + content
            else:
                questions[q_num_str] = content
                
        # If nothing parsed, return whole text as Q1
        if not questions and text.strip():
            questions["1"] = text.strip()
            
        return questions

def parse_exam_file(text):
    parser = ExamParser()
    return parser.parse_text_to_questions(text)
