import re
import math
from ocr_service import extract_text_from_file

class QuestionPaperParser:
    def __init__(self):
        # Pattern to detect "OR" lines between questions
        self.or_pattern = re.compile(r'(?:^|\n)\s*(?:OR|or|Or)\s*(?:$|\n)', re.MULTILINE)
        
        # Pattern to detect challenge/bonus questions
        self.challenge_pattern = re.compile(
            r'(?:challeng|bonus|extra\s+credit)',
            re.IGNORECASE
        )

    def parse_question_paper(self, file_path):
        """
        Parses the question paper file and returns a schema dict.
        Uses a per-line approach to find table rows with marks.
        
        Expected OCR line formats:
          "2. |Match the following  3 |cO1"
          "7.a) | 1. Prove that ...  8 |cO1"
          "11. |Let G be a directed graph... 5 |CO3"
          "9. a) |A city has implemented... 8 /|CO3"
        
        Key pattern: a line starts with a question number, and ends with
        <marks_number> followed by |CO or CO and a digit.
        """
        text = extract_text_from_file(file_path)
        if not text:
            print("[QuestionPaper] ERROR: OCR returned empty text from question paper.")
            return {}

        print(f"[QuestionPaper] OCR text preview (first 500 chars):\n{text[:500]}")
        
        # Try to detect total marks from the paper
        total_marks_detected = self._detect_total_marks(text)
        print(f"[QuestionPaper] Full OCR text length: {len(text)} chars")

        schema = {}
        q_marks = {}       # {question_key: marks}
        q_positions = []   # for OR group detection
        
        lines = text.split('\n')
        
        # ===== PER-LINE DETECTION =====
        # Pattern: line contains question number at start AND marks+CO at end
        # End-of-line marks pattern: <number> followed by optional |/| then CO<digit>
        line_pattern = re.compile(
            r'^\s*(\d{1,2})\s*'              # Question number (1-2 digits)
            r'[\.\)]*\s*'                     # Optional . or )
            r'([a-z]?\s*[\)\}\]]*)?'          # Optional sub-part like "a)", "b}", etc
            r'\s*[\|\[\(]*\s*'                # Optional pipe, bracket
            r'(.*?)'                          # Question text (non-greedy)
            r'\s*(\d{1,2})\s*'               # Marks (1-2 digit number before CO) - RELAXED whitespace
            r'[/\|\s]*'                       # Optional /| separators
            r'(?:[Cc]+[Oo]+\s*\d|[Pp]+[Oo]+\s*\d)' # CO1, CO2, or PO1
        )
        
        for line_idx, line in enumerate(lines):
            m = line_pattern.match(line.strip())
            if not m:
                continue
            
            q_num = int(m.group(1))
            sub_part = (m.group(2) or "").strip().rstrip(')]}')
            marks = int(m.group(4))
            q_text = m.group(3) or ""
            
            # Validate: reasonable question number and marks
            if q_num < 1 or q_num > 50:
                print(f"  [QP] Ignored invalid question number: {q_num}")
                continue
            if marks < 1 or marks > 100:
                continue
            
            # Build question key
            q_key = str(q_num)
            sub_clean = re.sub(r'[^a-z]', '', sub_part.lower())
            if sub_clean:
                q_key = str(q_num) + sub_clean
            
            # Deduplicate: keep first occurrence (OCR may repeat pages)
            if q_key in q_marks:
                continue
                
            q_marks[q_key] = marks
            q_positions.append({
                "q": q_key,
                "line": line_idx,
                "marks": marks,
                "text": q_text.strip()
            })
            
            print(f"  [QP] Detected: Q{q_key} = {marks} marks")
        
        print(f"[QuestionPaper] Per-line detection found: {q_marks}")
        
        # ===== FALLBACK: Classic marks patterns =====
        if not q_marks:
            print("[QuestionPaper] Per-line detection failed, trying classic patterns...")
            classic_pattern = re.compile(
                r'(?:^|\n)\s*(?:Q|Question)?\s*(\d+[a-z]?)\s*[\.:\)\]\-\_]?\s*'
                r'(.*?)'
                r'(?:'
                r'\[(\d+)\s*[Mm](?:arks)?\]'
                r'|'
                r'\((\d+)\s*[Mm](?:arks)?\)'
                r'|'
                r'[Mm]arks?\s*[\:\=]\s*(\d+)'
                r'|'
                r'(\d+)\s+[Mm]arks?'
                r')',
                re.IGNORECASE | re.DOTALL
            )
            
            for m in classic_pattern.finditer(text):
                q_num = m.group(1).strip().lower()
                marks = None
                for g in range(3, 7):
                    val = m.group(g)
                    if val:
                        marks = int(val)
                        break
                if q_num and marks and 1 <= marks <= 20:
                    pure = re.sub(r'[a-z]', '', q_num)
                    if pure.isdigit() and 1 <= int(pure) <= 20:
                        if q_num not in q_marks:
                            q_marks[q_num] = marks
                            q_positions.append({
                                "q": q_num, "line": 0,
                                "marks": marks, "text": ""
                            })
            
            print(f"[QuestionPaper] Classic detection found: {q_marks}")
        
        if not q_marks:
            print("[QuestionPaper] WARNING: No marks detected by any method.")
            if total_marks_detected:
                return {"_total_marks": total_marks_detected}
            return {}

        # ===== NO MERGING of SUB-PARTS =====
        # We process 7a, 7b separately so they appear in the schema.
        # Scoring logic will aggregate them later.
        q_marks_final = q_marks
        
        # ===== DETECT OR GROUPS =====
        # Find OR markers and figure out which questions they separate
        or_matches = list(self.or_pattern.finditer(text))
        print(f"[QuestionPaper] Found {len(or_matches)} 'OR' markers")
        
        groups = {q: q for q in q_marks_final}
        
        for or_match in or_matches:
            or_line = text[:or_match.start()].count('\n')
            
            # Find questions immediately before and after this OR
            sorted_qs = sorted(q_positions, key=lambda x: x['line'])
            
            prev_q = None
            next_q = None
            
            for qp in sorted_qs:
                base = re.sub(r'[a-z]', '', qp['q'])
                if qp['line'] < or_line:
                    prev_q = base
                elif qp['line'] > or_line and next_q is None:
                    next_q = base
            
            if prev_q and next_q and prev_q != next_q:
                shared_id = min(prev_q, next_q, key=lambda x: int(x))
                
                for q in list(groups.keys()):
                    # Check base number to include sub-parts in the group
                    # e.g. if prev_q="7", then "7a", "7b" should both get shared_id
                    base_q = re.sub(r'[a-z]', '', q)
                    if base_q == prev_q or base_q == next_q:
                        groups[q] = shared_id
                
                print(f"[QuestionPaper] OR group: Q{prev_q} (and parts) and Q{next_q} (and parts) -> group '{shared_id}'")

        # ===== DETECT CHALLENGE QUESTIONS =====
        challenge_questions = set()
        
        # Look for "Challenging Questions" or "Bonus" section header
        # Collect ALL candidate questions after challenge headers
        challenge_candidates = set()
        for cm in self.challenge_pattern.finditer(text):
            challenge_line = text[:cm.start()].count('\n')
            
            # Find ALL questions AFTER the challenge header
            for qp in sorted(q_positions, key=lambda x: x['line']):
                base = re.sub(r'[a-z]', '', qp['q'])
                if qp['line'] > challenge_line:
                    challenge_candidates.add(base)
        
        if challenge_candidates:
            # Challenge is ALWAYS the highest-numbered question in the paper
            # (not Q9 which is a regular OR question that appears after
            # a repeated "Challenging Questions" header in OCR)
            highest = max(challenge_candidates, key=lambda x: int(x))
            challenge_questions.add(highest)
            print(f"[QuestionPaper] Challenge candidates: {challenge_candidates}, selecting highest: Q{highest}")
        
        # Fallback: if challenge keyword found but no question detected after it,
        # mark the highest-numbered question
        if not challenge_questions and self.challenge_pattern.search(text):
            last_q = max(q_marks_final.keys(), key=lambda x: int(x))
            challenge_questions.add(last_q)
            print(f"[QuestionPaper] Fallback: marking Q{last_q} as challenge (highest numbered)")
        
        print(f"[QuestionPaper] Challenge questions: {challenge_questions}")

        # ===== BUILD FINAL SCHEMA =====
        for q, marks in q_marks_final.items():
            gid = groups.get(q, q)
            
            if q in challenge_questions:
                q_type = "challenge"
            else:
                siblings = [k for k, v in groups.items() if v == gid and k != q]
                q_type = "optional" if siblings else "mandatory"
            
            schema[q] = {
                "max_marks": marks,
                "type": q_type,
                "group": gid
            }
            
        if total_marks_detected:
            schema["_total_marks"] = total_marks_detected
            
        print(f"[QuestionPaper] Final schema: {schema}")
        return schema

    def _detect_total_marks(self, text):
        """
        Try to find total marks mentioned in the question paper.
        """
        patterns = [
            r'(?:total|max(?:imum)?|full)\s*(?:marks?)\s*[:\=\-]?\s*(\d+)',
            r'(\d+)\s*(?:total)\s*marks?',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for m in matches:
                val = int(m)
                if 20 <= val <= 100:
                    print(f"[QuestionPaper] Detected total marks: {val}")
                    return val
        return None

def parse_question_paper_file(file_path):
    parser = QuestionPaperParser()
    return parser.parse_question_paper(file_path)
