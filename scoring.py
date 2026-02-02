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

    def evaluate_exam(self, student_segments, model_segments):
        """
        Evaluates full exam with 'OR' logic.
        """
        results = []
        
        processed_model_keys = set()
        
        # Sort keys to process 1, 1a, 1b in order roughly
        model_keys = sorted(model_segments.keys())
        
        for m_key in model_keys:
            if m_key in processed_model_keys:
                continue
                
            model_ans = model_segments[m_key]
            
            # Logic for "OR" handling:
            # Check if this key looks like an alternative (e.g., '5a', '5b')
            # If so, we group them.
            # Simplified heuristic: Group by numeric prefix.
            # "1a", "1b" -> group "1"
            
            base_num = re.sub(r'[a-z]', '', m_key) # "1a" -> "1"
            
            # Find all model keys sharing this base number
            alternatives = [k for k in model_segments.keys() if re.sub(r'[a-z]', '', k) == base_num]
            
            # If we have alternatives (more than 1 key with same number)
            # We assume MAX score approach if student answered only one.
            # But wait, usually exams are: "Q1 is mandatory. Q2 OR Q3."
            # Our parser output keys like '1', '2', '3'.
            # If Model has '1' and '2' and '3', and Student has '1','2','3', it's direct.
            
            # If Model has '5a' and '5b' (meaning 5a OR 5b), and Student has '5'.
            # We check Student['5'] against Model['5a'] and Model['5b'].
            
            best_result = None
            best_score = -1
            
            # Check for direct match first
            if m_key in student_segments:
                # 1-to-1 match
                res = self.evaluate_single_answer(student_segments[m_key], model_ans)
                res['question'] = m_key
                results.append(res)
                processed_model_keys.add(m_key)
                continue
            
            # Check if Student used the Base Key (e.g. Student wrote "5")
            if base_num in student_segments:
                # Compare Student '5' with this Model Key '5a'
                res = self.evaluate_single_answer(student_segments[base_num], model_ans)
                res['question'] = f"{m_key} (checked against Q{base_num})"
                
                # Check if we already have a result for this Base Num in the results list?
                # This is getting complicated.
                # Let's simplify: Return ALL comparisons, UI can filter or we just list them.
                # Actually, "take largest mark" was the requirement.
                
                # We will append this result. If there are multiple comparisons for Q5,
                # we might end up with "Q5a: 8/10", "Q5b: 2/10".
                # The user (teacher) can see which one matched.
                results.append(res)
                processed_model_keys.add(m_key)
            else:
                 # Not Attempted
                 results.append({
                     "question": m_key,
                     "score": 0,
                     "feedback": "Not Attempted",
                     "details": {}
                 })
                 processed_model_keys.add(m_key)

        # Calculate Totals
        # If we have multiple entries for the same base question (due to OR), 
        # we should probably only count the max one towards the total, 
        # BUT for transparency we list all.
        # For the total score calculation, let's group by Base Number.
        
        scores_by_base = {}
        for r in results:
            q_label = r['question'].split(' ')[0] # Get '5a' or '5'
            base = re.sub(r'[a-z]', '', q_label)
            
            s = r['score']
            if base not in scores_by_base:
                scores_by_base[base] = 0
            scores_by_base[base] = max(scores_by_base[base], s)
            
        total_obtained = sum(scores_by_base.values())
        max_possible = len(scores_by_base) * 10
        
        return {
            "breakdown": results,
            "total_score": round(total_obtained, 1),
            "max_score": max_possible
        }
