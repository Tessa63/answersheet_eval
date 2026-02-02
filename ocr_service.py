import easyocr
from PIL import Image, ImageEnhance, ImageFilter
import re
import os
from pdf2image import convert_from_path
import sys
import numpy as np

# Try to find poppler in common locations, otherwise hope it's in PATH
POPPLER_PATH = None
possible_poppler_paths = [
    r"C:\poppler\poppler-23.11.0\Library\bin",
    r"C:\Program Files\poppler-0.68.0\bin",
]

for p in possible_poppler_paths:
    if os.path.isdir(p):
        POPPLER_PATH = p
        break


# Initialize EasyOCR reader globally to avoid reloading it (it's heavy)
# 'en' for English. You can add more languages if needed.
# GPU=True if available, else False.
READER = None

def get_reader():
    global READER
    if READER is None:
        print("Loading EasyOCR model... this might take a moment.")
        READER = easyocr.Reader(['en'])
    return READER

import cv2
import numpy as np

def preprocess_image(image):
    """
    Apply advanced image processing to improve OCR accuracy for messy handwriting.
    Uses CLAHE (Contrast Limited Adaptive Histogram Equalization) to handle uneven lighting
    while preserving grayscale details for the deep learning model.
    """
    # 1. Convert PIL Image to Numpy Array (OpenCV format)
    if not isinstance(image, np.ndarray):
        img = np.array(image)
    else:
        img = image

    # 2. Convert to Grayscale
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    else:
        gray = img

    # 3. Denoising
    # Remove noise while keeping edges sharp (Bilateral Filter is good for this)
    # d=9, sigmaColor=75, sigmaSpace=75 are standard starting points
    denoised = cv2.bilateralFilter(gray, 9, 75, 75)

    # 4. CLAHE (Contrast Limited Adaptive Histogram Equalization)
    # This enhances local contrast (great for shadows) without amplifying noise too much.
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(denoised)

    # 5. Optional: Slight sharpening
    kernel = np.array([[0, -1, 0], 
                       [-1, 5,-1], 
                       [0, -1, 0]])
    sharpened = cv2.filter2D(enhanced, -1, kernel)

    return sharpened

def extract_text_from_file(file_path):
    """
    Extracts text from a PDF or Image file using OCR.
    """
    text = ""
    
    try:
        reader = get_reader()
        
        # -------- PDF HANDLING --------
        if file_path.lower().endswith(".pdf"):
            if POPPLER_PATH:
                images = convert_from_path(file_path, poppler_path=POPPLER_PATH, dpi=300)
            else:
                images = convert_from_path(file_path, dpi=300)
                
            for img in images:
                # Preprocess for better handwriting recognition
                # EasyOCR works on numpy arrays or file paths. PIL images work too but 
                # converting to numpy array is standard for cv2-based backends.
                processed_img = preprocess_image(img)
                
                # Convert PIL to numpy array for EasyOCR (optional, but handled internally usually)
                # simpler: pass the PIL image or save temp. EasyOCR supports PIL images directly in newer versions
                # or we can pass numpy array.
                img_np = np.array(processed_img)
                
                # detail=0 returns just the list of text strings
                results = reader.readtext(img_np, detail=0, paragraph=True)
                text += "\n".join(results) + "\n\n"

        # -------- IMAGE HANDLING --------
        else:
            img = Image.open(file_path)
            processed_img = preprocess_image(img)
            img_np = np.array(processed_img)
            
            results = reader.readtext(img_np, detail=0, paragraph=True)
            text = "\n".join(results)
            
    except Exception as e:
        print(f"Error during OCR: {e}")
        return ""
    
    return text
