from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Read cleaned student answer
with open("corrected_answer.txt", "r", encoding="utf-8") as f:
    student_answer = f.read()


# Read model answer
with open("cleaned_model_answer.txt", "r", encoding="utf-8") as f:
    model_answer = f.read()

# Vectorize text
vectorizer = TfidfVectorizer()
vectors = vectorizer.fit_transform([student_answer, model_answer])

# Compute similarity
similarity_score = cosine_similarity(vectors[0], vectors[1])[0][0]

print("Similarity Score:", round(similarity_score, 2))
print("Marks:", round(similarity_score * 10, 2), "/10")
