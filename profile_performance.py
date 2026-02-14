import time
import os
import cv2
import numpy as np
from ocr_service import extract_text_from_file, remove_red_ink, preprocess_image, get_reader
from scoring import SemanticScorer
from pdf2image import convert_from_path

def profile_pipeline():
    # Use a dummy large image or a pdf if available
    # We'll generate a large dummy image to simulate 300 DPI A4
    # A4 at 300 DPI is approx 2480 x 3508
    print("Generating dummy image (2480x3508)...")
    img = np.random.randint(0, 255, (3508, 2480, 3), dtype=np.uint8)
    
    # 1. Profile Red Ink Removal
    start = time.time()
    remove_red_ink(img)
    print(f"Red Ink Removal: {time.time() - start:.4f}s")
    
    # 2. Profile Preprocessing
    # Preprocessing converts to gray then bilateral filter
    start = time.time()
    preprocess_image(img)
    print(f"Preprocessing (CLAHE+Bilateral): {time.time() - start:.4f}s")
    
    # 3. Profile OCR (just init and run on small crop to avoid waiting forever if too slow)
    # We'll use a smaller crop for OCR profiling
    crop = img[0:500, 0:500]
    
    start = time.time()
    reader = get_reader() # Init time
    print(f"OCR Model Load: {time.time() - start:.4f}s")
    
    start = time.time()
    reader.readtext(crop, detail=0)
    print(f"OCR Inference (500x500 crop): {time.time() - start:.4f}s")
    
    # 4. Profile Scoring
    scorer = SemanticScorer() # Model load
    text1 = "This is a sample student answer that is somewhat long and complex." * 10
    text2 = "This is a model answer that matches the student to some degree." * 10
    
    start = time.time()
    scorer.evaluate_single_answer(text1, text2)
    print(f"Scoring (Single Answer): {time.time() - start:.4f}s")

if __name__ == "__main__":
    profile_pipeline()
