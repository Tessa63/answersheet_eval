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
    Standardizes text: lowercase, keeps alphanumeric + basic punctuation,
    cleans whitespace. Preserves hyphens, commas, periods for semantic meaning.
    """
    if not text:
        return ""
        
    # Convert to lowercase
    text = text.lower()
    
    # Keep a-z, 0-9, spaces, hyphens, commas, periods (useful for semantic meaning)
    # Remove everything else (brackets, special symbols, etc.)
    text = re.sub(r"[^a-z0-9\s\-,.]", "", text)
    
    # Remove extra spaces
    text = re.sub(r"\s+", " ", text).strip()
    
    return text

def correct_spelling(text, custom_dictionary=None, cutoff=0.75):
    """
    Conservative spell correction based on a known dictionary of terms.
    Only corrects words that are very close to a dictionary term.
    Uses high cutoff (0.75) to avoid aggressively corrupting words.
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
        # Skip very short words (they are usually correct or common words)
        if len(word) <= 3:
            corrected_words.append(word)
            continue
        
        # Skip words that are already in the dictionary (exact match)
        if word in dictionary:
            corrected_words.append(word)
            continue
            
        # Find close matches with high cutoff to avoid aggressive replacement
        matches = get_close_matches(word, dictionary, n=1, cutoff=cutoff)
        if matches:
            match = matches[0]
            # Guard: don't replace if length difference is too big (likely wrong match)
            if abs(len(match) - len(word)) <= 3:
                corrected_words.append(match)
            else:
                corrected_words.append(word)
        else:
            corrected_words.append(word)
    
    return " ".join(corrected_words)
