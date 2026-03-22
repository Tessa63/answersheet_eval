import fitz

def extract_text_fast(pdf_path):
    text = ""
    try:
        doc = fitz.open(pdf_path)
        for page in doc:
            text += page.get_text()
    except Exception as e:
        print("Error:", e)
    return text

if __name__ == "__main__":
    m_path = "uploads/model_WhatsApp Image 2026-03-13 at 9.39.41 AM.pdf"
    text = extract_text_fast(m_path)
    print("Extracted Length:", len(text))
    print(text[:1000])
