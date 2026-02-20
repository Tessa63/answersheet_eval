
import re

def test_sub_parts_regex():
    # The problematic regex found in pdf_parser.py
    # FIXED Version:
    sub_pattern = re.compile(
        r'(?:^|\n)\s*([a-h]|[ivx]+)\s*[\)\.\-]\s*', 
        re.IGNORECASE
    )
    
    text = "i) Roman numeral one."
    print(f"Testing text: '{text}'")
    
    parts = sub_pattern.split(text)
    print(f"Parts: {parts}")
    
    # Iterate exactly like in the code
    if len(parts) >= 2:
        for i in range(1, len(parts), 2):
            marker = parts[i]
            print(f"Marker found: {marker!r}")
            try:
                marker_lower = marker.lower()
                print(f"Lower: {marker_lower}")
            except AttributeError as e:
                print(f"CRASH: {e}")
                
if __name__ == "__main__":
    test_sub_parts_regex()
