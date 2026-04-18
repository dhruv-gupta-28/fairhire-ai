import logging
from typing import Any, Dict, List, Optional

import pandas as pd

from ml.pipeline import MLPipeline
from services.mitigation import BiasMitigationEngine

logger = logging.getLogger(__name__)

SENSITIVE_KEYWORDS = ["gender", "sex", "race", "ethnicity", "age", "dob", "veteran", "disability"]


def detect_sensitive_columns(df: pd.DataFrame) -> List[str]:
    return [
        col for col in df.columns
        if any(keyword in str(col).lower() for keyword in SENSITIVE_KEYWORDS)
    ]


def _format_risk_transition(before: str, after: str) -> str:
    return f"{before} → {after}"


def _create_human_summary(before: Dict[str, Any], mitigation: Dict[str, Any]) -> str:
    before_level = before.get("bias_level", before.get("bias_summary", {}).get("bias_level", "Unknown"))
    after_info = mitigation.get("after", {})
    after_level = after_info.get("risk_level") or after_info.get("bias_level") or before_level
    fairness_before = float(before.get("fairness_score", 0.0))
    fairness_after = float(mitigation.get("fairness_after", after_info.get("fairness_score", fairness_before)))
    accuracy_before = float(before.get("metrics", {}).get("accuracy", before.get("accuracy", 0.0)))
    accuracy_after = float(mitigation.get("after", {}).get("accuracy", accuracy_before))

    if mitigation.get("tradeoff_log") and any(entry.get("rollback") for entry in mitigation.get("tradeoff_log", [])):
        return (
            f"Mitigation was rolled back to preserve model accuracy. "
            f"Bias remained at {before_level} and fairness score stayed at {fairness_before:.2f}. "
            "Accuracy was preserved."
        )

    fairness_delta = round(fairness_after - fairness_before, 2)
    accuracy_delta = round(accuracy_after - accuracy_before, 4)

    summary = [f"Bias reduced from {before_level} → {after_level}."]
    if fairness_delta > 0:
        summary.append(f"Fairness score improved by +{fairness_delta}.")
    elif fairness_delta == 0:
        summary.append("Fairness score remained stable.")
    else:
        summary.append(f"Fairness score shifted by {fairness_delta}.")

    if accuracy_delta < 0:
        summary.append(f"Minor accuracy trade-off observed (-{abs(accuracy_delta):.4f}).")
    else:
        summary.append("Accuracy remained stable.")

    return " ".join(summary)


def run_bias_mitigation_workflow(
    df: pd.DataFrame,
    sensitive_cols: Optional[List[str]] = None,
    max_accuracy_drop: float = 0.05
) -> Dict[str, Any]:
    pipeline = MLPipeline(random_state=42)
    baseline_result = pipeline.train(df)

    if baseline_result.get("failed"):
        return baseline_result

    if sensitive_cols is None:
        sensitive_cols = detect_sensitive_columns(df)

    baseline_metrics = {
        "accuracy": baseline_result.get("metrics", {}).get("accuracy", 0.0),
        "fairness_score": baseline_result.get("fairness_score", 0.0),
        "bias_level": baseline_result.get("bias_level", baseline_result.get("bias_summary", {}).get("bias_level", "Unknown")),
        "risk_level": baseline_result.get("bias_level", baseline_result.get("bias_summary", {}).get("bias_level", "Unknown"))
    }

    mitigation_engine = BiasMitigationEngine(min_accuracy_drop=max_accuracy_drop)
    mitigation_result = mitigation_engine.mitigate_and_retrain(
        df,
        baseline_result.get("target_column", "target"),
        sensitive_cols,
        baseline_metrics,
        baseline_pipeline=None,
        max_accuracy_drop=max_accuracy_drop
    )

    response = {
        "before": {
            "accuracy": baseline_metrics["accuracy"],
            "fairness_score": baseline_metrics["fairness_score"],
            "bias_level": baseline_metrics["bias_level"],
            "risk_level": baseline_metrics["risk_level"],
            "metrics": baseline_result.get("metrics", {}),
            "fairness_metrics": baseline_result.get("fairness_metrics", {}),
            "bias_by_feature": baseline_result.get("bias_by_feature", []),
        },
        "after": mitigation_result.get("after", {}),
        "accuracy_before": baseline_metrics["accuracy"],
        "accuracy_after": mitigation_result.get("after", {}).get("accuracy", baseline_metrics["accuracy"]),
        "fairness_before": baseline_metrics["fairness_score"],
        "fairness_after": mitigation_result.get("after", {}).get("fairness_score", baseline_metrics["fairness_score"]),
        "improvement": mitigation_result.get("improvement", "Mitigation process completed."),
        "risk_transition": mitigation_result.get("risk_transition", _format_risk_transition(baseline_metrics["risk_level"], baseline_metrics["risk_level"])),
        "tradeoff_log": mitigation_result.get("tradeoff_log", []),
        "human_summary": _create_human_summary(baseline_result, mitigation_result),
        "mitigation_details": mitigation_result
    }

    return response
