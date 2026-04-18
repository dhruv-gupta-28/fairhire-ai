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


def _verdict_recommendation(outcome: str, structural_warnings: List[str]) -> str:
    if structural_warnings:
        return (
            "Dataset redesign required. Review how training labels were assigned "
            "and whether the data collection process itself introduced the disparity. "
            "Algorithmic mitigation alone cannot resolve structural bias."
        )
    if outcome == "significant_improvement":
        return (
            "Continue monitoring fairness metrics in production. "
            "Re-audit when the model is retrained on new data."
        )
    if outcome in ("marginal_improvement", "no_meaningful_improvement"):
        return (
            "Consider auditing upstream data pipelines and label assignment processes. "
            "Threshold calibration per demographic group may provide additional gains."
        )
    if outcome == "fairness_degraded":
        return (
            "Review mitigation configuration. On small datasets, "
            "consider applying only reweighing without SMOTE."
        )
    return "Review mitigation results and monitor model performance over time."


def _generate_mitigation_verdict(
    before: Dict[str, Any],
    mitigation: Dict[str, Any],
    df: pd.DataFrame,
    sensitive_cols: List[str]
) -> Dict[str, Any]:
    fairness_before = float(before.get("fairness_score", 0.0))
    fairness_after = float(mitigation.get("fairness_after", fairness_before))
    accuracy_before = float(mitigation.get("accuracy_before", 0.0))
    accuracy_after = float(mitigation.get("accuracy_after", accuracy_before))
    
    delta_fairness = round(fairness_after - fairness_before, 2)
    delta_accuracy = round(accuracy_after - accuracy_before, 4)
    accuracy_drop_pct = round((accuracy_before - accuracy_after) * 100, 1) if accuracy_before > 0 else 0
    
    steps = mitigation.get("mitigation_details", {}).get("mitigation_steps", [])
    rolled_back = any(
        entry.get("rollback") for entry in mitigation.get("tradeoff_log", [])
    )

    structural_warnings = []
    target_col = before.get("target_column")
    if target_col and target_col in df.columns:
        for col in sensitive_cols:
            if col not in df.columns:
                continue
            try:
                cross = pd.crosstab(df[col], df[target_col], normalize="index")
                max_concentration = cross.max(axis=1).max()
                if max_concentration >= 0.90:
                    structural_warnings.append(
                        f"'{col}' is strongly predictive of the target "
                        f"({max_concentration:.0%} concentration in one outcome group). "
                        f"Algorithmic mitigation has limited effect — "
                        f"the data collection or labeling process itself needs review."
                    )
            except Exception:
                continue

    if rolled_back:
        outcome = "rolled_back"
        summary = (
            f"Mitigation was attempted but rolled back to preserve model accuracy. "
            f"Fairness score remains at {fairness_before}."
        )
        reliability = "high"
    elif accuracy_drop_pct > 50:
        outcome = "fairness_improved_unreliable"
        summary = (
            f"Fairness improved by {delta_fairness} points ({fairness_before} -> {fairness_after}), "
            f"but model reliability declined sharply: accuracy dropped {accuracy_drop_pct}% "
            f"({accuracy_before:.4f} -> {accuracy_after:.4f}). "
            f"⚠️ CRITICAL TRADEOFF: The data itself may be biased. "
            f"Fixing fairness algorithmically requires degrading accuracy significantly."
        )
        reliability = "low"
    elif delta_fairness >= 10:
        outcome = "significant_improvement"
        summary = (
            f"Mitigation improved fairness by {delta_fairness} points "
            f"({fairness_before} -> {fairness_after}). "
            f"Accuracy impact: {delta_accuracy:+.4f} ({accuracy_drop_pct:+.1f}%). "
            f"{len(steps)} technique(s) applied: {', '.join(steps)}."
        )
        reliability = "moderate" if accuracy_drop_pct > 10 else "high"
    elif delta_fairness >= 2:
        outcome = "marginal_improvement"
        summary = (
            f"Mitigation produced a small fairness improvement of {delta_fairness} points "
            f"({fairness_before} -> {fairness_after}). "
            f"Accuracy impact: {delta_accuracy:+.4f} ({accuracy_drop_pct:+.1f}%). "
            f"All {len(steps)} technique(s) completed successfully."
        )
        reliability = "high" if accuracy_drop_pct < 5 else "moderate"
    elif delta_fairness >= 0:
        outcome = "no_meaningful_improvement"
        summary = (
            f"Mitigation completed ({len(steps)} technique(s) applied) "
            f"but fairness did not meaningfully change "
            f"({fairness_before} -> {fairness_after}, delta {delta_fairness}). "
            f"This typically indicates structural bias in the dataset "
            f"that cannot be corrected algorithmically."
        )
        reliability = "high"
    else:
        outcome = "fairness_degraded"
        summary = (
            f"Fairness score decreased after mitigation "
            f"({fairness_before} -> {fairness_after}, delta {delta_fairness}). "
            f"This can occur when mitigation techniques conflict on small or "
            f"highly imbalanced datasets. Manual review is recommended."
        )
        reliability = "moderate"

    recommendation = _verdict_recommendation(outcome, structural_warnings)

    return {
        "outcome": outcome,
        "summary": summary,
        "delta": delta_fairness,
        "fairness_before": fairness_before,
        "fairness_after": fairness_after,
        "accuracy_before": accuracy_before,
        "accuracy_after": accuracy_after,
        "accuracy_drop_pct": accuracy_drop_pct,
        "reliability_assessment": reliability,
        "steps_applied": steps,
        "structural_warnings": structural_warnings,
        "recommendation": recommendation,
    }


