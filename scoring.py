from sentence_transformers import SentenceTransformer, util
import numpy as np
import re

# Global MODEL cache
MODEL = None

def get_model():
    global MODEL
    if MODEL is None:
        print("Loading Semantic Model (all-MiniLM-L6-v2)...")
        MODEL = SentenceTransformer('all-MiniLM-L6-v2')
    return MODEL

class SemanticScorer:
    def __init__(self):
        self.model = get_model()
        # Lowered from 0.65 -- OCR garbling inherently reduces cosine similarity
        # even for correct answers. A score of 0.50 is a cleaner paraphrase signal.
        self.similarity_threshold = 0.50
        self.stop_words = set([
            "a", "an", "the", "and", "or", "but", "is", "are", "was", "were", 
            "in", "on", "at", "to", "for", "with", "by", "of", "it", "that", 
            "this", "these", "those", "he", "she", "they", "we", "i", "you",
            "process", "method", "system", "which", "from", "as", "be", "have",
            "has", "had", "do", "does", "did", "can", "could", "will", "would",
            "should", "may", "might", "must", "done", "used", "using", "uses"
        ])

    def extract_key_concepts(self, text, top_n=10):
        """
        Extracts key concepts (n-grams) from text using embedding similarity (KeyBERT style).
        """
        from sklearn.feature_extraction.text import CountVectorizer
        from sklearn.metrics.pairwise import cosine_similarity

        # 1. Extract candidate n-grams (1-gram to 3-gram)
        # We use a simple regex for tokens to avoid complex NLTK dependencies if possible
        n_gram_range = (1, 3)
        stop_words_list = list(self.stop_words)
        
        try:
            count = CountVectorizer(ngram_range=n_gram_range, stop_words=stop_words_list).fit([text])
            candidates = count.get_feature_names_out()
        except ValueError:
            # If text is empty or only stopwords
            return []

        if len(candidates) == 0:
            return []

        # 2. Embed document and candidates
        doc_embedding = self.model.encode([text], convert_to_tensor=True)
        candidate_embeddings = self.model.encode(candidates, convert_to_tensor=True)

        # 3. Calculate Similarity
        # We want concepts that are most similar to the overall document meaning
        # Move to CPU for sklearn
        doc_embedding_np = doc_embedding.cpu().numpy()
        candidate_embeddings_np = candidate_embeddings.cpu().numpy()
        
        distances = cosine_similarity(doc_embedding_np, candidate_embeddings_np)
        
        # 4. Select Top N
        keywords = []
        indices = distances.argsort()[0][-top_n:]
        for i in indices:
            keywords.append(candidates[i])
            
        # Reverse to get most relevant first
        return keywords[::-1]

    def extract_keywords_simple(self, text):
        """
        Simple extraction for fallback or specific checks.
        """
        clean = re.sub(r'[^\w\s]', '', text.lower())
        words = clean.split()
        return [w for w in words if len(w) > 3 and w not in self.stop_words]

    def fuzzy_keyword_overlap(self, concept_keywords, student_text):
        """
        Returns True if any concept keyword is fuzzy-matched in student text.
        Requires proportional edit distances (no 2-edit matches for 4-letter words).
        """
        student_words = self.extract_keywords_simple(student_text)
        
        # Heuristic: only allow fuzzy matching if the student's word is reasonably close in length
        # and doesn't diverge too quickly.
        for tgt in concept_keywords:
            if len(tgt) < 4:
                continue # Do not fuzzy match very short words (e.g. "bus", "car", "net")
                
            for cand in student_words:
                if abs(len(cand) - len(tgt)) > 2:
                    continue
                
                # First char match (optimization & sanity)
                if cand[0] != tgt[0]:
                    continue
                    
                # Simple diff check
                diffs = sum(1 for a, b in zip(cand, tgt) if a != b)
                diffs += abs(len(cand) - len(tgt))
                
                # Dynamic tolerance:
                # 4-5 chars: 1 edit max
                # 6+ chars: 2 edits max
                tolerance = 1 if len(tgt) <= 5 else 2
                
                if diffs <= tolerance:
                    return True
        return False

    def ocr_noise_ratio(self, text):
        """
        Estimate what fraction of the text looks like OCR garbage.
        High ratio (>0.35) means the text is very noisy and scoring should be lenient.
        """
        words = text.split()
        if not words:
            return 0.0
        # Garbage words: contain >= 2 digits mixed with letters, or are mostly non-alpha
        noise_words = 0
        for w in words:
            alpha_chars = sum(c.isalpha() for c in w)
            digit_chars = sum(c.isdigit() for c in w)
            if len(w) >= 2 and alpha_chars == 0:   # Purely non-alpha ("---", "...", "##")
                noise_words += 1
            elif digit_chars > 0 and alpha_chars > 0 and digit_chars >= alpha_chars:  # Like "42ab"
                noise_words += 1
        return noise_words / max(len(words), 1)

    def keyword_rescue_floor(self, model_keywords, student_text):
        """
        If ≥2 subject keywords from the model answer appear (even fuzzily) in the
        student text, guarantee a minimum score floor to prevent total zero-scoring
        due to OCR degradation.
        Returns the number of matched keywords.
        """
        # Filter: only keep meaty keywords (>5 chars, not a stop word)
        meaty_kw = [k for k in model_keywords if len(k) > 5 and k not in self.stop_words]
        if not meaty_kw:
            return 0
        
        matches = 0
        student_lower = student_text.lower()
        for kw in meaty_kw:
            kw_lower = kw.lower()
            if kw_lower in student_lower:
                matches += 1
            elif self.fuzzy_keyword_overlap([kw_lower], student_lower):
                matches += 1
                
        return matches

    def check_match(self, concept, student_text, best_sem_score, noisy_mode=False):
        """
        Hybrid check: Semantic Score + Keyword Overlap.
        In noisy_mode (high OCR noise), thresholds are relaxed.
        """
        # Thresholds: lower in noisy_mode since OCR degrades cosine similarity
        # Relaxed for more "human-like" understanding of meaning
        high_threshold  = 0.40 if noisy_mode else 0.55
        mid_threshold   = 0.30 if noisy_mode else 0.45
        low_threshold   = 0.20 if noisy_mode else 0.35

        # 1. High Semantic Confidence (Paraphrase)
        if best_sem_score > high_threshold:
            return True
        
        concept_keywords = self.extract_keywords_simple(concept)
        
        # 2. Moderate Semantic + Answer likely relevant
        if best_sem_score > mid_threshold: 
            student_keywords = self.extract_keywords_simple(student_text)
            if set(concept_keywords) & set(student_keywords):
                return True
                
        # 3. Loose Semantic + Fuzzy Keyword Support (Typos/Messy OCR)
        if best_sem_score > low_threshold:
             if self.fuzzy_keyword_overlap(concept_keywords, student_text):
                 return True

        # 4. Keyword Rescue (Literal match despite bad semantic)
        if concept.lower() in student_text.lower():
             return True
             
        # 5. Fuzzy keyword alone — important for OCR noise
        if self.fuzzy_keyword_overlap(concept_keywords, student_text):
             return True
             
        return False


    def evaluate_single_answer(self, student_text, model_text):
        """
        Evaluates answer using Granular Concept Matching.
        Handles OCR-noisy student text with adaptive thresholds.
        """
        if not student_text or not model_text:
            return {"score": 0, "feedback": "Empty answer"}

        student_text = student_text.replace('\n', ' ')
        model_text = model_text.replace('\n', ' ')

        # Detect OCR noise level in student answer
        noise_ratio = self.ocr_noise_ratio(student_text)
        noisy_mode = noise_ratio > 0.30
        if noisy_mode:
            print(f"    [Scoring] OCR noisy mode ON (noise_ratio={noise_ratio:.2f})")

        # 1. Extract Concepts from model answer
        model_concepts = self.extract_key_concepts(model_text, top_n=8)
        if not model_concepts:
            model_concepts = [model_text]

        # 2. Variable Windowing
        # For short answers (<= 30 words), use the full text (windowing is harmful on short noisy text)
        words = student_text.split()
        window_size = 6
        step_size = 3
        windows = []
        if len(words) <= window_size or len(words) <= 30:
            windows.append(student_text)
        else:
            for i in range(0, len(words) - window_size + 1, step_size):
                windows.append(" ".join(words[i:i+window_size]))
            if len(words) % step_size != 0:
                 windows.append(" ".join(words[-window_size:]))
        
        if not windows:
            windows = [student_text]
            
        window_embeddings = self.model.encode(windows, convert_to_tensor=True)
        
        matched_concepts = []
        missing_concepts = []
        
        for concept in model_concepts:
            concept_emb = self.model.encode(concept, convert_to_tensor=True)
            hits = util.semantic_search(concept_emb, window_embeddings, top_k=1)
            best_score = hits[0][0]['score'] if hits and hits[0] else 0.0
            
            if self.check_match(concept, student_text, best_score, noisy_mode=noisy_mode):
                matched_concepts.append(concept)
            else:
                missing_concepts.append(concept)

        # 3. Overall Similarity
        emb1 = self.model.encode(student_text, convert_to_tensor=True)
        emb2 = self.model.encode(model_text, convert_to_tensor=True)
        overall_sim = float(util.cos_sim(emb1, emb2)[0][0])
        
        # 4. Final Score — CONCEPT-DRIVEN (Pure Semantic Grading)
        # We rely on the AI's holistic understanding of the answer block.
        # If the whole block means the same thing, it's correct.
        
        # --- Base Semantic Score (85% weight) ---
        sim_multiplier = 1.15 if noisy_mode else 1.0
        effective_sim = overall_sim * sim_multiplier
        
        base_semantic_score = 0.0
        if effective_sim >= 0.55:
            base_semantic_score = 1.0       # Perfect conceptual understanding
        elif effective_sim >= 0.40:
            # Scale linearly from 0.70 to 1.0
            fraction = (effective_sim - 0.40) / 0.15
            base_semantic_score = 0.70 + (0.30 * fraction)
        elif effective_sim >= 0.20:
            # Scale linearly from 0.25 to 0.70
            fraction = (effective_sim - 0.20) / 0.20
            base_semantic_score = 0.25 + (0.45 * fraction)
        else:
            base_semantic_score = 0.0       # Unrelated garbage
            
        final_score = base_semantic_score * 0.85
        
        # --- Bonus Detail Score (15% weight) ---
        # If the student happened to nail the specific sub-concepts, they get a bonus.
        if model_concepts:
            concept_score = len(matched_concepts) / len(model_concepts)
        else:
            concept_score = 0
            
        final_score += (concept_score * 0.15)
        
        # 5. Keyword Rescue Floor: if ≥2 subject keywords found, guarantee ≥35%
        # But ONLY if the text actually has some length. Prevents zeros from bad OCR.
        words = student_text.split()
        model_simple_kws = self.extract_keywords_simple(model_text)
        kw_hits = self.keyword_rescue_floor(model_simple_kws, student_text)
        if kw_hits >= 2 and len(words) > 5:
            final_score = max(final_score, 0.35)
            print(f"    [Scoring] Keyword rescue: {kw_hits} keywords matched -> floor 35%")
        elif kw_hits >= 1 and len(words) > 5:
            final_score = max(final_score, 0.15)
            
        # Minimum floor: any non-trivial answer with *some* semantic relevance gets at least 20%
        if len(words) >= 8 and effective_sim > 0.25:
            final_score = max(final_score, 0.20)
            
        final_score = max(0.0, min(1.0, final_score))
        
        # Feedback (Human-like)
        feedback_lines = []
        if final_score >= 0.85:
            feedback_lines.append("Excellent understanding of the concept.")
        elif final_score >= 0.60:
             feedback_lines.append("Good conceptual grasp, but slightly brief or missing some details.")
        elif final_score >= 0.35:
             feedback_lines.append("Partial understanding shown.")
        else:
             feedback_lines.append("Incorrect or insufficient concept.")
             
        if final_score < 0.85 and missing_concepts:
             missed_txt = ", ".join([f"'{c}'" for c in missing_concepts[:2]])
             feedback_lines.append(f"Consider adding details like: {missed_txt}.")

        return {
            "score": round(final_score * 10, 1),
            "feedback": " ".join(feedback_lines),
            "details": {
                "similarity": round(overall_sim, 2),
                "concept_coverage": round(concept_score, 2),
                "matched_concepts": matched_concepts,
                "missing_concepts": missing_concepts
            }
        }


    def evaluate_exam(self, student_segments, model_segments, question_schema=None):
        """
        Evaluates full exam with 'OR' logic and variable Max Marks using schema.
        """
        results = []
        processed_model_keys = set()
        
        # Sort keys to process 1, 1a, 1b in order roughly
        model_keys = sorted(model_segments.keys())
        
        # Fallback if no schema
        if not question_schema:
            question_schema = {}
        
        # Extract total marks hint from schema (if detected from question paper)
        total_marks_hint = None
        if "_total_marks" in question_schema:
            total_marks_hint = question_schema["_total_marks"]
            if isinstance(total_marks_hint, dict):
                total_marks_hint = None
            print(f"[Scoring] Total marks hint from question paper: {total_marks_hint}")
        
        # ===== GARBAGE SCHEMA DETECTION =====
        # The question paper parser sometimes produces nonsense keys like Q10784.
        # Detect this by: any non-meta key with a pure-numeric base > 50,
        # OR only 1-2 non-meta keys exist but they hold all the total marks
        # (meaning the parser caught a header row, not actual questions).
        def _is_garbage_schema(schema, total_marks):
            real_keys = [k for k in schema if not k.startswith("_") and isinstance(schema[k], dict)]
            if not real_keys:
                return False
            for k in real_keys:
                base = re.sub(r'[a-z]', '', k)
                if base.isdigit() and int(base) > 50:
                    print(f"[Scoring] Garbage schema detected: Q{base} > 50. Ignoring schema.")
                    return True
            # Also garbage if: only 1-2 keys but total marks sum equals total_marks
            if total_marks and len(real_keys) <= 2:
                marks_sum = sum(schema[k].get("max_marks", 0) for k in real_keys if isinstance(schema[k], dict))
                if marks_sum >= total_marks:
                    print(f"[Scoring] Garbage schema: only {len(real_keys)} keys with marks={marks_sum} = total. Ignoring.")
                    return True
            return False

        if _is_garbage_schema(question_schema, total_marks_hint):
            # Reset schema to just the total marks hint so even distribution kicks in
            question_schema = {"_total_marks": total_marks_hint} if total_marks_hint else {}

        # Calculate default marks per question.
        # Use unique OR-groups as denominator so paired alternatives (7a+7b OR 8)
        # don't inflate the count and underestimate per-question marks.
        if total_marks_hint and len(model_keys) > 0:
            # Count distinct OR groups from the (already sanitised) schema
            real_schema_keys = [k for k in question_schema if not k.startswith("_") and isinstance(question_schema[k], dict)]
            if real_schema_keys:
                group_ids = set(question_schema[k].get("group", k) for k in real_schema_keys)
                num_distinct_groups = max(len(group_ids), 1)
            else:
                num_distinct_groups = len(model_keys)
            default_marks = round(total_marks_hint / num_distinct_groups)
            default_marks = max(1, default_marks)  # At least 1 mark
            print(f"[Scoring] Computed default marks per question: {default_marks} ({total_marks_hint}/{num_distinct_groups} groups)")
        else:
            default_marks = 5  # University exams commonly use 5-mark questions
            print(f"[Scoring] WARNING: No total marks hint — defaulting to {default_marks} marks per question. Upload a question paper for accurate marks.")
        
        print(f"\n[Scoring] Using question schema (after sanity check): {question_schema}")
        print(f"[Scoring] Model answer keys: {model_keys}")
        print(f"[Scoring] Student answer keys: {list(student_segments.keys())}")
        print(f"[Scoring] Default marks per question: {default_marks}")
            
        # Group results by Schema Group ID to handle OR logic
        grouped_results = {} 
        
        # Track which student keys have already been consumed (by exact, base, or semantic match)
        # This MUST persist across all model key iterations to prevent reuse
        globally_matched_students = set()
        
        # Pre-compute schema info and score_data for all model keys
        model_key_info = {}
        for m_key in model_keys:
            base_num = re.sub(r'[a-z]', '', m_key)  # "1a" -> "1"
            schema_info = question_schema.get(m_key) or question_schema.get(base_num) or {}
            if isinstance(schema_info, (int, float)):
                schema_info = {}
            max_marks = schema_info.get("max_marks", default_marks)
            group_id = schema_info.get("group", m_key)
            q_type = schema_info.get("type", "mandatory")
            
            model_key_info[m_key] = {
                "base_num": base_num,
                "max_marks": max_marks,
                "group_id": group_id,
                "q_type": q_type,
            }
        
        # ------------------------------------------------------------------
        # PASS 1: Exact and base-number matches only (safe, reliable)
        # These should always be assigned first before semantic fallback
        # ------------------------------------------------------------------
        score_data_map = {}  # m_key -> score_data
        pass1_matched = set()  # model keys that found a match in Pass 1
        
        for m_key in model_keys:
            info = model_key_info[m_key]
            model_ans = model_segments[m_key]
            
            score_data = {
                "question": m_key,
                "_base_key": m_key,   # FIX: preserve clean key before any annotation added
                "score": 0,
                "max_marks": info["max_marks"],
                "feedback": "",
                "details": {},
                "type": info["q_type"]
            }
            
            # 1. Exact match
            if m_key in student_segments and m_key not in globally_matched_students:
                res = self.evaluate_single_answer(student_segments[m_key], model_ans)
                raw_score_normalized = res['score'] / 10.0
                
                score_data.update(res)
                score_data['score'] = round(raw_score_normalized * info["max_marks"], 1)
                globally_matched_students.add(m_key)
                pass1_matched.add(m_key)
                print(f"    [Pass1] Q{m_key} exact-matched to student Q{m_key}")
                
            # 2. Base match (e.g. Model '1a', Student '1')
            elif info["base_num"] in student_segments and info["base_num"] not in globally_matched_students:
                res = self.evaluate_single_answer(student_segments[info["base_num"]], model_ans)
                raw_score_normalized = res['score'] / 10.0
                
                score_data.update(res)
                score_data['question'] = f"{m_key} (checked against Q{info['base_num']})"
                score_data['score'] = round(raw_score_normalized * info["max_marks"], 1)
                globally_matched_students.add(info["base_num"])
                pass1_matched.add(m_key)
                print(f"    [Pass1] Q{m_key} base-matched to student Q{info['base_num']}")
            
            score_data_map[m_key] = score_data
        
        print(f"    [Pass1] Matched {len(pass1_matched)}/{len(model_keys)} model keys via exact/base")
        print(f"    [Pass1] Consumed student keys: {globally_matched_students}")
        
        # ------------------------------------------------------------------
        # PASS 2: Semantic fallback for remaining unmatched model keys
        # Only uses student answers NOT consumed in Pass 1
        # ------------------------------------------------------------------
        unmatched_model_keys = [mk for mk in model_keys if mk not in pass1_matched]
        
        if unmatched_model_keys and student_segments:
            unmatched_student_keys = [sk for sk in student_segments if sk not in globally_matched_students]
            print(f"    [Pass2] Unmatched model keys: {unmatched_model_keys}")
            print(f"    [Pass2] Available student keys: {unmatched_student_keys}")
            
            for m_key in unmatched_model_keys:
                model_ans = model_segments[m_key]
                info = model_key_info[m_key]
                score_data = score_data_map[m_key]
                
                # Recompute available student keys (some may have been consumed in this pass)
                available_keys = [sk for sk in student_segments if sk not in globally_matched_students]

                # NEW: Check for student sub-parts (e.g. Model '1' vs Student '1a', '1b')
                # If found, aggregate them and score as one block.
                # Only if the Model key is a pure number (no sub-part itself)
                is_pure_num = m_key.isdigit()
                student_sub_keys = []
                if is_pure_num:
                    for sk in available_keys:
                        # Check if starts with '1' and followed by letter (e.g. '1a')
                        if sk.startswith(m_key) and len(sk) > len(m_key) and sk[len(m_key)].isalpha():
                            student_sub_keys.append(sk)
                
                if student_sub_keys:
                    student_sub_keys.sort()
                    combined_text = " ".join([student_segments[k] for k in student_sub_keys])
                    
                    res = self.evaluate_single_answer(combined_text, model_ans)
                    raw_score_normalized = res['score'] / 10.0
                    
                    score_data.update(res)
                    score_data['question'] = f"{m_key}"
                    score_data['score'] = round(raw_score_normalized * info["max_marks"], 1)
                    score_data['feedback'] += f" (aggregated from student Q{', Q'.join(student_sub_keys)})"
                    
                    globally_matched_students.update(student_sub_keys)
                    print(f"    [Pass2] Q{m_key} aggregated match to student Q{student_sub_keys}")
                    
                elif available_keys:
                    best_match_key = None
                    best_match_score = -1
                    
                    model_emb = self.model.encode(model_ans[:500], convert_to_tensor=True)
                    
                    for sk in available_keys:
                        s_text = student_segments[sk]
                        if len(s_text.strip()) < 10:
                            continue
                        s_emb = self.model.encode(s_text[:500], convert_to_tensor=True)
                        sim = float(util.cos_sim(model_emb, s_emb)[0][0])
                        
                        if sim > best_match_score:
                            best_match_score = sim
                            best_match_key = sk
                    
                    # Only use if similarity is reasonable (> 0.2)
                    if best_match_key and best_match_score > 0.2:
                        res = self.evaluate_single_answer(student_segments[best_match_key], model_ans)
                        raw_score_normalized = res['score'] / 10.0
                        
                        score_data.update(res)
                        score_data['question'] = f"{m_key}"
                        score_data['score'] = round(raw_score_normalized * info["max_marks"], 1)
                        score_data['feedback'] += f" (matched to Q{best_match_key})"
                        
                        globally_matched_students.add(best_match_key)
                        print(f"    [Pass2] Q{m_key} semantic-matched to student Q{best_match_key} (sim={best_match_score:.2f})")
                    else:
                        score_data['score'] = 0
                        score_data['feedback'] = "Not Attempted"
                        print(f"    [Pass2] Q{m_key} -> Not Attempted (no good semantic match)")
                else:
                    score_data['score'] = 0
                    score_data['feedback'] = "Not Attempted"
                    print(f"    [Pass2] Q{m_key} -> Not Attempted (no available student keys)")
                
                score_data_map[m_key] = score_data
        elif unmatched_model_keys:
            for m_key in unmatched_model_keys:
                score_data_map[m_key]['score'] = 0
                score_data_map[m_key]['feedback'] = "Not Attempted"
                print(f"    [Pass2] Q{m_key} -> Not Attempted (no student segments at all)")

        # Add all results to groups
        for m_key in model_keys:
            info = model_key_info[m_key]
            group_id = info["group_id"]
            if group_id not in grouped_results:
                grouped_results[group_id] = []
            grouped_results[group_id].append(score_data_map[m_key])
            processed_model_keys.add(m_key)

        # Post-Processing: Handle OR Groups and Challenge Questions
        final_results = []
        total_obtained = 0
        total_possible = 0
        
        for group_id, items in grouped_results.items():
            # Group items by their base question number
            # e.g. Group "7" contains [7a, 7b, 8].
            # by_base["7"] = [7a, 7b]
            # by_base["8"] = [8]
            by_base = {}
            for item in items:
                # FIX: use _base_key (the original, unannotated key) for grouping.
                # item['question'] may be annotated e.g. "1 (checked against Q1)" which
                # caused re.sub to produce "1 ( 1)" instead of "1", breaking score totals.
                raw_key = item.get('_base_key', item['question'])
                base = re.sub(r'[a-z]', '', raw_key)
                if base not in by_base:
                    by_base[base] = []
                by_base[base].append(item)
            
            # Calculate total score for each base option
            base_scores = {}
            for base, sub_items in by_base.items():
                total_s = sum(i['score'] for i in sub_items)
                base_scores[base] = total_s
            
            # Identify the WINNING base question
            # If there's only one base (e.g. Q1), it wins by default
            if not base_scores:
                 best_base = None
            else:
                 # Break ties by max possible marks? Or just first?
                 best_base = max(base_scores, key=base_scores.get)
            
            # Mark items as selected/not selected
            for base, sub_items in by_base.items():
                is_selected = (base == best_base)
                
                for item in sub_items:
                    item['selected'] = is_selected
                    
                    if is_selected:
                        # Add to total ONLY if selected
                        # Challenge questions are scored but NOT counted in total
                        if item.get('type') != 'challenge':
                            total_obtained += item['score']
                            total_possible += item['max_marks']
                    else:
                        item['feedback'] += " (OR alternative -- not counted)"
            
            final_results.extend(items)
            
        # Sort by question ID for display
        def natural_keys(text):
            return [int(c) if c.isdigit() else c for c in re.split(r'(\d+)', text)]
            
        final_results.sort(key=lambda x: natural_keys(x['question']))
        
        # Post-hoc: if we know the actual total marks from the question paper,
        # scale to match (handles cases where per-question marks were estimated)
        final_max = total_possible
        final_obtained = total_obtained
        
        if total_marks_hint and total_possible > 0 and total_possible != total_marks_hint:
            scale_factor = total_marks_hint / total_possible
            final_obtained = round(total_obtained * scale_factor, 1)
            final_max = total_marks_hint
            print(f"[Scoring] Scaling to match detected total: {total_obtained}/{total_possible} -> {final_obtained}/{final_max}")
            
            # Also scale individual scores for display consistency
            for r in final_results:
                r['score'] = round(r['score'] * scale_factor, 1)
                r['max_marks'] = round(r['max_marks'] * scale_factor)
        
        print(f"\n[Scoring] Final: {round(final_obtained, 1)} / {final_max}")
        for r in final_results:
            sel = '[Y]' if r.get('selected') else '[N]'
            print(f"  {sel} Q{r['question']}: {r['score']}/{r['max_marks']} ({r.get('type', 'mandatory')})")

        return {
            "breakdown": final_results,
            "total_score": round(final_obtained, 1),
            "max_score": final_max
        }

