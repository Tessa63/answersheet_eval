from text_utils import correct_spelling, clean_text

# 1. Simulated Garbled OCR Output (from previous step)
ocr_output = """
2 oeirion . 4~ 4^ Rave 947 ba O4 Lot Deetsioatut paunin]
an3lu
Qelsu a4
Un Ba ARa a wa Iu les
P4 Mt.ka Lizh MA R Pkuni 7
F plunbntMela Deetsioatut Iul 1s Raullad bikeu_tonstaudies . l Ikis Hpapatanb , k Ea Routd Anomaliek 944 taud A conGlAucko+ nu& KRi4 #8_Fue
ost pnitg Mle4 Ta. t pJ : Aueins hua pkuri 65 A~ 1,, do~ de & 3leye? " Mac bllann a 0 Y hnoidu  tu_hs _ 9 Aaenan An S Lbaa-sl , 2ld 'ple: 3 4iss e7 4 M 5o petiv ) alall,
Ta
"""

# 2. Simulated Model Answer (Ground Truth)
model_answer_text = """
Decision tree pruning is a technique to reduce the size of decision trees by removing sections of the tree that are non-critical and redundant to classify instances. Pruning reduces the complexity of the final classifier, and hence improves predictive accuracy by the reduction of overfitting.
Pruning methods can be divided into two types: Pre-pruning and Post-pruning.
Pre-pruning halts the construction of the tree early.
Post-pruning removes branches from a fully grown tree.
"""

# 3. Build Dynamic Dictionary from Model Answer
def build_dictionary(text):
    cleaned = clean_text(text)
    return list(set(cleaned.split()))

custom_dict = build_dictionary(model_answer_text)

print(f"Dictionary Size: {len(custom_dict)}")
print(f"Sample Words: {custom_dict[:10]}")

# 4. Clean OCR Output
cleaned_ocr = clean_text(ocr_output)
print(f"\nCleaned OCR: {cleaned_ocr[:100]}...")

# 5. Apply Correction
print("\nApplying correction with cutoff 0.6...")
from difflib import get_close_matches

def custom_correct(text, dictionary):
    words = text.split()
    corrected = []
    for w in words:
        matches = get_close_matches(w, dictionary, n=1, cutoff=0.6)
        corrected.append(matches[0] if matches else w)
    return " ".join(corrected)

corrected = custom_correct(cleaned_ocr, custom_dict)

print("\n--- BEFORE ---")
print(cleaned_ocr)
print("\n--- AFTER ---")
print(corrected)

# 6. Check for key terms
key_terms = ["decision", "tree", "pruning", "overfitting"]
found = [t for t in key_terms if t in corrected]
print(f"\nRecovered Key Terms: {found}")
