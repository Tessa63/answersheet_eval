"""
ocr_pipeline.py — Local OCR Pipeline (Student's Contribution)

Architecture:
  - Student answer sheets (handwritten): TrOCR (microsoft/trocr-base-handwritten)
  - Model answers / Question papers (printed): EasyOCR + Tesseract dual-engine
  - Preprocessing: OpenCV (grayscale, denoise, adaptive threshold, deskew)
  - Red ink removal: HSV-based masking
  - Results cached by file MD5 hash to avoid re-running OCR on the same file

This module is the core student contribution. Gemini is only used AFTER this
for evaluation/grading, NOT for text extraction.
"""

import os
import re
import time
import json
import hashlib
import traceback

import numpy as np
import cv2
from PIL import Image
from pdf2image import convert_from_path

# ── EasyOCR (lazy loaded) ──────────────────────────────────────────────────
_easyocr_reader = None

def _get_easyocr():
    global _easyocr_reader
    if _easyocr_reader is None:
        print("[OCR] Loading EasyOCR model...")
        import easyocr
        _easyocr_reader = easyocr.Reader(['en'], gpu=False)
        print("[OCR] EasyOCR ready.")
    return _easyocr_reader


# ── TrOCR (lazy loaded) — for Handwritten text ────────────────────────────
_trocr_processor = None
_trocr_model = None

def _get_trocr():
    global _trocr_processor, _trocr_model
    if _trocr_processor is None:
        print("[OCR] Loading TrOCR model (first time may take a while)...")
        from transformers import TrOCRProcessor, VisionEncoderDecoderModel
        import torch
        model_name = "microsoft/trocr-base-handwritten"
        _trocr_processor = TrOCRProcessor.from_pretrained(model_name)
        _trocr_model = VisionEncoderDecoderModel.from_pretrained(model_name)
        _trocr_model.eval()
        print("[OCR] TrOCR ready.")
    return _trocr_processor, _trocr_model


# ── OCR Cache ──────────────────────────────────────────────────────────────
_CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".ocr_cache")
os.makedirs(_CACHE_DIR, exist_ok=True)

def _file_hash(path: str) -> str:
    h = hashlib.md5()
    with open(path, 'rb') as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def _read_cache(key: str):
    p = os.path.join(_CACHE_DIR, f"{key}.txt")
    if os.path.exists(p):
        with open(p, 'r', encoding='utf-8') as f:
            print(f"[OCR Cache] HIT — loaded from cache")
            return f.read()
    return None

def _write_cache(key: str, text: str):
    p = os.path.join(_CACHE_DIR, f"{key}.txt")
    with open(p, 'w', encoding='utf-8') as f:
        f.write(text)
    print(f"[OCR Cache] Saved ({len(text)} chars)")


# ── Poppler Path (Windows) ─────────────────────────────────────────────────
POPPLER_PATH = None
for candidate in [
    r"C:\poppler\poppler-23.11.0\Library\bin",
    r"C:\poppler\Library\bin",
    r"C:\Program Files\poppler\Library\bin",
    r"C:\Program Files\poppler-0.68.0\bin",
]:
    if os.path.isdir(candidate):
        POPPLER_PATH = candidate
        break


# ══════════════════════════════════════════════════════════════════════════
#  PREPROCESSING
# ══════════════════════════════════════════════════════════════════════════

def remove_red_ink(img_np: np.ndarray) -> np.ndarray:
    """Remove red ink (teacher corrections) from a colour image."""
    img = img_np.copy()
    if len(img.shape) == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    elif img.shape[2] == 4:
        img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)

    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    mask1 = cv2.inRange(hsv, np.array([0, 50, 50]),   np.array([10, 255, 255]))
    mask2 = cv2.inRange(hsv, np.array([170, 50, 50]), np.array([180, 255, 255]))
    mask  = cv2.dilate(mask1 | mask2, np.ones((3, 3), np.uint8), iterations=1)
    img[mask > 0] = [255, 255, 255]
    return img


def preprocess_for_ocr(img_np: np.ndarray) -> np.ndarray:
    """
    Preprocessing tuned for handwritten text:
      1. Grayscale
      2. Slight gaussian blur (noise reduction)
      3. Adaptive threshold → clean binary image
    """
    if len(img_np.shape) == 3:
        gray = cv2.cvtColor(img_np, cv2.COLOR_BGR2GRAY)
    else:
        gray = img_np

    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    binary  = cv2.adaptiveThreshold(
        blurred, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 31, 12
    )
    return binary


