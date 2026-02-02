from difflib import get_close_matches

# Simple dictionary of expected academic words
dictionary = [
    "decision", "tree", "pruning", "prepruning", "postpruning",
    "overfitting", "outliers", "simplify", "reduce",
    "training", "data", "model", "classification",
    "early", "stopping", "nodes", "branches"
]

def correct_word(word):
    matches = get_close_matches(word, dictionary, n=1, cutoff=0.75)
    return matches[0] if matches else word

# Read cleaned student answer
with open("cleaned_answer.txt", "r", encoding="utf-8") as f:
    words = f.read().split()

# Correct words
corrected_words = [correct_word(w) for w in words]
corrected_text = " ".join(corrected_words)

print("CORRECTED STUDENT ANSWER:")
print(corrected_text)

# Save corrected text
with open("corrected_answer.txt", "w", encoding="utf-8") as f:
    f.write(corrected_text)
