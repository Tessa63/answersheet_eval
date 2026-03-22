import re

# Read model answer
with open("model_answer.txt", "r", encoding="utf-8") as f:
    text = f.read()

# Convert to lowercase
text = text.lower()

# Remove special characters
text = re.sub(r"[^a-z0-9\s]", "", text)



# Remove extra spaces
text = re.sub(r"\s+", " ", text).strip()

print("CLEANED MODEL ANSWER:")
print(text)

# Save cleaned model answer
with open("cleaned_model_answer.txt", "w", encoding="utf-8") as f:
    f.write(text)
