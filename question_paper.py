import re
from ocr_service import extract_text_from_file

class QuestionPaperParser:
    def __init__(self):
        # Broad pattern to find Question Numbers and their Marks
        # Matches formats like:
        #   "1. ... [3 Marks]", "Q1 (5M)", "1. ... Marks: 3"
        #   "1. ... 3 marks", "1. ... [3]", "1. ... (3)"
        #   "1a) ... [8 Marks]", "7 a) ... 8 Marks"
        self.marks_pattern = re.compile(
            r'(?:^|\n)\s*(?:Q|Question)?\s*(\d+[a-z]?)\s*[\.\:\)\]\-\_]?\s*'  # Question number
            r'(.*?)'  # Question text (non-greedy)
            r'(?:'
            r'\[(\d+)\s*[Mm](?:arks)?\]'       # [3 Marks] or [3M]
            r'|'
            r'\((\d+)\s*[Mm](?:arks)?\)'        # (3 Marks) or (3M)
            r'|'
            r'[Mm]arks?\s*[\:\=]\s*(\d+)'       # Marks: 3 or Mark=3
            r'|'
            r'[\[\(]\s*(\d+)\s*[\]\)]'           # [3] or (3)
            r'|'
            r'(\d+)\s+[Mm]arks?'                 # 3 marks or 3 Marks
            r')',
            re.IGNORECASE | re.DOTALL
        )
        
        # Pattern to detect "OR" lines between questions
        self.or_pattern = re.compile(r'(?:^|\n)\s*(?:OR|or|Or)\s*(?:$|\n)', re.MULTILINE)
        
        # Pattern to detect challenge/bonus questions
        self.challenge_pattern = re.compile(
            r'(?:challenge|bonus|extra|optional|additional)\s*(?:question)?',
            re.IGNORECASE
        )

    def _extract_marks(self, match):
        """Extract marks value from whichever group matched."""
        for g in range(3, 8):  # Groups 3-7 contain marks from different patterns
            val = match.group(g)
            if val:
                return int(val)
        return None

    def parse_question_paper(self, file_path):
        """
        Parses the question paper file and returns a schema dict.
        Schema:
        {
            "1": {"max_marks": 3, "type": "mandatory", "group": "1"},
            "7": {"max_marks": 16, "type": "optional", "group": "7"},
            "8": {"max_marks": 16, "type": "optional", "group": "7"},
            "11": {"max_marks": 5, "type": "challenge", "group": "11"}
        }
        """
        text = extract_text_from_file(file_path)
        if not text:
            print("[QuestionPaper] ERROR: OCR returned empty text from question paper.")
            return {}

        print(f"[QuestionPaper] OCR text preview (first 500 chars):\n{text[:500]}")
        print(f"[QuestionPaper] Full OCR text length: {len(text)} chars")

        schema = {}
        
        # 1. Find all question-marks matches
        matches = list(self.marks_pattern.finditer(text))
        
        q_marks = {}
        q_positions = []
        
        for m in matches:
            q_num = m.group(1).strip().lower()
            marks = self._extract_marks(m)
            q_text = m.group(2) or ""
            
            if q_num and marks:
                q_marks[q_num] = marks
                q_positions.append({
                    "q": q_num,
                    "start": m.start(),
                    "end": m.end(),
                    "marks": marks,
                    "text": q_text.strip()
                })

        print(f"[QuestionPaper] Detected marks from regex: {q_marks}")
        
        if not q_marks:
            print("[QuestionPaper] WARNING: No marks detected by regex. Schema will be empty.")
            print("[QuestionPaper] This means all questions will use default marks.")
            return {}

        # 2. Detect OR groups
        or_matches = list(self.or_pattern.finditer(text))
        print(f"[QuestionPaper] Found {len(or_matches)} 'OR' markers in text")
        
        # Default: each Q is its own group
        groups = {}
        for q in q_marks:
            base = re.sub(r'[a-z]', '', q)  # "7a" -> "7"
            groups[q] = base
            
        for or_match in or_matches:
            or_pos = or_match.start()
            
            sorted_qs = sorted(q_positions, key=lambda x: x['start'])
            
            prev_q = None
            next_q = None
            
            for i, q_data in enumerate(sorted_qs):
                if q_data['end'] < or_pos:
                    prev_q = q_data
                if q_data['start'] > or_pos:
                    next_q = q_data
                    break 
            
            if prev_q and next_q:
                # Get base numbers for grouping
                prev_base = re.sub(r'[a-z]', '', prev_q['q'])
                next_base = re.sub(r'[a-z]', '', next_q['q'])
                
                # Use the lower number as canonical group ID
                shared_id = min(prev_base, next_base, key=lambda x: int(x))
                
                # Update all questions with these base numbers to use shared group
                for q in list(groups.keys()):
                    q_base = re.sub(r'[a-z]', '', q)
                    if q_base == prev_base or q_base == next_base:
                        groups[q] = shared_id
                
                print(f"[QuestionPaper] OR group: Q{prev_q['q']} and Q{next_q['q']} -> group '{shared_id}'")

        # 3. Detect challenge questions
        challenge_questions = set()
        for qp in q_positions:
            if self.challenge_pattern.search(qp['text']):
                challenge_questions.add(qp['q'])
                base = re.sub(r'[a-z]', '', qp['q'])
                challenge_questions.add(base)
        
        # Also check context around the last question
        # Often Q11 is a challenge question mentioned elsewhere in the text
        if self.challenge_pattern.search(text):
            # Find which question number appears near the challenge keyword
            for cm in self.challenge_pattern.finditer(text):
                # Look for a question number near this match
                nearby = text[max(0, cm.start()-100):cm.end()+100]
                q_near = re.findall(r'(?:Q|Question)?\s*(\d+)', nearby)
                for qn in q_near:
                    if qn in q_marks:
                        challenge_questions.add(qn)
        
        print(f"[QuestionPaper] Challenge questions detected: {challenge_questions}")

        # 4. Build final schema
        for q, marks in q_marks.items():
            gid = groups.get(q, q)
            base = re.sub(r'[a-z]', '', q)
            
            # Determine type
            if q in challenge_questions or base in challenge_questions:
                q_type = "challenge"
            else:
                # Check if anyone else shares this group (OR alternative)
                siblings = [k for k, v in groups.items() if v == gid and k != q]
                q_type = "optional" if siblings else "mandatory"
            
            schema[q] = {
                "max_marks": marks,
                "type": q_type,
                "group": gid
            }
            
        print(f"[QuestionPaper] Final schema: {schema}")
        return schema

def parse_question_paper_file(file_path):
    parser = QuestionPaperParser()
    return parser.parse_question_paper(file_path)
