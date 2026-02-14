import cv2
import numpy as np
from ocr_service import remove_red_ink
import os

def test_red_ink_removal():
    # 1. Create a dummy image (White background, Black text, Red lines)
    ht, wd = 200, 400
    img = np.ones((ht, wd, 3), dtype=np.uint8) * 255
    
    # Draw Black Text
    cv2.putText(img, "Hello World", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    
    # Draw Red Lines (Correction marks)
    cv2.line(img, (40, 110), (250, 90), (0, 0, 255), 3) # Pure Red
    cv2.line(img, (100, 50), (120, 150), (50, 50, 200), 2) # ish Red
    
    # Save original
    cv2.imwrite("test_red_input.png", img)
    
    # 2. Process
    cleaned = remove_red_ink(img)
    cv2.imwrite("test_red_output.png", cleaned)
    
    # 3. Verify
    # Check specific pixels where red line was.
    # Line 1 approx center: (145, 100).
    # Original should be red. Cleaned should be white.
    
    # Let's check the mask area.
    # We can check if any red pixels remain?
    
    hsv = cv2.cvtColor(cleaned, cv2.COLOR_BGR2HSV)
    lower_red1 = np.array([0, 50, 50])
    upper_red1 = np.array([10, 255, 255])
    mask = cv2.inRange(hsv, lower_red1, upper_red1)
    
    red_pixels = cv2.countNonZero(mask)
    print(f"Remaining Red Pixels: {red_pixels}")
    
    if red_pixels < 5:
        print("PASS: Red ink removed successfully.")
    else:
        print("FAIL: Red ink still present.")

if __name__ == "__main__":
    test_red_ink_removal()
