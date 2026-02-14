import re
from ocr_service import extract_text_from_file

class QuestionPaperParser:
    def __init__(self):
        # Pattern to find Question Numbers and their Marks
        # Examples: "1. (5 Marks)", "Q1 [10]", "1. ... [5]"
        # We look for a line starting with a number/Q-number, containing content, and ending with marks
        self.marks_pattern = re.compile(
            r'(?:^|\n)\s*(?:Q|Question)?\s*(\d+[a-z]?)\.?\s*.*?(?:\[(\d+)\s*M(?:arks)?\]|\((\d+)\s*M(?:arks)?\)|Marks\s*:\s*(\d+))',
            re.IGNORECASE | re.DOTALL
        )
        
        # Simple pattern to detect "OR" lines which suggest alternatives
        # This is tricky without strict structure. 
        # We'll assume if we see a line with just "OR" between two identified questions, they are alternatives.
        self.or_pattern = re.compile(r'(?:^|\n)\s*OR\s*(?:$|\n)', re.IGNORECASE)

    def parse_question_paper(self, file_path):
        """
        Parses the question paper file and returns a schema dict.
        Schema:
        {
            "1": {"max_marks": 5, "type": "mandatory", "group": "1"},
            "2": {"max_marks": 10, "type": "optional", "group": "2_OR_3"},
            "3": {"max_marks": 10, "type": "optional", "group": "2_OR_3"}
        }
        """
        text = extract_text_from_file(file_path)
        if not text:
            return {}

        schema = {}
        
        # 1. Regex approach to find Questions and Marks
        # We iterate through the text to find matches
        # Note: This is a heuristic. Real parsing might need more robust layout analysis.
        
        # Let's split by "Q" or Numbers to process chunks, similar to exam parser
        # But here we specifically want the marks at the end of the line/block.
        
        matches = list(self.marks_pattern.finditer(text))
        
        # Map of Q_Num -> Marks
        q_marks = {}
        for m in matches:
            q_num = m.group(1)
            # Extracted marks could be in group 2, 3, or 4 depending on correct regex group
            marks = m.group(2) or m.group(3) or m.group(4)
            
            if q_num and marks:
                q_marks[q_num] = int(marks)

        if not q_marks:
            # Fallback: Try a simpler pattern if the complex one failed
            # Maybe marks are just numbers at the end of lines?
            pass

        # 2. Logic to detect OR (Alternatives)
        # We need relative positions. 
        # If "OR" appears between Q2 and Q3, they are likely a group.
        
        # Get start positions of all questions
        q_positions = []
        for m in matches:
            q_positions.append({
                "q": m.group(1),
                "start": m.start(),
                "end": m.end(),
                "marks": int(m.group(2) or m.group(3) or m.group(4))
            })
            
        # Find ORs
        or_matches = list(self.or_pattern.finditer(text))
        
        # Group assignment
        # Default: each Q is its own group
        groups = {}
        for q in q_marks:
            groups[q] = q 
            
        for or_match in or_matches:
            or_pos = or_match.start()
            
            # Find the question immediately before and immediately after this OR
            # Sort questions by position
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
                # Merge groups
                group_id = f"{groups[prev_q['q']]}_OR_{groups[next_q['q']]}"
                
                # Update all members of these groups to the new group_id
                # (Union-Find style logic would be better but this is simple enough for small N)
                old_g1 = groups[prev_q['q']]
                old_g2 = groups[next_q['q']]
                
                new_gid = f"{old_g1}_OR_{old_g2}" # Simplification
                
                # Actually, simpler: Just link them.
                # Let's use a shared identifier.
                shared_id = min(old_g1, old_g2) # canonical ID
                
                groups[prev_q['q']] = shared_id
                groups[next_q['q']] = shared_id

        # Build final schema
        for q, marks in q_marks.items():
            gid = groups.get(q, q)
            is_optional = False
            # Check if anyone else shares this group
            siblings = [k for k, v in groups.items() if v == gid and k != q]
            if siblings:
                is_optional = True
            
            schema[q] = {
                "max_marks": marks,
                "type": "optional" if is_optional else "mandatory",
                "group": gid
            }
            
        return schema

def parse_question_paper_file(file_path):
    parser = QuestionPaperParser()
    return parser.parse_question_paper(file_path)
