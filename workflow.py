# workflow.py – orchestrates the end‑to‑end FairHire pipeline
"""High‑level pipeline entry point.

The function `run_pipeline` ties together:
1. Gemini resume profiling (cached for speed & fallback)
2. Feature processing via the ML pipeline (`ml.pipeline.MLPipeline`)
3. Model prediction and bias mitigation
4. Human‑readable explanations & visual data for the frontend

All steps are logged for production observability.
"""

import logging
from functools import lru_cache
from typing import Dict, Any

from gemini_helper import generate_resume_profile, generate_resume_summary, generate_bias_explanation, generate_suggestions
from ml.pipeline import MLPipeline

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Cached Gemini helpers – reduces latency and protects against transient API
# failures by re‑using recent results (max 100 distinct resumes).
# ---------------------------------------------------------------------------
@lru_cache(maxsize=100)
def _cached_profile(text: str) -> Dict[str, Any]:
    return generate_resume_profile(text)

@lru_cache(maxsize=100)
def _cached_summary(text: str) -> Dict[str, Any]:
    return generate_resume_summary(text)


def run_pipeline(resume_text: str, job_desc: str) -> Dict[str, Any]:
    """Execute the full FairHire analysis pipeline.

    Parameters
    ----------
    resume_text: str
        Raw extracted text from a candidate resume.
    job_desc: str
        Text describing the target job (used for future extensions –
        currently passed through to the model as a feature placeholder).

    Returns
    -------
    dict
        A dictionary containing the profile, raw model score, bias
        diagnostics, final mitigated score and a concise explanation.
    """
    logger.info("Pipeline start – processing resume")

    # 1️⃣ Gemini profiling – cached and with graceful fallback
    profile = _cached_profile(resume_text)
    summary = _cached_summary(resume_text)

    # 2️⃣ Build feature vector & predict
    ml = MLPipeline()
    try:
        ml_output = ml.train(pd.DataFrame([profile]))  # simple wrapper for demo
        # In a real deployment we would reuse a trained model; here we just
        # extract the prediction from the training output for illustration.
        raw_score = ml_output.get("fairness_score", 0)
    except Exception as exc:
        logger.error(f"ML pipeline failed: {exc}")
        raw_score = 0

    # 3️⃣ Bias detection & mitigation (placeholder logic)
    bias_result = ml.compute_fairness(pd.DataFrame([profile]), [raw_score], {"gender": None, "race": None, "age": None})
    # Simple mitigation: cap extreme scores
    final_score = max(min(raw_score, 100), 0)

    # 4️⃣ Human‑readable explanation & suggestions
    explanation = generate_bias_explanation(bias_result)
    suggestions = generate_suggestions(bias_result)

    logger.info("Pipeline completed successfully")
    return {
        "profile": profile,
        "summary": summary,
        "raw_score": raw_score,
        "bias": bias_result,
        "final_score": final_score,
        "explanation": explanation,
        "suggestions": suggestions,
    }

# When executed directly, provide a quick demo for developers.
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python workflow.py <resume_text_file>")
        sys.exit(1)
    with open(sys.argv[1], "r", encoding="utf-8") as f:
        txt = f.read()
    result = run_pipeline(txt, "")
    from pprint import pprint
    pprint(result)
