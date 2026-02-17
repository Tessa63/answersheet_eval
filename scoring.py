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
        self.similarity_threshold = 0.65 # Increased to 0.65 to reduce false positives
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
        """
        student_words = self.extract_keywords_simple(student_text)
        
        for tgt in concept_keywords:
            for cand in student_words:
                # Length check
                if abs(len(cand) - len(tgt)) > 2:
                    continue
                # First char match (optimization)
                if cand[0] != tgt[0]:
                    continue
                    
                # Simple diff check
                diffs = sum(1 for a, b in zip(cand, tgt) if a != b)
                diffs += abs(len(cand) - len(tgt))
                
                if diffs <= 2: # Tolerance of 2 edits
                    return True
        return False

    def check_match(self, concept, student_text, best_sem_score):
        """
        Hybrid check: Semantic Score + Keyword Overlap.
        """
        # 1. High Semantic Confidence (Paraphrase)
        # Reduced from 0.75 to 0.70 based on "Green flora" -> 0.72
        if best_sem_score > 0.70:
            return True
        
        concept_keywords = self.extract_keywords_simple(concept)
        
        # 2. Moderate Semantic + Exact Keyword Support
        if best_sem_score > 0.55: # Loosened slightly
            student_keywords = self.extract_keywords_simple(student_text)
            if set(concept_keywords) & set(student_keywords):
                return True
                
        # 3. Loose Semantic + Fuzzy Keyword Support (Typos/Messy OCR)
        if best_sem_score > 0.45:
             if self.fuzzy_keyword_overlap(concept_keywords, student_text):
                 return True

        # 4. Keyword Rescue (Literal match despite bad semantic)
        # Check literal string
        if concept.lower() in student_text.lower():
             return True
             
        # Check fuzzy keywords alone? optional
        # Maybe dangerous if semantic score is trash (0.1).
        # But if word is "chlorophyll" and student wrote "clorophyl", we should give it.
        if self.fuzzy_keyword_overlap(concept_keywords, student_text):
             return True
             
        return False


    def evaluate_single_answer(self, student_text, model_text):
        """
        Evaluates answer using Granular Concept Matching.
        """
        if not student_text or not model_text:
            return {"score": 0, "feedback": "Empty answer"}

        student_text = student_text.replace('\n', ' ')
        model_text = model_text.replace('\n', ' ')

        # 1. Extract Concepts
        model_concepts = self.extract_key_concepts(model_text, top_n=8)
        if not model_concepts:
            model_concepts = [model_text]

        # 2. Variable Windowing (Size 6)
        # Optimized for catching 3-5 word phrases without too much dilution
        words = student_text.split()
        window_size = 6 
        step_size = 3
        windows = []
        if len(words) <= window_size:
            windows.append(student_text)
        else:
            for i in range(0, len(words) - window_size + 1, step_size):
                windows.append(" ".join(words[i:i+window_size]))
            # Add the tail if needed
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
            
            if self.check_match(concept, student_text, best_score):
                matched_concepts.append(concept)
            else:
                missing_concepts.append(concept)

        # 3. Overall Similarity
        emb1 = self.model.encode(student_text, convert_to_tensor=True)
        emb2 = self.model.encode(model_text, convert_to_tensor=True)
        overall_sim = float(util.cos_sim(emb1, emb2)[0][0])
        
        # 4. Final Score — CONCEPT-DRIVEN
        # Philosophy: if the student covers the key concepts from the model answer,
        # they deserve the marks. Semantic similarity is a secondary signal.
        if model_concepts:
            concept_score = len(matched_concepts) / len(model_concepts)
        else:
            concept_score = 0
        
        # Concept coverage is the PRIMARY signal (like a teacher checking key points)
        # Similarity is a SECONDARY boost for answers that paraphrase well
        
        # Base score from concept coverage (0-85%)
        final_score = concept_score * 0.85
        
        # Similarity boost (up to 15% additional)
        # Rewards well-articulated answers that semantically match
        if overall_sim > 0.3:
            sim_boost = min(overall_sim, 1.0) * 0.15
            final_score += sim_boost
        
        # Floor from overall similarity alone — catches paraphrased answers
        # where concepts extracted poorly but the overall meaning is correct
        if overall_sim > 0.6:
            # Very similar answers should score well even if concept extraction missed
            final_score = max(final_score, overall_sim * 0.95)
        elif overall_sim > 0.45:
            final_score = max(final_score, overall_sim * 0.85)
        elif overall_sim > 0.3:
            final_score = max(final_score, overall_sim * 0.7)
        
        # Length bonus: reward students who wrote substantial answers
        student_len = len(student_text.split())
        model_len = max(len(model_text.split()), 1)
        length_ratio = min(student_len / model_len, 1.5)
        if length_ratio > 0.4 and concept_score > 0.3:
            length_bonus = 0.1 * min(length_ratio, 1.0)
            final_score += length_bonus
        
        # Minimum floor: any non-trivial answer gets at least 20%
        if student_len >= 5:
            final_score = max(final_score, 0.20)
            
        final_score = max(0.0, min(1.0, final_score))
        
        # Feedback
        feedback_lines = []
        if final_score > 0.75:
            feedback_lines.append("Excellent answer!")
        elif final_score > 0.50:
             feedback_lines.append("Good attempt.")
        elif final_score > 0.25:
             feedback_lines.append("Partial answer.")
        else:
             feedback_lines.append("Needs more detail.")
             
        if missing_concepts:
             missed_txt = ", ".join([f"'{c}'" for c in missing_concepts[:2]])
             feedback_lines.append(f"Consider mentioning: {missed_txt}.")

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
        
        # Calculate default marks per question
        num_model_questions = len(model_keys)
        if total_marks_hint and num_model_questions > 0:
            # Distribute total marks evenly if we know the total but not individual marks
            default_marks = round(total_marks_hint / num_model_questions)
            default_marks = max(1, default_marks)  # At least 1 mark
            print(f"[Scoring] Computed default marks per question: {default_marks} ({total_marks_hint}/{num_model_questions})")
        else:
            default_marks = 5  # University exams commonly use 5-mark questions
        
        print(f"\n[Scoring] Using question schema: {question_schema}")
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
                
                if available_keys:
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
            has_multiple = len(items) > 1
            
            if has_multiple:
                # OR group: select the best scoring alternative
                best_item = max(items, key=lambda x: x['score'])
                
                for item in items:
                    if item == best_item:
                        item['selected'] = True
                        # Challenge questions are scored but NOT counted in total
                        if item.get('type') != 'challenge':
                            total_obtained += item['score']
                            total_possible += item['max_marks']
                    else:
                        item['selected'] = False
                        item['feedback'] += " (OR alternative -- not counted)"
            else:
                # Single question (mandatory or challenge)
                item = items[0]
                item['selected'] = True
                
                if item.get('type') == 'challenge':
                    # Challenge questions: show score but don't add to total
                    item['feedback'] = f"Challenge question (not counted in total). {item.get('feedback', '')}".strip()
                else:
                    total_obtained += item['score']
                    total_possible += item['max_marks']
            
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

