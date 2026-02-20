import re

# Page break marker inserted by ocr_service.py
PAGE_BREAK = "---PAGE_BREAK---"

# Common page header patterns from Indian university answer sheets
# Tolerant of OCR errors
PAGE_HEADER_PATTERNS = [
    r'[Mm]uthoo?t\s+[Ii]n?s[it]i?t?u?t?e?\b',
    r'\b(?:Main|Additional)\s+(?:Sh[ea][ea]t|Answer)',
    r'\bAddit[io][ao]n[ae]l\s+Sh[ea][ea]t',
    r'Space\s+for\s+Writing',
    r'MARKS\s+T[oO]\s+BE\s+FILLED',
    r'(?:Main|Additional)\s*Sh[a-z]*t\b',
    r'[Ii](?:nst|ule)\s+\d+\s+(?:of\s+)?Technology\s*\&?\s*(?:Main|Additional)',
]
PAGE_HEADER_RE = re.compile(
    '|'.join(PAGE_HEADER_PATTERNS),
    re.IGNORECASE
)


class ExamParser:
    def __init__(self):
        self.question_start_pattern = re.compile(
            r'(?:^|\n)\s*(?:Q|Question|Ans|Answer)?\.?\s*[\.\-]?\s*(\d+[a-z]?)\s*[\.\:\-\)\_\ ]',
            re.IGNORECASE
        )

    def parse_text_to_questions(self, text, expected_keys=None):
        """Split text into { '1': 'text...', '2': 'text...', '9a': '...', '9b': '...' }"""
        if not text:
            return {}

        clean_text = text.replace(PAGE_BREAK, "\n")
        questions = {}
        
        # 1. Primary Split by Numbered Questions (1, 2, 3...)
        # This regex handles "1.", "Q1", "1)", "1a", "9a)" etc.
        split_data = self.question_start_pattern.split(clean_text)
        
        if len(split_data) < 2:
            if clean_text.strip():
                 questions["1"] = clean_text.strip()
            return questions

        current_parent_num = None
        
        # We iterate over the split pieces. 
        # split_data[0] is text before first match (usually header/empty)
        # split_data[1] is first match group (question number)
        # split_data[2] is text following first match
        # split_data[3] is second match group...
        
        for i in range(1, len(split_data), 2):
            q_key_raw = split_data[i].strip().lower() # e.g. "9", "9a", "10"
            content = split_data[i+1].strip() if i+1 < len(split_data) else ""
            
            # Identify if this is a main number or already has a suffix
            pure_num = re.sub(r'[a-z]', '', q_key_raw)
            if not pure_num or not pure_num.isdigit():
                continue
                
            num_val = int(pure_num)
            if num_val < 1 or num_val > 50: # Sanity check
                continue
                
            # If it's just a number like "9", set it as current parent
            if pure_num == q_key_raw:
                current_parent_num = pure_num
                # If we have expected keys, verify if this number is expected
                # (Optional: we generally trust explicit numbers in text, but sub-parts check is stricter)
            
            # Store the main question content
            # If "9a" was found directly by the main regex, key is "9a"
            normalized_key = str(num_val) + re.sub(r'\d', '', q_key_raw)
            
            # --- SUB-PART DETECTION WITHIN CONTENT ---
            # Often "a)" and "b)" are inside the content block of "9", not split by the main regex
            # We need to extract them and create "9a", "9b" keys
            
            # Use schema to validate sub-parts if available
            parent_key = current_parent_num if current_parent_num else str(num_val)
            sub_parts = self._extract_sub_parts(content, parent_key, expected_keys)
            
            if sub_parts:
                # If we found sub-parts, add them to questions
                # The 'main' content might be the intro or the first part if unlabeled
                if sub_parts.get("main_intro"):
                     if normalized_key in questions:
                         questions[normalized_key] += " " + sub_parts["main_intro"]
                     else:
                         questions[normalized_key] = sub_parts["main_intro"]
                
                for sub_key, sub_text in sub_parts.items():
                    if sub_key == "main_intro": continue
                    
                    full_key = sub_key # e.g. "9a"
                    if full_key in questions:
                        questions[full_key] += " " + sub_text
                    else:
                        questions[full_key] = sub_text
            else:
                # No sub-parts found, just add the content to the main key
                if normalized_key in questions:
                    questions[normalized_key] += " " + content
                else:
                    questions[normalized_key] = content
                
        if not questions and clean_text.strip():
            questions["1"] = clean_text.strip()
            
        return questions

    def _extract_sub_parts(self, text, parent_num, expected_keys=None):
        """
        Scans a text block for lines starting with a), b), c) or i), ii).
        Returns dict: { '9a': 'text...', '9b': 'text...', 'main_intro': '...' }
        
        Strictness:
        - If expected_keys is provided, ONLY return keys that are in expected_keys.
          e.g. if '2a' is NOT in expected_keys, ignore 'a)' inside Q2 text.
        """
        # Regex for sub-parts: newline followed by a) or b) or i)
        # We are strict: must be at start of line
        # Fixed regex to use single capturing group `([a-h]|[ivx]+)` to avoid None results
        sub_pattern = re.compile(
            r'(?:^|\n)\s*([a-h]|[ivx]+)\s*[\)\.\-]\s*', 
            re.IGNORECASE
        )
        
        parts = sub_pattern.split(text)
        if len(parts) < 2:
            return None
            
        # parts[0] = intro text
        # parts[1] = first marker (e.g. 'a')
        # parts[2] = text for first part
        # parts[3] = second marker (e.g. 'b')
        # ...
        
        results = {}
        if parts[0].strip():
            results["main_intro"] = parts[0].strip()
            
        for i in range(1, len(parts), 2):
            marker = parts[i]
            # Safety check for None (though regex fix should prevent it)
            if not marker:
                continue
                
            marker = marker.lower()
            content = parts[i+1].strip() if i+1 < len(parts) else ""
            
            # Skip if content is too short to be a real answer
            if len(content) < 3:
                continue
                
            # If marker is roman numeral, map to a,b,c? Or keep as is?
            # User specifically asked for 9a, 9b. Roman numerals often map to a,b in checking.
            # Let's map i->a, ii->b for consistency if widely used, but user said 'a,b'.
            # If marker is 'a', 'b', use it.
            if marker in ['a','b','c','d','e','f','g','h']:
                key = f"{parent_num}{marker}"
                
                # SCHEMA VALIDATION
                if expected_keys:
                    # If this key is NOT in expected_keys, treat it as text content for the parent/previous part
                    # instead of a new question
                    if key not in expected_keys:
                        # Append to previous context (main_intro or previous key)
                        # We just return None here to signal "don't split this block"
                        # But wait, we are iterating. If ANY part is invalid, maybe we should invalidate the whole split?
                        # Or just append this part to the previous valid part?
                        # For simplicity: if '2a' is invalid, we invalidate the split assumption for this marker.
                        
                        # BUT, we've already split the string. 
                        # Easier to just not add it to results keys, but append correct text.
                        # Actually if we ignore 'a)', we should treat 'a) content' as part of the previous block.
                        # This is complex to reconstruct.
                        
                        # Alternative: check if ANY of the potential keys (e.g. 2a, 2b) are in expected_keys.
                        # If NONE are, then return None (no sub-parts).
                        pass
                
                results[key] = content
            # (Optional: handle roman numerals if needed later)
            
        # Post-validation: Check against expected_keys
        if expected_keys:
            valid_sub_keys = [k for k in results.keys() if k != "main_intro" and k in expected_keys]
            if not valid_sub_keys:
                # No valid sub-questions found. Return None so the caller treats the whole text as one block.
                return None
            
            # Filter out invalid keys?
            # If 9a is valid but 9c is not in schema...
            # Usually strictness means: only return what is in schema.
            filtered_results = {}
            if "main_intro" in results:
                filtered_results["main_intro"] = results["main_intro"]
                
            for k in results:
                if k == "main_intro": continue
                if k in expected_keys:
                    filtered_results[k] = results[k]
                else:
                     # Invalid key content should probably be appended to previous valid key?
                     # For now, let's just drop the KEY, but we might lose content.
                     # Better: append to main_intro or previous valid key.
                     # Simplest: if we have mixed validity, it's safer to keep all or drop all based on majority?
                     # No, strict schema means strict.
                     pass
            
            # Better approach: if schema says Q2 has NO parts, valid_sub_keys will be empty -> returns None.
            return filtered_results if valid_sub_keys else None

        return results if len(results) > 0 else None

    def _split_into_pages(self, text):
        """Split OCR text into logical pages."""
        if PAGE_BREAK in text:
            pages = text.split(PAGE_BREAK)
            pages = [p.strip() for p in pages if p.strip() and len(p.strip()) > 20]
            if len(pages) > 1:
                return pages
        
        # Split by page header patterns
        header_positions = []
        for m in PAGE_HEADER_RE.finditer(text):
            line_start = text.rfind('\n', 0, m.start())
            line_start = 0 if line_start == -1 else line_start + 1
            header_positions.append(line_start)
        
        if not header_positions:
            return [text]
        
        deduped = [header_positions[0]]
        for pos in header_positions[1:]:
            if pos - deduped[-1] > 100:
                deduped.append(pos)
        
        if len(deduped) <= 1:
            return [text]
        
        pages = []
        for i, start in enumerate(deduped):
            end = deduped[i + 1] if i + 1 < len(deduped) else len(text)
            page_text = text[start:end].strip()
            if page_text and len(page_text) > 20:
                pages.append(page_text)
        
        return pages if len(pages) > 1 else [text]

    def _strip_page_headers(self, text):
        """Remove page header lines from text."""
        lines = text.split('\n')
        clean_lines = []
        skip_count = 0
        for line in lines:
            if skip_count > 0:
                skip_count -= 1
                continue
            if PAGE_HEADER_RE.search(line):
                skip_count = 2
                continue
            if re.match(r'^\s*(Sub\s+Total|Maximum\s+Marks|Marks\s+Secured|CO\s*\d|Onos)\s*$', line, re.IGNORECASE):
                continue
            clean_lines.append(line)
        return '\n'.join(clean_lines)
    
    def _split_text_into_chunks(self, text, num_chunks):
        """
        Smart splitting of text into roughly num_chunks pieces.
        Uses page headers first, then paragraph breaks, then even splitting.
        """
        # First try page headers
        pages = self._split_into_pages(text)
        if len(pages) >= num_chunks:
            return pages[:num_chunks + 2]  # Return a few extra if available
        
        # Then try splitting by large paragraph breaks (3+ newlines)
        paragraphs = re.split(r'\n\s*\n\s*\n', text)
        paragraphs = [p.strip() for p in paragraphs if p.strip() and len(p.strip()) > 15]
        
        if len(paragraphs) >= num_chunks:
            # Group paragraphs into roughly equal chunks
            per_chunk = max(1, len(paragraphs) // num_chunks)
            chunks = []
            for i in range(0, len(paragraphs), per_chunk):
                chunk = '\n\n'.join(paragraphs[i:i + per_chunk])
                if chunk.strip():
                    chunks.append(chunk.strip())
            return chunks
        
        # Last resort: split by double newlines
        paragraphs = re.split(r'\n\s*\n', text)
        paragraphs = [p.strip() for p in paragraphs if p.strip() and len(p.strip()) > 15]
        
        if len(paragraphs) >= num_chunks:
            per_chunk = max(1, len(paragraphs) // num_chunks)
            chunks = []
            for i in range(0, len(paragraphs), per_chunk):
                chunk = '\n\n'.join(paragraphs[i:i + per_chunk])
                if chunk.strip():
                    chunks.append(chunk.strip())
            return chunks
        
        # Can't split further
        return [text.strip()] if text.strip() else []

    def parse_with_page_awareness(self, text, expected_keys=None):
        """
        Enhanced parsing using page boundaries when standard parsing fails.
        """
        questions = self.parse_text_to_questions(text, expected_keys=expected_keys)
        
        if not expected_keys:
            return questions
        
        expected_count = len([k for k in expected_keys if not k.startswith("_")])
        found_count = len(questions)
        
        if found_count >= expected_count * 0.6:
            return questions
        
        print(f"    [Parser] Standard parsing found {found_count}/{expected_count} expected questions")
        print(f"    [Parser] Trying page-aware parsing as fallback...")
        
        # Find where the last parsed question's content ends in the text
        clean_text = text.replace(PAGE_BREAK, "\n")
        last_consumed_pos = 0
        
        for k, v in questions.items():
            snippet = v[:30].strip()
            if len(snippet) >= 10:
                pos = clean_text.find(snippet)
                if pos >= 0:
                    end_pos = pos + len(v)
                    if end_pos > last_consumed_pos:
                        last_consumed_pos = end_pos
        
        # Find missing expected keys
        found_keys = set(questions.keys())
        found_base_keys = set()
        for k in found_keys:
            found_base_keys.add(k)
            found_base_keys.add(re.sub(r'[a-z]', '', k))
        
        missing_keys = []
        for k in expected_keys:
            if k.startswith("_"):
                continue
            base_k = re.sub(r'[a-z]', '', k)
            if k not in found_base_keys and base_k not in found_base_keys:
                missing_keys.append(k)
        
        missing_keys = sorted(
            missing_keys,
            key=lambda x: [int(c) if c.isdigit() else c for c in re.split(r'(\d+)', x)]
        )
        
        if not missing_keys:
            return questions
        
        # Take trailing text
        if last_consumed_pos > 0 and last_consumed_pos < len(text) - 50:
            # Normal case: we found some questions, take the rest
            trailing_text = text[last_consumed_pos:]
        elif last_consumed_pos >= len(text) * 0.9:
            # Case: Q1 (or others) consumed almost EVERYTHING (greedy default).
            # We should assume missing keys might be ANYWHERE in the text.
            # So we use the FULL text for fallback splitting.
            trailing_text = text
            print("    [Parser] text consumed > 90%, using FULL text for fallback splitting")
        else:
            # Fallback: we didn't consume much, but didn't find clear end?
            # Safe bet: take last 60%? Or maybe just take everything?
            # Let's take LAST 70% to be safer against header issues
            trailing_text = text[int(len(text) * 0.3):]
        
        print(f"    [Parser] Text consumed: {last_consumed_pos}/{len(text)} chars, "
              f"trailing: {len(trailing_text)} chars")
        print(f"    [Parser] Missing keys: {missing_keys}")
        
        if len(trailing_text.strip()) < 30:
            return questions
        
        # Clean trailing text
        trailing_clean = self._strip_page_headers(trailing_text)
        
        # Split trailing text into chunks — one per missing key
        chunks = self._split_text_into_chunks(trailing_clean, len(missing_keys))
        
        print(f"    [Parser] Split trailing text into {len(chunks)} chunks")
        
        result = dict(questions)
        
        # Assign chunks to missing keys
        for i, missing_key in enumerate(missing_keys):
            if i < len(chunks):
                result[missing_key] = chunks[i]
                preview = chunks[i][:60].replace('\n', ' ')
                print(f"    [Parser] Chunk {i+1} -> Q{missing_key} ({len(chunks[i])} chars): {preview}...")
            else:
                break
        
        # If there are extra chunks, append them to the last assigned key
        last_assigned = missing_keys[min(len(chunks), len(missing_keys)) - 1] if missing_keys else None
        if last_assigned and len(chunks) > len(missing_keys):
            for extra_chunk in chunks[len(missing_keys):]:
                result[last_assigned] += " " + extra_chunk
            print(f"    [Parser] {len(chunks) - len(missing_keys)} extra chunks appended to Q{last_assigned}")
        
        final_count = len(result)
        if final_count > found_count:
            print(f"    [Parser] Improved: {found_count} -> {final_count} questions")
        
        return result


def parse_exam_file(text, expected_keys=None):
    parser = ExamParser()
    if expected_keys:
        return parser.parse_with_page_awareness(text, expected_keys)
    return parser.parse_text_to_questions(text)
