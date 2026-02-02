from scoring import SemanticScorer, get_model
from sentence_transformers import util

def debug():
    scorer = SemanticScorer()
    model = scorer.model

    pairs = [
        ("plants use sunlight", "Green flora utilize solar radiation"),
        ("plants use sunlight", "flora utilize solar radiation to"),
        ("plants use sunlight", "utilize solar radiation to create"),
    ]

    print("\n--- Window Size 6 Debug ---")
    for c, s in pairs:
        emb1 = model.encode(c, convert_to_tensor=True)
        emb2 = model.encode(s, convert_to_tensor=True)
        score = float(util.cos_sim(emb1, emb2)[0][0])
        print(f"Concept: '{c}' vs Window: '{s}' => Score: {score:.4f}")

if __name__ == "__main__":
    debug()