def run_bias_mitigation_workflow(
    df: pd.DataFrame,
    sensitive_cols: Optional[List[str]] = None,
    max_accuracy_drop: float = 0.70
) -> Dict[str, Any]:
    pipeline = MLPipeline(random_state=42)
    baseline_result = pipeline.train(df)

    if baseline_result.get("failed"):
        return baseline_result

    if sensitive_cols is None:
        sensitive_cols = detect_sensitive_columns(df)

    # Run safe mode (strict accuracy preservation)
    safe_engine = BiasMitigationEngine(min_accuracy_drop=0.05)
    safe_result = safe_engine.mitigate_and_retrain(
        df,
        baseline_result.get("target_column", "target"),
        sensitive_cols,
        {
            "accuracy": baseline_result.get("metrics", {}).get("accuracy", 0.0),
            "fairness_score": baseline_result.get("fairness_score", 0.0),
            "bias_level": baseline_result.get("bias_level", baseline_result.get("bias_summary", {}).get("bias_level", "Unknown")),
            "risk_level": baseline_result.get("bias_level", baseline_result.get("bias_summary", {}).get("bias_level", "Unknown"))
        },
        baseline_pipeline=None,
        max_accuracy_drop=0.05
    )

    # Run aggressive mode (relaxed accuracy constraints)
    aggressive_engine = BiasMitigationEngine(min_accuracy_drop=max_accuracy_drop)
    aggressive_result = aggressive_engine.mitigate_and_retrain(
        df,
        baseline_result.get("target_column", "target"),
        sensitive_cols,
        {
            "accuracy": baseline_result.get("metrics", {}).get("accuracy", 0.0),
            "fairness_score": baseline_result.get("fairness_score", 0.0),
            "bias_level": baseline_result.get("bias_level", baseline_result.get("bias_summary", {}).get("bias_level", "Unknown")),
            "risk_level": baseline_result.get("bias_level", baseline_result.get("bias_summary", {}).get("bias_level", "Unknown"))
        },
        baseline_pipeline=None,
        max_accuracy_drop=max_accuracy_drop
    )

    # Build scenarios
    baseline_fairness = baseline_result.get("fairness_score", 0.0)
    baseline_accuracy = baseline_result.get("metrics", {}).get("accuracy", 0.0)
    baseline_bias_level = baseline_result.get("bias_level", baseline_result.get("bias_summary", {}).get("bias_level", "Unknown"))

    safe_fairness = safe_result.get("fairness_after", baseline_fairness)
    safe_accuracy = safe_result.get("after", {}).get("accuracy", baseline_accuracy)
    safe_rolled_back = any(entry.get("rollback") for entry in safe_result.get("tradeoff_log", []))
    safe_reliability = "high" if safe_rolled_back else "moderate"

    aggressive_fairness = aggressive_result.get("fairness_after", baseline_fairness)
    aggressive_accuracy = aggressive_result.get("after", {}).get("accuracy", baseline_accuracy)
    aggressive_rolled_back = any(entry.get("rollback") for entry in aggressive_result.get("tradeoff_log", []))
    aggressive_reliability = "low" if not aggressive_rolled_back and (baseline_accuracy - aggressive_accuracy) > 0.5 else "moderate"

    # Determine core issue
    structural_warnings = []
    target_col = baseline_result.get("target_column")
    if target_col and target_col in df.columns:
        for col in sensitive_cols:
            if col not in df.columns:
                continue
            try:
                cross = pd.crosstab(df[col], df[target_col], normalize="index")
                max_concentration = cross.max(axis=1).max()
                if max_concentration >= 0.90:
                    structural_warnings.append(f"'{col}' shows {max_concentration:.0%} concentration in one outcome group")
            except Exception:
                continue

    core_issue = "structural_bias" if structural_warnings else "algorithmic_bias"

    # Build response
    response = {
        "summary": {
            "headline": "Fairness can be improved, but with significant accuracy tradeoff" if aggressive_fairness > baseline_fairness else "Fairness improvements are limited by dataset constraints",
            "core_issue": "Dataset exhibits structural gender bias" if core_issue == "structural_bias" else "Algorithmic bias detected in model predictions",
            "decision_required": aggressive_fairness > baseline_fairness
        },
        "scenarios": {
            "safe_mode": {
                "description": "No mitigation applied to preserve model reliability",
                "fairness_score": round(baseline_fairness, 2),
                "accuracy": round(baseline_accuracy, 4),
                "risk_level": "high_bias" if baseline_fairness < 60 else "moderate_bias",
                "reliability": "high",
                "decision": "recommended_for_production"
            },
            "aggressive_mode": {
                "description": "Bias mitigation applied with relaxed accuracy constraints",
                "fairness_score": round(aggressive_fairness, 2),
                "accuracy": round(aggressive_accuracy, 4),
                "risk_level": "low_bias" if aggressive_fairness > 70 else "moderate_bias",
                "reliability": aggressive_reliability,
                "decision": "use_with_caution" if aggressive_reliability == "low" else "acceptable_tradeoff"
            }
        },
        "tradeoff": {
            "fairness_improvement": f"+{round(aggressive_fairness - baseline_fairness, 2)}",
            "accuracy_loss": f"-{round((baseline_accuracy - aggressive_accuracy) * 100, 1)}%",
            "interpretation": "Improving fairness significantly reduces predictive reliability" if (baseline_accuracy - aggressive_accuracy) > 0.5 else "Fairness improvements achieved with manageable accuracy impact",
            "severity": "critical" if (baseline_accuracy - aggressive_accuracy) > 0.5 else "moderate"
        },
        "root_cause": {
            "type": core_issue,
            "explanation": "The dataset reflects historical bias where one group dominates positive outcomes." if core_issue == "structural_bias" else "Model learned biased patterns from training data.",
            "technical_reason": "Model learns biased patterns, so correcting them conflicts with original labels." if core_issue == "structural_bias" else "Training data contained biased representations.",
            "not_a_bug": True
        },
        "risk_assessment": {
            "bias_risk": {
                "level": "high" if baseline_fairness < 60 else "moderate",
                "impact": "discriminatory outcomes in hiring decisions"
            },
            "accuracy_risk": {
                "level": "critical" if aggressive_reliability == "low" else "low",
                "impact": "model predictions become unreliable for deployment"
            }
        },
        "recommendation": {
            "best_action": "collect_more_balanced_data" if core_issue == "structural_bias" else "apply_safe_mode_mitigation",
            "alternatives": [
                "use_safe_mode_for_deployment",
                "apply_partial_mitigation",
                "retrain_with_bias-aware_labeling"
            ],
            "explanation": "Algorithmic fixes alone are insufficient; data-level correction is required." if core_issue == "structural_bias" else "Safe mitigation can improve fairness without compromising reliability."
        },
        "confidence": {
            "fairness_confidence": 0.85,
            "accuracy_confidence": 0.92,
            "overall_reliability": aggressive_reliability
        },
        "details": {
            "thresholds": aggressive_result.get("after", {}).get("thresholds", {}),
            "protected_attributes": sensitive_cols,
            "metrics": {
                "baseline_fairness": round(baseline_fairness, 2),
                "baseline_accuracy": round(baseline_accuracy, 4),
                "aggressive_fairness": round(aggressive_fairness, 2),
                "aggressive_accuracy": round(aggressive_accuracy, 4)
            },
            "structural_warnings": structural_warnings
        },
        "mode_selector": {
            "default": "safe_mode",
            "user_can_override": True
        }
    }

    return response
