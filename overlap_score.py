# Read cleaned texts
with open("cleaned_answer.txt", "r", encoding="utf-8") as f:
    student = f.read()

with open("cleaned_model_answer.txt", "r", encoding="utf-8") as f:
    model = f.read()

# Convert to word sets
student_words = set(student.split())
model_words = set(model.split())

# Compute overlap
common_words = student_words.intersection(model_words)

if len(model_words) == 0:
    score = 0
else:
    score = len(common_words) / len(model_words)

print("Common words:", common_words)
print("Overlap Score:", round(score, 2))
print("Marks:", round(score * 10, 2), "/10")
