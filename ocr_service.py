import easyocr
from PIL import Image, ImageEnhance, ImageFilter
import re
import os
from pdf2image import convert_from_path
import sys
import numpy as np
import cv2
import pytesseract

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
READER = None

def get_reader():
    global READER
    if READER is None:
        print("Loading EasyOCR model... this might take a moment.")
        READER = easyocr.Reader(['en'])
    return READER


def preprocess_light(image):
    """
    Light preprocessing for handwritten text -- preserves ink details
    that heavy CLAHE/sharpening destroys. Only does:
      1. Grayscale conversion
      2. Light denoising
    """
    if not isinstance(image, np.ndarray):
        img = np.array(image)
    else:
        img = image

    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    else:
        gray = img

    # Light gaussian blur to reduce noise without destroying strokes
    denoised = cv2.GaussianBlur(gray, (3, 3), 0)
    
    return denoised


def preprocess_for_tesseract(image):
    """
    Preprocessing optimized for Tesseract: adaptive thresholding to
    create clean binary image from handwriting.
    """
    if not isinstance(image, np.ndarray):
        img = np.array(image)
    else:
        img = image
    
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    else:
        gray = img
    
    # Adaptive threshold handles uneven lighting on paper
    binary = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY, 31, 12
    )
    
    return binary


def remove_red_ink(image):
    """
    Removes red ink (teacher's grading) from the image by replacing it with white.
    """
    if not isinstance(image, np.ndarray):
        img = np.array(image)
    else:
        img = image.copy()
        
    if len(img.shape) == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    elif img.shape[2] == 4:
        img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
        
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    
    # Red wraps around 180 in HSV, so we need two ranges
    lower_red1 = np.array([0, 50, 50])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([170, 50, 50])
    upper_red2 = np.array([180, 255, 255])
    
    mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
    mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
    mask = mask1 + mask2
    
    # Dilate mask slightly to catch edges of ink
    kernel = np.ones((3,3), np.uint8)
    mask = cv2.dilate(mask, kernel, iterations=1)
    
    # Replace red pixels with white
    img[mask > 0] = [255, 255, 255]
    
    return img


def _count_readable_words(text):
    """Count words that look like actual English words (>= 3 chars, alphabetic)."""
    words = re.findall(r'[a-zA-Z]{3,}', text)
    return len(words)


def ocr_page_dual_engine(img_np):
    """
    Run both EasyOCR and Tesseract on a page, return the better result.
    
    Strategy:
    - EasyOCR: run on raw color image (after red ink removal) -- uses deep learning
    - Tesseract: run on adaptive threshold binary -- better for structured text
    - Pick the result with more readable words (heuristic for quality)
    """
    reader = get_reader()
    
    # --- EasyOCR on lightly processed image ---
    light_img = preprocess_light(img_np)
    try:
        easy_results = reader.readtext(light_img, detail=0, paragraph=True)
        easy_text = "\n".join(easy_results)
    except Exception as e:
        print(f"    EasyOCR error: {e}")
        easy_text = ""
    
    # --- Tesseract on adaptive threshold ---
    binary_img = preprocess_for_tesseract(img_np)
    try:
        tess_text = pytesseract.image_to_string(binary_img, config='--psm 4 --oem 3')
    except Exception as e:
        print(f"    Tesseract error: {e}")
        tess_text = ""
    
    # --- Pick the better result ---
    easy_words = _count_readable_words(easy_text)
    tess_words = _count_readable_words(tess_text)
    
    # Merge: use the one with more readable words  
    # But also combine unique content from both if they're close
    if easy_words == 0 and tess_words == 0:
        # Both failed -- return whatever we got
        return easy_text + "\n" + tess_text
    
    if tess_words > easy_words * 1.3:
        chosen = "Tesseract"
        result = tess_text
    elif easy_words > tess_words * 1.3:
        chosen = "EasyOCR"
        result = easy_text
    else:
        # Similar quality -- merge both for maximum content
        chosen = "Merged"
        result = easy_text + "\n" + tess_text
    
    print(f"    OCR winner: {chosen} (EasyOCR: {easy_words} words, Tesseract: {tess_words} words)")
    
    return result


def extract_text_from_file(file_path):
    """
    Extracts text from a PDF or Image file using dual-engine OCR
    (EasyOCR + Tesseract) with confidence-based selection.
    """
    text = ""
    
    try:
        # -------- PDF HANDLING --------
        if file_path.lower().endswith(".pdf"):
            # Use higher DPI (200) for better handwriting recognition
            if POPPLER_PATH:
                images = convert_from_path(file_path, poppler_path=POPPLER_PATH, dpi=200)
            else:
                images = convert_from_path(file_path, dpi=200)
            
            total_pages = len(images)
            print(f"Processing {total_pages} page(s) from: {os.path.basename(file_path)}")
                
            for i, img in enumerate(images, 1):
                print(f"  OCR page {i}/{total_pages}...")
                # 1. Remove Red Ink first (requires Color image)
                img_np = np.array(img)
                no_red_img = remove_red_ink(img_np)
                
                # 2. Dual-engine OCR
                page_text = ocr_page_dual_engine(no_red_img)
                text += page_text + "\n\n"

        # -------- IMAGE HANDLING --------
        else:
            img = Image.open(file_path)
            img_np = np.array(img)
            
            # 1. Remove Red Ink
            no_red_img = remove_red_ink(img_np)
             
            # 2. Dual-engine OCR
            text = ocr_page_dual_engine(no_red_img)
            
    except Exception as e:
        print(f"Error during OCR: {e}")
        import traceback
        traceback.print_exc()
        return ""
    
    return text
