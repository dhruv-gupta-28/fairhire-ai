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
        raise ValueError(f"Could not load CSV data: {str(e)}")

    if df.empty:
        raise ValueError("The uploaded CSV file is completely empty.")

    pipeline = MLPipeline(random_state=42)
    pipeline_result = pipeline.train(df)
    
    if pipeline_result.get("failed"):
        raise ValueError(f"Pipeline Analysis Failed Natively: {pipeline_result.get('error')}")

    # Re-map organic fairness data to React Dashboard legacy schema implicitly!
    gender_bias = {}
    if "gender" in pipeline_result["fairness"]:
        gender_bias = {k: v["rate"] for k, v in pipeline_result["fairness"]["gender"]["groups"].items()}

    race_bias = {}
    if "race" in pipeline_result["fairness"]:
        race_bias = {k: v["rate"] for k, v in pipeline_result["fairness"]["race"]["groups"].items()}

    age_bias = {}
    if "age" in pipeline_result["fairness"]:
        age_bias = {k: v["rate"] for k, v in pipeline_result["fairness"]["age"]["groups"].items()}
            
    overall_score = pipeline_result["bias_summary"]["fairness_score"]

    bias_payload = {
        "fairness_score": overall_score,
        "gender_bias": gender_bias,
        "age_bias": age_bias,
        "race_bias": race_bias,
        "education_bias": {}
    }

    explanation_result = generate_bias_explanation(bias_payload)
    recommendations_result = generate_suggestions(bias_payload)
    summary_result = generate_detailed_summary(bias_payload)

    dataset_info = {
        "rows": int(len(df)),
        "features": int(len(df.columns)),
        "columns": df.columns.tolist()
    }

    # Merging the new SHAP architecture directly into the response payload mapping
    result = {
        "model_metrics": pipeline_result["metrics"],
        "fairness_score": overall_score,
        "summary": summary_result["summary"],
        "gender_bias": gender_bias,
        "age_bias": age_bias,
        "race_bias": race_bias,
        "education_bias": {},
        "occupation_bias": {},
        "explanation": explanation_result["explanations"],
        "recommendations": recommendations_result["recommendations"],
        "ai_used": summary_result["ai_used"] or recommendations_result["ai_used"] or explanation_result["ai_used"],
        "dataset_info": dataset_info,
        "advanced_fairness": {
            "overall_score": overall_score,
            "severity": pipeline_result["bias_summary"]["overall_severity"],
            "metric_gaps": {},
            "weights": {},
            "thresholds": {},
            "protected_attributes_evaluated": list(pipeline_result["fairness"].keys())
        },
        "flagged_metrics": pipeline_result["fairness"],
        "target_column": pipeline_result["target_column"],
        "target_confidence": pipeline_result["target_confidence"],
        "feature_summary": pipeline_result["feature_summary"],
        "predictions_sample": pipeline_result["predictions_sample"],
        "class_distribution": pipeline_result["class_distribution"],
        "feature_importance": pipeline_result["feature_importance"],
        "charts": pipeline_result["charts"]
    }

    MODEL_CACHE[cache_key] = result
    if len(MODEL_CACHE) > MODEL_CACHE_MAX_SIZE:
        MODEL_CACHE.popitem(last=False)

    if save_to_db and user_id:
        try:
            Analysis.create(user_id, dataset_info, overall_score, result)
        except Exception as e:
            logger.warning(f"Failed to save analysis record: {e}")

    return result