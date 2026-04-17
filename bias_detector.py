import pandas as pd
from pathlib import Path
from typing import Dict
import hashlib
import logging
from collections import OrderedDict

from ml.pipeline import MLPipeline
from gemini_helper import generate_suggestions, generate_detailed_summary, generate_bias_explanation
from config import MODEL_CACHE_MAX_SIZE
from database import Analysis
import numpy as np

logger = logging.getLogger(__name__)

MODEL_CACHE = OrderedDict()

def get_file_hash(file_path):
    hash_sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()

def analyze_bias(file_path, user_id=None, save_to_db=False):
    cache_key = get_file_hash(file_path)

    if cache_key in MODEL_CACHE:
        return MODEL_CACHE[cache_key].copy()

    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        logger.error(f"Failed to read CSV file: {e}")
        return {"error": f"Could not load CSV data: {str(e)}", "failed": True}

    if df.empty:
        return {"error": "The uploaded CSV file is completely empty.", "failed": True}

    pipeline = MLPipeline(random_state=42)
    pipeline_result = pipeline.train(df)
    
    if pipeline_result.get("failed"):
        return pipeline_result

    dataset_info = {
        "rows": int(len(df)),
        "features": int(len(df.columns)),
        "columns": df.columns.tolist()
    }
    
    pipeline_result["dataset_info"] = dataset_info

    # To maintain stability for Gemini Recommendations & Fallbacks, we can bridge it using the old format logic 
    # but append it directly into the result payload
    gender_bias = {}
    if "gender" in pipeline_result.get("fairness", {}):
        gender_bias = {k: v["rate"] for k, v in pipeline_result["fairness"]["gender"]["groups"].items()}
        
    overall_score = pipeline_result.get("bias_summary", {}).get("fairness_score", 100.0)

    bias_payload = {
        "fairness_score": overall_score,
        "gender_bias": gender_bias,
        "age_bias": {},
        "race_bias": {},
        "education_bias": {}
    }

    # Retrieve fallback / AI recommendations dynamically
    recommendations_result = generate_suggestions(bias_payload)

    # Attach Recommendations natively
    pipeline_result["recommendations"] = recommendations_result["recommendations"]
    pipeline_result["ai_used"] = recommendations_result["ai_used"]
    pipeline_result["fairness_score"] = overall_score
    
    # Backwards compatibility
    pipeline_result["gender_bias"] = gender_bias

    MODEL_CACHE[cache_key] = pipeline_result
    if len(MODEL_CACHE) > MODEL_CACHE_MAX_SIZE:
        MODEL_CACHE.popitem(last=False)

    if save_to_db and user_id:
        try:
            Analysis.create(user_id, dataset_info, overall_score, pipeline_result)
        except Exception as e:
            logger.warning(f"Failed to save analysis record: {e}")

    return pipeline_result