def deskew(img_np: np.ndarray) -> np.ndarray:
    """Correct slight rotation (skew) common in scanned answer sheets."""
    gray = cv2.cvtColor(img_np, cv2.COLOR_BGR2GRAY) if len(img_np.shape) == 3 else img_np
    coords = np.column_stack(np.where(gray < 127))
    if len(coords) < 10:
        return img_np
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = 90 + angle
    if abs(angle) < 0.5:
        return img_np   # Already straight enough
    h, w = img_np.shape[:2]
    M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
    rotated = cv2.warpAffine(img_np, M, (w, h),
                             flags=cv2.INTER_CUBIC,
                             borderMode=cv2.BORDER_REPLICATE)
    return rotated


# ══════════════════════════════════════════════════════════════════════════
#  LINE SEGMENTATION
# ══════════════════════════════════════════════════════════════════════════

def segment_lines(binary_img: np.ndarray, min_height: int = 15, max_height: int = 120):
    """
    Horizontal projection profiling to cut a page into individual text lines.
    Returns list of (y_start, y_end) tuples for each detected line.
    """
    # Invert so text = white, background = black for projection
    inv = cv2.bitwise_not(binary_img)
    projection = np.sum(inv, axis=1)  # Sum across columns for each row

    threshold = projection.max() * 0.05  # 5% of peak = "has text"
    in_line = False
    lines = []
    y_start = 0

    for y, val in enumerate(projection):
        if not in_line and val > threshold:
            in_line = True
            y_start = y
        elif in_line and val <= threshold:
            in_line = False
            height = y - y_start
            if min_height <= height <= max_height:
                lines.append((max(0, y_start - 2), min(binary_img.shape[0], y + 2)))

    if in_line:
        height = len(projection) - y_start
        if min_height <= height <= max_height:
            lines.append((y_start, len(projection)))

    return lines


# ══════════════════════════════════════════════════════════════════════════
#  HANDWRITTEN OCR
#  Default: EasyOCR (fast, ~3-10s/page, good handwriting support)
#  Optional: TrOCR — set USE_TROCR = True below (slow without GPU, ~4min/page)
# ══════════════════════════════════════════════════════════════════════════

USE_TROCR = False   # Set True only if you have a GPU or don't mind slow speed


def _trocr_on_lines(img_np: np.ndarray) -> str:
    """
    Run TrOCR on each detected text line.
    Only used when USE_TROCR = True. Very slow on CPU (4+ min/page).
    """
    import torch
    processor, model = _get_trocr()

    binary = preprocess_for_ocr(img_np)
    lines  = segment_lines(binary)

    if not lines:
        print("[OCR] No lines detected, running TrOCR on whole image")
        lines = [(0, img_np.shape[0])]

    texts = []
    pil_source = Image.fromarray(cv2.cvtColor(img_np, cv2.COLOR_BGR2RGB))

    for (y0, y1) in lines:
        line_img = pil_source.crop((0, max(0, y0 - 2), pil_source.width, y1 + 2))
        try:
            pixel_values = processor(images=line_img, return_tensors="pt").pixel_values
            with torch.no_grad():
                generated_ids = model.generate(pixel_values, max_new_tokens=128)
            text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0].strip()
            if text:
                texts.append(text)
        except Exception as e:
            print(f"[OCR] TrOCR line error: {e}")
            continue

    result = "\n".join(texts)
    readable_words = len(re.findall(r'[a-zA-Z]{3,}', result))
    if readable_words < 5:
        print(f"[OCR] TrOCR got only {readable_words} words, falling back to EasyOCR...")
        result = _easyocr_on_image(img_np)
    return result


def _handwriting_ocr_on_image(img_np: np.ndarray) -> str:
    """
    Handwriting OCR dispatcher.
    - Default (USE_TROCR=False): EasyOCR — fast (~3-10s/page), good accuracy
    - Optional (USE_TROCR=True): TrOCR  — slower but higher accuracy with GPU
    """
    if USE_TROCR:
        return _trocr_on_lines(img_np)

    # EasyOCR with paragraph mode — handles handwriting well
    reader = _get_easyocr()
    try:
        # Use the original RGB-like image (EasyOCR works better on colour)
        results = reader.readtext(img_np, detail=0, paragraph=True)
        text = "\n".join(results)
        readable = len(re.findall(r'[a-zA-Z]{3,}', text))
        print(f"    [OCR] EasyOCR handwriting: {readable} words extracted")
        return text
    except Exception as e:
        print(f"[OCR] EasyOCR handwriting error: {e}")
        return ""



# ══════════════════════════════════════════════════════════════════════════
#  PRINTED OCR — EasyOCR + Tesseract dual engine
# ══════════════════════════════════════════════════════════════════════════

