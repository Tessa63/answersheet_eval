"""
show_ocr_output.py — View cached OCR output from any PDF in a readable format.
Run: python show_ocr_output.py
"""
import os

CACHE_DIR = ".ocr_cache"

# Find all cached files
files = os.listdir(CACHE_DIR)
print(f"\n{'='*60}")
print(f"  OCR CACHE — {len(files)} file(s) found")
print(f"{'='*60}\n")

for fname in sorted(files):
    label = "HANDWRITTEN (student)" if fname.endswith("_hw.txt") else "PRINTED (model/question)"
    path  = os.path.join(CACHE_DIR, fname)

    with open(path, encoding="utf-8") as f:
        text = f.read()

    pages = text.split("---PAGE_BREAK---")
    pages = [p.strip() for p in pages if p.strip()]

    print(f"📄 File: {fname}")
    print(f"   Type: {label}")
    print(f"   Pages: {len(pages)} | Total chars: {len(text)}")
    print()

    for i, page in enumerate(pages, 1):
        print(f"  ── Page {i} ──────────────────────────────────────")
        # Print up to 400 chars per page
        preview = page[:400].replace("\r", "")
        print(f"  {preview}")
        if len(page) > 400:
            print(f"  ... [{len(page)-400} more chars]")
        print()

    print(f"{'─'*60}\n")
