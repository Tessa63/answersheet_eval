import re

# Read OCR output
with open("student_answer.txt", "r", encoding="utf-8") as f:
    text = f.read()

# Convert to lowercase
text = text.lower()

# Remove special characters
text = re.sub(r"[^a-z0-9\s]", "", text)

# Remove extra spaces
text = re.sub(r"\s+", " ", text).strip()

print("CLEANED TEXT:")
print(text)

# Save cleaned text
with open("cleaned_answer.txt", "w", encoding="utf-8") as f:
    f.write(text)
