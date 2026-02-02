import re
from difflib import get_close_matches

# Common academic/ML words to help with context-aware correction if needed
# This can be expanded, but we shouldn't rely on it exclusively.
COMMON_TERMS = [
    "decision", "tree", "pruning", "prepruning", "postpruning",
    "overfitting", "outliers", "simplify", "reduce",
    "training", "data", "model", "classification",
    "early", "stopping", "nodes", "branches", "algorithm",
    "learning", "supervised", "unsupervised", "regression"
]

def clean_text(text):
    """
    Standardizes text: lowercase, removes special chars, cleans whitespace.
    """
    if not text:
        return ""
        
    # Convert to lowercase
    text = text.lower()
    
    # Remove special characters (keep a-z and 0-9)
    # Note: Depending on requirements, we might want to keep punctuation, 
    # but the original script removed it, so preserving that behavior.
    text = re.sub(r"[^a-z0-9\s]", "", text)
    
    # Remove extra spaces
    text = re.sub(r"\s+", " ", text).strip()
    
    return text

def correct_spelling(text, custom_dictionary=None, cutoff=0.6):
    """
    Simple spell correction based on a known dictionary of terms.
    If a word is 'close enough' to a dictionary term, replace it.
    """
    if not text:
        return ""

    if custom_dictionary is None:
        dictionary = COMMON_TERMS
    else:
        dictionary = COMMON_TERMS + list(custom_dictionary)

    words = text.split()
    corrected_words = []

    for word in words:
        # Find close matches
        matches = get_close_matches(word, dictionary, n=1, cutoff=cutoff)
        if matches:
            corrected_words.append(matches[0])
        else:
            corrected_words.append(word)
    
    return " ".join(corrected_words)
