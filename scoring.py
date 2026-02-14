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
        
        # 4. Final Score
        if model_concepts:
            concept_score = len(matched_concepts) / len(model_concepts)
        else:
            concept_score = 0
            
        final_score = (0.4 * overall_sim) + (0.6 * concept_score)
        
        # Boost
        if concept_score > 0.8:
            final_score = max(final_score, concept_score)
            
        final_score = max(0.0, min(1.0, final_score))
        
        # Feedback
        feedback_lines = []
        if final_score > 0.8:
            feedback_lines.append("Excellent answer!")
        elif final_score > 0.5:
             feedback_lines.append("Good attempt.")
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
        
        # 1. First, align Model Answers to Schema if exists
        # If we have a schema, we ideally want to iterate through schema questions.
        # But our Model Answer file might match 1-to-1 with Schema questions.
        
        # We will iterate through MODEL keys as the source of truth for "Correct Answer Content".
        # But we will look up metadata from Schema.
        
        # Fallback if no schema: Assume 10 marks per question, no OR groups.
        if not question_schema:
            question_schema = {}
            
        # Group results by Schema Group ID to handle OR logic
        grouped_results = {} 
        
        for m_key in model_keys:
            if m_key in processed_model_keys:
                continue
                
            model_ans = model_segments[m_key]
            
            # Lookup Schema Info
            # Schema keys might be "1" while Model key is "1" or "Q1" or "1a".
            # Try exact match or loose match.
            base_num = re.sub(r'[a-z]', '', m_key) # "1a" -> "1"
            
            schema_info = question_schema.get(m_key) or question_schema.get(base_num) or {}
            max_marks = schema_info.get("max_marks", 10) # Default 10
            group_id = schema_info.get("group", m_key) # Default to self as group
            
            score_data = {
                "question": m_key,
                "score": 0,
                "max_marks": max_marks,
                "feedback": "",
                "details": {}
            }
            
            # Find Student Answer
            # 1. Exact match
            if m_key in student_segments:
                res = self.evaluate_single_answer(student_segments[m_key], model_ans)
                raw_score_normalized = res['score'] / 10.0 # 0.0 to 1.0 (res['score'] is out of 10 currently)
                
                score_data.update(res)
                # Scale to Actual Max Marks
                score_data['score'] = round(raw_score_normalized * max_marks, 1)
                
            # 2. Base match (e.g. Model '1a', Student '1')
            elif base_num in student_segments:
                res = self.evaluate_single_answer(student_segments[base_num], model_ans)
                raw_score_normalized = res['score'] / 10.0
                
                score_data.update(res)
                score_data['question'] = f"{m_key} (checked against Q{base_num})"
                score_data['score'] = round(raw_score_normalized * max_marks, 1)
                
            else:
                 score_data['score'] = 0
                 score_data['feedback'] = "Not Attempted"

            # Add to Group
            if group_id not in grouped_results:
                grouped_results[group_id] = []
            grouped_results[group_id].append(score_data)
            
            processed_model_keys.add(m_key)

        # Post-Processing: Handle OR Groups
        # For each group, we pick the highest score?
        # Actually, "OR" usually means "Select one of these questions". 
        # If student answered both, exams usually take the BEST one.
        
        final_results = []
        total_obtained = 0
        total_possible = 0
        
        for group_id, items in grouped_results.items():
            # If group has multiple items, it effectively means they are alternatives OR parts.
            # Wait, parts (1a, 1b) are usually SUMMED. Alternatives (Q1 OR Q2) are MAXED.
            # The schema should tell us.
            # Our current schema parser uses "OR" detection to assign same Group ID to alternatives.
            # So items with SAME Group ID are ALTERNATIVES.
            
            # Select the Best score in this group
            best_item = max(items, key=lambda x: x['score'])
            
            # Mark others as "Skipped / Alternative"
            for item in items:
                if item == best_item:
                    item['selected'] = True
                    total_obtained += item['score']
                    total_possible += item['max_marks']
                else:
                    item['selected'] = False
                    item['feedback'] += " (Alternative option not selected or lower score)"
                    # Do not add to total possible if it's an alternative we didn't count
            
            final_results.extend(items)
            
        # Sort by question ID for display
        def natural_keys(text):
            return [int(c) if c.isdigit() else c for c in re.split(r'(\d+)', text)]
            
        final_results.sort(key=lambda x: natural_keys(x['question']))

        return {
            "breakdown": final_results,
            "total_score": round(total_obtained, 1),
            "max_score": total_possible
        }
