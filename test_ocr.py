import ssl

# Disable SSL verification
ssl._create_default_https_context = ssl._create_unverified_context

import easyocr

reader = easyocr.Reader(['en'])
print("OCR Ready")
