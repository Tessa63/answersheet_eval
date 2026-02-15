"""
Pre-load EasyOCR and Sentence Transformer models to avoid first-request timeout.
Run this script ONCE before starting the Flask app.
"""

print("="*60)
print("PRE-LOADING MODELS - This will take 2-5 minutes...")
print("="*60)

# 1. Load EasyOCR
print("\n[1/2] Loading EasyOCR...")
import easyocr
reader = easyocr.Reader(['en'])
print("[OK] EasyOCR loaded successfully!")

# 2. Load Sentence Transformer
print("\n[2/2] Loading Sentence Transformer...")
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('all-MiniLM-L6-v2')
print("[OK] Sentence Transformer loaded successfully!")

print("\n" + "="*60)
print("ALL MODELS LOADED! You can now run: python app.py")
print("="*60)
