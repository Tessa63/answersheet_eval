import re

text = """
53: No. Questions Marks| CO
55: 1. |Is gr+1 = Of2") ? Is 92 = Of2") ? Justify your answer. 3 |coO1
57: 2. |Match the following 3 |cO1
104: 7.a) | 1. Prove that lon +5 4 ew ?). 8 |cO1
"""

# The regex from question_paper.py
line_pattern = re.compile(
    r'^\s*(\d{1,2})\s*'              # Question number (1-2 digits)
    r'[\.\)]*\s*'                     # Optional . or )
    r'([a-z]?\s*[\)\}\]]*)?'          # Optional sub-part like "a)", "b}", etc
    r'\s*[\|\[\(]*\s*'                # Optional pipe, bracket
    r'(.*?)'                          # Question text (non-greedy)
    r'\s+(\d{1,2})\s*'               # Marks (1-2 digit number before CO)
    r'[/\|\s]*'                       # Optional /| separators
    r'[Cc]+[Oo]+\s*\d'               # CO1, CO2, CO3, cO1, CcO3, etc.
)

print("regex pattern:", line_pattern.pattern)

for line in text.split('\n'):
    line = line.strip()
    # Remove the "55: " prefix if checking the debug_qp_text style, 
    # BUT the actual file content won't have "55: ". 
    # The snippet I pasted above has "55: " because I copied from view_file output?
    # Wait, in the previous step I decided "55:" IS NOT in the file.
    # The file content is "1. |Is..."
    
    # Simulating what the file content really is:
    if ":" in line and line.split(':')[0].isdigit():
        # Strip the "55: " part for testing actual line matching
        parts = line.split(':', 1)
        if len(parts) > 1:
            line_content = parts[1].strip()
    else:
        line_content = line

    print(f"\nTesting line: '{line_content}'")
    m = line_pattern.match(line_content)
    if m:
        print("  MATCHED!")
        print("  Groups:", m.groups())
    else:
        print("  NO MATCH")
