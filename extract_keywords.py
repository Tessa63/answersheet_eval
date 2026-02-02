from sklearn.feature_extraction.text import TfidfVectorizer

# ---------- READ MODEL ANSWER ----------
with open("cleaned_model_answer.txt", "r", encoding="utf-8") as f:
    model_text = f.read()

# ---------- EXTRACT KEYWORDS ----------
vectorizer = TfidfVectorizer(
    stop_words="english",
    ngram_range=(1, 2),
    max_features=15
)

X = vectorizer.fit_transform([model_text])
keywords = vectorizer.get_feature_names_out()

with open("dynamic_keywords.txt", "w", encoding="utf-8") as f:
    f.write(" ".join(keywords))

# ---------- FIND MISSING KEYWORDS ----------
with open("student_answer.txt", "r", encoding="utf-8") as f:
    student_text = f.read()

student_words = set(student_text.split())
missing = [k for k in keywords if k not in student_words]

with open("missing_keywords.txt", "w", encoding="utf-8") as f:
    f.write(" ".join(missing))

print("KEYWORDS:", keywords)
print("MISSING:", missing)
