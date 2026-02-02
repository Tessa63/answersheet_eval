from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import json

# ---------- READ TEXT ----------
with open("student_answer.txt", "r", encoding="utf-8") as f:
    student_text = f.read()

with open("cleaned_model_answer.txt", "r", encoding="utf-8") as f:
    model_text = f.read()

# ---------- TF-IDF ----------
vectorizer = TfidfVectorizer(stop_words="english")
vectors = vectorizer.fit_transform([student_text, model_text])
tfidf_score = cosine_similarity(vectors[0], vectors[1])[0][0]

# ---------- KEYWORD SCORE ----------
with open("dynamic_keywords.txt", "r", encoding="utf-8") as f:
    keywords = f.read().split()

student_words = set(student_text.split())
matched = [k for k in keywords if k in student_words]

keyword_score = len(matched) / max(len(keywords), 1)

# ---------- FINAL SCORE ----------
final_score = (0.6 * tfidf_score) + (0.4 * keyword_score)
final_score = min(final_score, 1.0)

output = {
    "tfidf": round(tfidf_score, 2),
    "keyword": round(keyword_score, 2),
    "final": round(final_score, 2),
    "marks": round(final_score * 10, 2)
}

print(json.dumps(output))
