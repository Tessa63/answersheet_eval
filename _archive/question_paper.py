import re
import math
from ocr_service import extract_text_from_file
from llm_parser import get_schema_from_llm

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
        
        print("[QuestionPaper] Attempting Intelligent LLM parsing for extreme accuracy...")
        try:
            llm_schema = get_schema_from_llm(text)
            if llm_schema:
                print(f"[QuestionPaper] LLM successfully extracted robust schema: {llm_schema}")
                return llm_schema
        except Exception as e:
            print(f"[QuestionPaper] LLM parsing encountered an error: {e}")
            
        print("[QuestionPaper] LLM schema generation unavailable or failed. Falling back to simple Regex...")
        
        # Try to detect total marks from the paper
        total_marks_detected = self._detect_total_marks(text)
        print(f"[QuestionPaper] Full OCR text length: {len(text)} chars")

        schema = {}
        q_marks = {}       # {question_key: marks}
        q_positions = []   # for OR group detection
        
        lines = text.split('\n')
        
        # ===== PER-LINE DETECTION =====
        # Pattern: line contains question number at start AND marks+CO at end.
        # STRICT: q_num must be 1-2 digits (1-15 range), marks must be ≤ 20.
        # This prevents matching header rows like "10784 ... 50 |CO1".
        line_pattern = re.compile(
            r'^\s*(\d{1,2})\s*'              # Question number (STRICT: 1-2 digits only)
            r'[\.)\]]*\s*'                    # Optional . or )
            r'([a-z]?\s*[\)\}\]]*)?'          # Optional sub-part like "a)", "b}", etc
            r'\s*[\|\[\(\/\\]*\s*'                # Optional pipe, bracket, slash
            r'(.*?)'                          # Question text (non-greedy)
            r'\s+(\d{1,2})\s*'               # Marks (1-2 digits) — must follow whitespace
            r'[I/l\|\s\\]*'                       # Optional /| separators (with I,l for bad OCR PIPES)
            r'(?:(?:[Cc]+[Oo]+\s*\d|[Pp]+[Oo]+\s*\d)\s*)?'  # CO/PO marker OPTIONAL
            r'$'                              # Must be end of line — prevents mid-text digit matches
        )
        
        for line_idx, line in enumerate(lines):
            # Ignore simple "Page X of Y" or "X of Y" lines
            if re.match(r'^\s*(?:[Pp]age\s*)?\d+\s*of\s*\d+\s*$', line.strip()):
                continue

            m = line_pattern.match(line.strip())
            if not m:
                continue
            
            q_num = int(m.group(1))
            sub_part = (m.group(2) or "").strip().rstrip(']}')
            marks = int(m.group(4))
            q_text = m.group(3) or ""
            
            # Validate: reasonable question number (1-15) and per-question marks (1-20)
            if q_num < 1 or q_num > 15:
                print(f"  [QP] Ignored out-of-range Q#: {q_num}")
                continue
            if marks < 1 or marks > 20:  # Per-question marks; total marks rows > 20
                print(f"  [QP] Ignored implausible marks for Q{q_num}: {marks}")
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
                r'(?:^|\n)\s*(?:Q|Question|Qn)?\s*\.?\s*(\d+[a-z]?)\s*[\.:\)\]\-\_]?\s*'
                r'(.*?)'
                r'(?:'
                r'\[(\d+)\s*[Mm](?:arks)?\]'
                r'|'
                r'\((\d+)\s*[Mm](?:arks)?\)'
                r'|'
                r'[Mm]arks?\s*[\:\=\-]\s*(\d+)'
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
                # Try to count questions from plain numbered list ("1.", "2.", etc.)
                q_count = self._detect_question_count(text)
                if q_count and q_count >= 2:
                    print(f"[QuestionPaper] Fallback: detected {q_count} questions from numbering, distributing {total_marks_detected} marks evenly")
                    return self._build_even_schema(q_count, total_marks_detected, text)
                return {"_total_marks": total_marks_detected}
            return {}

        # ===== SCHEMA SANITY CHECK =====
        # If the detected schema looks garbage (e.g., max Q# > 20, or only one question
        # was found but it has the full total marks), fall back to distributing evenly.
        max_q_num = max(int(re.sub(r'[a-z]', '', k)) for k in q_marks if re.sub(r'[a-z]', '', k).isdigit())
        if max_q_num > 20:
            print(f"[QuestionPaper] SCHEMA GARBAGE DETECTED (max Q# = {max_q_num} > 20). Discarding and rebuilding from total marks.")
            q_marks = {}
            if total_marks_detected:
                q_count = self._detect_question_count(text)
                if q_count and q_count >= 2:
                    return self._build_even_schema(q_count, total_marks_detected, text)
                return {"_total_marks": total_marks_detected}
            return {}

        # SANITY: If too few questions vs. total marks, schema is likely wrong
        # e.g. only Q1=2marks detected but total=50 and text has many paragraphs -> rebuild
        if total_marks_detected and len(q_marks) <= 2:
            marks_sum = sum(q_marks.values())
            # If detected marks sum is way less than total marks, we likely missed questions
            if marks_sum <= total_marks_detected * 0.2:  # detected < 20% of total
                q_count = self._detect_question_count(text)
                if q_count and q_count >= 4:
                    print(f"[QuestionPaper] Schema too sparse ({len(q_marks)} Qs, {marks_sum} marks) vs total {total_marks_detected}. Rebuilding from {q_count} detected questions.")
                    return self._build_even_schema(q_count, total_marks_detected, text)

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

        # ===== BUILD FALLBACK SCHEMA if nothing useful was detected =====
        # This handles cases where per-line and classic detection both produce garbage
        # but we at least know the total marks.
        if not q_marks and total_marks_detected and not schema:
            print(f"[QuestionPaper] Building fallback schema: 10 questions × {total_marks_detected//10} marks each")
            schema["_total_marks"] = total_marks_detected
            
        print(f"[QuestionPaper] Final schema: {schema}")
        return schema

    def _detect_question_count(self, text):
        """
        Count distinct question numbers by scanning for patterns like
        '1.', '2.', '1)', '2)', 'Q1', 'Q2' in the text.
        Returns the highest question number found (as a proxy for question count).
        """
        # Find all standalone numbers 1-15 that look like question numbers
        # Must be at start of line or after newline / pipe / bracket
        pattern = re.compile(
            r'(?:^|[\n\|])\s*(?:Q\.?\s*)?(\d{1,2})\s*[\.:\)\]|]',
            re.MULTILINE
        )
        nums = set()
        for m in pattern.finditer(text):
            n = int(m.group(1))
            if 1 <= n <= 15:
                nums.add(n)
        
        if not nums:
            return None
        
        count = max(nums)  # highest number found = question count
        print(f"[QuestionPaper] Detected {count} questions from numbering pattern")
        return count

    def _build_even_schema(self, q_count, total_marks, text):
        """
        Build a schema distributing total_marks evenly across q_count questions.
        Tries to guess Part A (short) vs Part B (long) structure if evident.
        Challenge questions (from 'Challenging Questions' section) are added separately.
        """
        schema = {}
        
        # ---- Detect challenge question ----
        challenge_q = None
        challenge_marks = None
        challenge_match = re.search(
            r'Challeng\w*\s+Questions?[^\n]*\n[^\n]*\n?\s*(?:No\.?\s*)?(\d+)[^\n]{0,60}\s+(\d{1,2})\s*(?:[|/]|CO|$)',
            text, re.IGNORECASE
        )
        if challenge_match:
            challenge_q = challenge_match.group(1)
            challenge_marks = int(challenge_match.group(2))
            print(f"[QuestionPaper] Challenge Q detected from section: Q{challenge_q} = {challenge_marks} marks")
        else:
            # Look for the challenge section and grab marks from nearby context
            sec = re.search(r'Challeng\w*\s+Questions?', text, re.IGNORECASE)
            if sec:
                after = text[sec.start():sec.start()+400]
                # Look for a standalone marks number (5 marks typical for challenge)
                m_marks = re.search(r'(?:^|\s)(\d{1,2})\s*(?:[|/]|CO|$)', after, re.MULTILINE)
                if m_marks:
                    challenge_marks = int(m_marks.group(1))
                    challenge_q = str(q_count + 1)  # one beyond last detected
                    print(f"[QuestionPaper] Challenge section found, assigning Q{challenge_q} = {challenge_marks} marks")
        
        # Heuristic: try to detect Part A / Part B split
        has_part_a = bool(re.search(r'PART\s+A', text, re.IGNORECASE))
        has_part_b = bool(re.search(r'PART\s+B', text, re.IGNORECASE))
        
        if has_part_a and has_part_b:
            # Common university pattern: Part A = short answers (2-3 marks each)
            # Count how many questions appear before PART B
            part_b_match = re.search(r'PART\s+B', text, re.IGNORECASE)
            part_b_pos = part_b_match.start() if part_b_match else len(text) // 2
            
            text_before_b = text[:part_b_pos]
            nums_before_b = set()
            pattern = re.compile(r'(?:^|[\n\|])\s*(?:Q\.?\s*)?(\d{1,2})\s*[\.:\)\]|]', re.MULTILINE)
            for m in pattern.finditer(text_before_b):
                n = int(m.group(1))
                if 1 <= n <= 15:
                    nums_before_b.add(n)
            
            part_a_count = len(nums_before_b) if nums_before_b else max(1, q_count // 2)
            part_b_count = q_count - part_a_count
            
            if part_b_count > 0:
                # Use 30/70 split: Part A ≈ 30% of marks, Part B ≈ 70%
                # This correctly gives 3 marks/q for Part A and 7 marks/q for Part B
                # when total=50, Part A=5q, Part B=5q
                part_a_marks_each = max(1, round(total_marks * 0.30 / max(part_a_count, 1)))
                part_b_marks_each = max(1, round(total_marks * 0.70 / max(part_b_count, 1)))
                
                for i in range(1, part_a_count + 1):
                    schema[str(i)] = {"max_marks": part_a_marks_each, "type": "mandatory", "group": str(i)}
                for i in range(part_a_count + 1, q_count + 1):
                    schema[str(i)] = {"max_marks": part_b_marks_each, "type": "mandatory", "group": str(i)}
                
                # Add challenge question if detected
                if challenge_q and challenge_marks:
                    schema[challenge_q] = {"max_marks": challenge_marks, "type": "challenge", "group": challenge_q}
                    print(f"[QuestionPaper] Added challenge Q{challenge_q} = {challenge_marks} marks to schema")
                
                print(f"[QuestionPaper] Schema: {part_a_count} Part-A × {part_a_marks_each}m + {part_b_count} Part-B × {part_b_marks_each}m")
                schema["_total_marks"] = total_marks
                return schema
        
        # Simple even distribution
        marks_each = max(1, round(total_marks / q_count))
        for i in range(1, q_count + 1):
            schema[str(i)] = {"max_marks": marks_each, "type": "mandatory", "group": str(i)}
        
        # Add challenge question if detected
        if challenge_q and challenge_marks:
            schema[challenge_q] = {"max_marks": challenge_marks, "type": "challenge", "group": challenge_q}
        
        schema["_total_marks"] = total_marks
        print(f"[QuestionPaper] Even schema: {q_count} questions × {marks_each} marks each")
        return schema

    def _detect_total_marks(self, text):
        """
        Try to find total marks mentioned in the question paper.
        """
        patterns = [
            r'(?:total|max(?:imum)?|full)\s*(?:marks?)\s*[:\=\-]?\s*(\d+)',
            r'(\d+)\s*(?:total)\s*marks?',
            r'(?:Max\.?\s*Marks?)\s*[:\=\-]?\s*(\d+)',
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
