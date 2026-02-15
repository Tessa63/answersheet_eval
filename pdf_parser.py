import re

class ExamParser:
    def __init__(self):
        # Improved Regex patterns
        # Matches: "Q1", "Q.1", "1)", "1.", "Ans 1", "Question 1"
        # We use a comprehensive regex to catch the start of a question.
        # Improved Regex patterns
        # Matches: "Q1", "Q.1", "1)", "1.", "1 _", "Ans 1", "Question 1"
        # Added '_' and '\s' to the final char class to handle EasyOCR artifacts.
        self.question_start_pattern = re.compile(
            r'(?:^|\n)\s*(?:Q|Question|Ans|Answer)?\s*[\.\-]?\s*(\d+[a-z]?)\s*[\.\:\-\)\_\ ]',
            re.IGNORECASE
        )

    def parse_text_to_questions(self, text):
        """
        Splits text into a dict { '1': 'text...', '2': 'text...' }
        """
        if not text:
            return {}

        questions = {}
        
        # Split text by the pattern
        # The split will return: [preamble, number1, content1, number2, content2...]
        split_data = self.question_start_pattern.split(text)
        
        # split_data[0] is preamble before first question
        if len(split_data) < 2:
            # Maybe the whole text is one answer if no numbers found?
            # Or maybe it failed. Let's return it as "1" if reasonable size?
            # Safe fallback: return explicit error or try to find loose numbers.
            # Ideally we warn, but for now let's just return what we have as "0" or "raw"
            if text.strip():
                 questions["1"] = text.strip() # Assign as Q1 if no question numbers detected
            return questions

        # Iterate pairs
        # Structure: [preamble, num1, content1, num2, content2, ...]
        current_num = None
        
        # Skip index 0 (preamble)
        for i in range(1, len(split_data), 2):
            q_num_str = split_data[i].strip().lower() # e.g. "1", "2a"
            content = split_data[i+1].strip() if i+1 < len(split_data) else ""
            
            # Formatting standardization
            if content:
                questions[q_num_str] = content
                
        return questions

def parse_exam_file(text):
    parser = ExamParser()
    return parser.parse_text_to_questions(text)