def _easyocr_on_image(img_np: np.ndarray) -> str:
    """Run EasyOCR on a BGR numpy image."""
    reader = _get_easyocr()
    light = cv2.GaussianBlur(img_np, (3, 3), 0) if len(img_np.shape) == 3 else img_np
    try:
        results = reader.readtext(light, detail=0, paragraph=True)
        return "\n".join(results)
    except Exception as e:
        print(f"[OCR] EasyOCR error: {e}")
        return ""


def _tesseract_on_image(img_np: np.ndarray) -> str:
    """Run Tesseract on a preprocessed binary image."""
    try:
        import pytesseract
        binary = preprocess_for_ocr(img_np)
        return pytesseract.image_to_string(binary, config='--psm 4 --oem 3')
    except Exception as e:
        print(f"[OCR] Tesseract error: {e}")
        return ""


def _printed_ocr_on_image(img_np: np.ndarray) -> str:
    """
    Dual-engine OCR for printed text (model answer, question paper).
    Runs both EasyOCR and Tesseract, then picks the better result.
    """
    easy_text = _easyocr_on_image(img_np)
    tess_text = _tesseract_on_image(img_np)

    easy_words = len(re.findall(r'[a-zA-Z]{3,}', easy_text))
    tess_words = len(re.findall(r'[a-zA-Z]{3,}', tess_text))

    print(f"    [OCR] EasyOCR: {easy_words} words | Tesseract: {tess_words} words")

    if tess_words > easy_words * 1.3:
        return tess_text
    elif easy_words > tess_words * 1.3:
        return easy_text
    else:
        return easy_text + "\n" + tess_text  # Merge when similar quality


# ══════════════════════════════════════════════════════════════════════════
#  MAIN PUBLIC API
# ══════════════════════════════════════════════════════════════════════════

def extract_text_from_pdf(pdf_path: str, is_handwritten: bool = True) -> str:
    """
    Extract text from a PDF file (or image) using local OCR.

    Args:
        pdf_path:       Path to the PDF file.
        is_handwritten: True  → use TrOCR (handwritten — student answer sheets)
                        False → use EasyOCR + Tesseract (printed — model answers, question papers)

    Returns:
        Extracted text as a single string.
    """
    print(f"[OCR] Extracting: {os.path.basename(pdf_path)} | handwritten={is_handwritten}")

    # Cache check
    try:
        fhash = _file_hash(pdf_path)
        cache_key = fhash + ("_hw" if is_handwritten else "_pr")
        cached = _read_cache(cache_key)
        if cached is not None:
            return cached
    except Exception as e:
        print(f"[OCR Cache] Cache check error (non-fatal): {e}")
        fhash = None
        cache_key = None

    full_text = ""

    try:
        # ── PDF → Pages ──────────────────────────────────────────────────
        if pdf_path.lower().endswith(".pdf"):
            convert_kwargs = dict(dpi=200)
            if POPPLER_PATH:
                convert_kwargs["poppler_path"] = POPPLER_PATH

            images = convert_from_path(pdf_path, **convert_kwargs)
            print(f"[OCR] {len(images)} page(s) in PDF")

            for i, pil_img in enumerate(images, 1):
                print(f"[OCR] Processing page {i}/{len(images)}...")
                page_start = time.time()

                img_np = np.array(pil_img)
                img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)

                # Remove red teacher ink before OCR
                img_bgr = remove_red_ink(img_bgr)

                # Deskew (helps a lot with scanned sheets)
                img_bgr = deskew(img_bgr)

                if is_handwritten:
                    page_text = _handwriting_ocr_on_image(img_bgr)
                else:
                    page_text = _printed_ocr_on_image(img_bgr)

                word_count = len(re.findall(r'\w+', page_text))
                print(f"    Page {i} done in {time.time() - page_start:.1f}s — {word_count} words")
                full_text += page_text + "\n---PAGE_BREAK---\n"

        # ── Single image file ──────────────────────────────────────────
        else:
            pil_img = Image.open(pdf_path).convert("RGB")
            img_np  = np.array(pil_img)
            img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
            img_bgr = remove_red_ink(img_bgr)
            img_bgr = deskew(img_bgr)

            if is_handwritten:
                full_text = _handwriting_ocr_on_image(img_bgr)
            else:
                full_text = _printed_ocr_on_image(img_bgr)

    except Exception as e:
        print(f"[OCR] Fatal error: {e}")
        traceback.print_exc()
        return ""

    # Save to cache
    if full_text and cache_key:
        try:
            _write_cache(cache_key, full_text)
        except Exception as e:
            print(f"[OCR Cache] Write error (non-fatal): {e}")

    return full_text
