import os
os.environ["GEMINI_API_KEY"] = "AIzaSyA1cTVbWHQsw4m_wzLHypXfomSc_ZtZoWk"
from llm_scorer import LLMScorer

scorer = LLMScorer()
res = scorer.score_answer("Patents protect inventions for an extended time.", "Patents provide inventors exclusive rights for 20 years to make, use, and sell.", 5)
print("Score result:", res)
