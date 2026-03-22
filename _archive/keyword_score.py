from difflib import SequenceMatcher

# Read corrected student answer
with open("corrected_answer.txt", "r", encoding="utf-8") as f:
    student_text = f.read().split()

# Read dynamic keywords (from model answer)
with open("dynamic_keywords.txt", "r", encoding="utf-8") as f:
    keywords = f.read().split()

def is_similar(word, keyword, threshold=0.7):
    return SequenceMatcher(None, word, keyword).ratio() >= threshold

matched = set()

for w in student_text:
    for k in keywords:
        if is_similar(w, k):
            matched.add(k)

# Avoid division by zero
if len(keywords) == 0:
    score = 0
else:
    score = len(matched) / len(keywords)

print("Matched keywords:", matched)
print("Keyword Score:", round(score, 2))
print("Marks:", round(score * 10, 2))

missing_keywords = set(keywords) - matched

with open("missing_keywords.txt", "w", encoding="utf-8") as f:
    f.write(" ".join(missing_keywords))
