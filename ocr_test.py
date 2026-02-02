import pytesseract
from PIL import Image

# Tell Python where Tesseract is installed
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Load an image
img = Image.open("answer.jpeg")

# Extract text
text = pytesseract.image_to_string(img)

print(text)

with open("student_answer.txt", "w", encoding="utf-8") as f:
    f.write(text)
