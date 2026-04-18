import pandas as pd
from pathlib import Path
from typing import Dict, Any
import hashlib
import logging
from collections import OrderedDict

from ml.pipeline import MLPipeline
from services.dataset_auditor import DatasetAuditor
from services.workflow import run_bias_mitigation_workflow
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

def analyze_bias(file_path, user_id=None, save_to_db=False, run_mitigation=False, sensitive_columns=None):
    cache_key = get_file_hash(file_path)

    if cache_key in MODEL_CACHE:
        cached = MODEL_CACHE[cache_key].copy()
        return cached

    audit = {}
    try:
        auditor = DatasetAuditor()
        audit_result = auditor.audit(file_path)
        audit_warnings = audit_result.get("warnings", [])
        summary_list = audit_result.get("summary", [])
        severity_counts = {}
        for warning in audit_warnings:
            severity_counts[warning.get("severity", "INFO")] = severity_counts.get(warning.get("severity", "INFO"), 0) + 1

        audit = {
            "warnings": audit_warnings,
            "summary": " ".join(summary_list) if summary_list else "Dataset audit completed.",
            "severity": audit_result.get("severity", "INFO"),
            "severity_counts": severity_counts,
            "details": audit_result.get("audit_details", {})
        }
    except Exception as audit_exc:
        logger.warning(f"Dataset audit failed: {audit_exc}")
        audit = {
            "warnings": [{
                "type": "AUDIT_ERROR",
                "message": str(audit_exc),
                "severity": "WARNING"
            }],
            "summary": "Dataset audit failed, continuing with bias analysis.",
            "severity": "WARNING",
            "severity_counts": {"WARNING": 1},
            "details": {}
        }

    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        logger.error(f"Failed to read CSV file: {e}")
        return {"error": f"Could not load CSV data: {str(e)}", "failed": True, "audit": audit}

    if df.empty:
        return {"error": "The uploaded CSV file is completely empty.", "failed": True, "audit": audit}

    pipeline = MLPipeline(random_state=42)
    pipeline_result = pipeline.train(df)
    
    if pipeline_result.get("failed"):
        pipeline_result["audit"] = audit
        return pipeline_result

    dataset_info = {
        "rows": int(len(df)),
        "features": int(len(df.columns)),
        "columns": df.columns.tolist()
    }
    pipeline_result["dataset_info"] = dataset_info

    if "fairness" in pipeline_result and "gender" in pipeline_result["fairness"]:
        gender_bias = {k: v["rate"] for k, v in pipeline_result["fairness"]["gender"]["groups"].items()}
    else:
        gender_bias = {}

    overall_score = pipeline_result.get("bias_summary", {}).get("fairness_score", pipeline_result.get("fairness_score", 100.0))

    bias_payload = {
        "fairness_score": overall_score,
        "gender_bias": gender_bias,
        "age_bias": {},
        "race_bias": {},
        "education_bias": {}
    }

    recommendations_result = generate_suggestions(bias_payload)
    pipeline_result["recommendations"] = recommendations_result["recommendations"]
    pipeline_result["ai_used"] = recommendations_result["ai_used"]
    pipeline_result["fairness_score"] = overall_score
    pipeline_result["gender_bias"] = gender_bias

    human_summary = []
    score_text = "Low bias detected." if overall_score >= 70 else "Moderate bias detected." if overall_score >= 40 else "High bias detected."
    human_summary.append(score_text)

    if isinstance(pipeline_result.get("bias_by_feature"), list):
        for item in pipeline_result["bias_by_feature"]:
            severity = item.get("severity", "INFO")
            if severity in ["WARNING", "CRITICAL"]:
                human_summary.append(
                    f"{item.get('attribute', 'Attribute')} shows {severity.lower()} disparity with demographic parity gap {item.get('demographic_parity_gap', 0.0):.3f}."
                )

    selection_rates = pipeline_result.get("selection_rates", {})
    for attr, groups in selection_rates.items():
        if isinstance(groups, dict) and len(groups) > 1:
            rates = {g: float(r) for g, r in groups.items()}
            if len(rates) > 1:
                low_group = min(rates, key=rates.get)
                high_group = max(rates, key=rates.get)
                human_summary.append(
                    f"Group '{low_group}' has a lower selection rate ({rates[low_group]:.2f}) than '{high_group}' ({rates[high_group]:.2f}) for {attr}."
                )

    human_readable = {
        "summary": " ".join(human_summary) if human_summary else "Bias analysis completed.",
        "key_findings": human_summary
    }

    response = {
        "audit": audit,
        "before": pipeline_result.copy(),
        "fairness_score": overall_score,
        "bias_level": pipeline_result.get("bias_level", pipeline_result.get("bias_summary", {}).get("bias_level", "Unknown")),
        "bias_by_feature": pipeline_result.get("bias_by_feature", []),
        "selection_rates": pipeline_result.get("selection_rates", {}),
        "shap_summary": pipeline_result.get("shap_summary", {}),
        "human_readable": human_readable,
        **pipeline_result
    }

    if run_mitigation:
        try:
            mitigation_output = run_bias_mitigation_workflow(df, sensitive_cols=sensitive_columns)
            response["mitigation"] = mitigation_output
        except Exception as mitigation_exc:
            logger.warning(f"Mitigation workflow failed: {mitigation_exc}")
            response["mitigation"] = {"error": "Mitigation workflow failed.", "details": str(mitigation_exc)}

    MODEL_CACHE[cache_key] = response
    if len(MODEL_CACHE) > MODEL_CACHE_MAX_SIZE:
        MODEL_CACHE.popitem(last=False)

    if save_to_db and user_id:
        try:
            Analysis.create(user_id, dataset_info, overall_score, response)
        except Exception as e:
            logger.warning(f"Failed to save analysis record: {e}")

    return response