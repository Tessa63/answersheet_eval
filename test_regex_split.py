
import re

def test_split_behavior():
    pattern = re.compile(
        r'(?:^|\n)\s*(?:Q|Question|Ans|Answer)?\.?\s*[\.\-]?\s*(\d+[a-z]?)\s*[\.\:\-\)\_\ ]',
        re.IGNORECASE
    )
    
    text = "Q1. Answer to q1. \n 2) Answer to q2."
    split_data = pattern.split(text)
    print(f"Split data: {split_data}")
    
    for item in split_data:
        if item is None:
            print("FOUND NONE in split_data!")
            
    # Test strictness of group
    # If the group (\d+[a-z]?) matches, does it ever return None?
    # It shouldn't.
    
    # What if the text has weird encoding?
    
if __name__ == "__main__":
    test_split_behavior()
