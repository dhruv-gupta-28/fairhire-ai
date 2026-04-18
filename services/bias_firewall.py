import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline

logger = logging.getLogger(__name__)

RISK_LEVELS = ["Low", "Moderate", "High"]


class BiasFirewall:
    def __init__(self, gap_threshold_high: float = 0.15, gap_threshold_moderate: float = 0.08):
        self.gap_threshold_high = gap_threshold_high
        self.gap_threshold_moderate = gap_threshold_moderate

    def _build_input_frame(self, candidate_data: Any) -> pd.DataFrame:
        if isinstance(candidate_data, pd.Series):
            return candidate_data.to_frame().T
        if isinstance(candidate_data, dict):
            return pd.DataFrame([candidate_data])
        if isinstance(candidate_data, pd.DataFrame) and len(candidate_data) == 1:
            return candidate_data.copy()
        if isinstance(candidate_data, pd.DataFrame) and len(candidate_data) > 1:
            return candidate_data.iloc[[0]].copy()
        raise ValueError("candidate_data must be a dict, pandas Series, or single-row DataFrame.")

    def _predict(self, model_pipeline: Pipeline, X: pd.DataFrame) -> Tuple[Any, float]:
        if hasattr(model_pipeline, "predict_proba"):
            probabilities = model_pipeline.predict_proba(X)
            if probabilities.ndim == 1:
                confidence = float(np.max(probabilities))
            else:
                confidence = float(np.max(probabilities, axis=1)[0])
        else:
            try:
                confidence = float(np.max(model_pipeline.decision_function(X)))
            except Exception:
                confidence = 1.0

        prediction = model_pipeline.predict(X)[0]
        return prediction, confidence

    def _extract_group_rates(self, metadata: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
        rates = {}
        if not isinstance(metadata, dict):
            return rates

        if "selection_rates" in metadata and isinstance(metadata["selection_rates"], dict):
            rates.update({k: {str(g): float(v) for g, v in groups.items()} for k, groups in metadata["selection_rates"].items() if isinstance(groups, dict)})

        if "group_rates" in metadata and isinstance(metadata["group_rates"], dict):
            rates.update({k: {str(g): float(v) for g, v in groups.items()} for k, groups in metadata["group_rates"].items() if isinstance(groups, dict)})

        if "bias_data" in metadata and isinstance(metadata["bias_data"], dict):
            bias_data = metadata["bias_data"]
            for key in ["gender_bias", "race_bias", "age_bias", "education_bias"]:
                if key in bias_data and isinstance(bias_data[key], dict):
                    rates[key.replace("_bias", "")] = {str(g): float(v) for g, v in bias_data[key].items()}

        return rates

    def _assess_attribute_risk(self, attr: str, group_value: Any, group_rates: Dict[str, float]) -> Optional[Dict[str, Any]]:
        if group_value is None or not group_rates:
            return None

        group_key = str(group_value).strip()
        if group_key not in group_rates:
            return None

        values = list(group_rates.values())
        if not values:
            return None

        max_rate = max(values)
        min_rate = min(values)
        candidate_rate = float(group_rates[group_key])
        gap = float(round(max_rate - min_rate, 4))

        risk_level = "Low"
        if gap >= self.gap_threshold_high and candidate_rate <= min_rate:
            risk_level = "High"
        elif gap >= self.gap_threshold_moderate and candidate_rate <= min_rate:
            risk_level = "Moderate"
        elif gap >= self.gap_threshold_high and candidate_rate < max_rate:
            risk_level = "Moderate"

        if risk_level == "Low":
            return None

        weaker_group = [k for k, v in group_rates.items() if float(v) == min_rate]
        weaker_group = weaker_group[0] if weaker_group else "the lower-rate group"

        reason = (
            f"Candidate belongs to '{group_key}', which has a lower selection rate ({candidate_rate:.2f}) than the best-performing group ({max_rate:.2f})."
            if risk_level == "High"
            else f"Candidate belongs to '{group_key}', which is below the top group selection rate and indicates fairness risk."
        )

        return {
            "attribute": attr,
            "reason": reason,
            "risk_level": risk_level,
            "group_rate": candidate_rate,
            "rate_gap": gap,
            "weaker_group": weaker_group
        }

    def evaluate(self, candidate_data: Any, model_pipeline: Optional[Pipeline], metadata: Dict[str, Any]) -> Dict[str, Any]:
        input_df = self._build_input_frame(candidate_data)
        if input_df.empty:
            raise ValueError("Candidate data is empty.")

        if model_pipeline is not None:
            prediction, confidence = self._predict(model_pipeline, input_df)
        else:
            prediction = candidate_data.get("prediction") if isinstance(candidate_data, dict) else None
            confidence = 0.0

        group_rates = self._extract_group_rates(metadata)
        candidate_row = input_df.iloc[0].to_dict()

        flags: List[Dict[str, Any]] = []
        highest_risk = "Low"

        for attr, rates in group_rates.items():
            if attr in candidate_row and pd.notna(candidate_row[attr]):
                flag = self._assess_attribute_risk(attr, candidate_row[attr], rates)
                if flag is not None:
                    flags.append({
                        "attribute": attr,
                        "reason": flag["reason"],
                        "risk_level": flag["risk_level"]
                    })
                    if RISK_LEVELS.index(flag["risk_level"]) > RISK_LEVELS.index(highest_risk):
                        highest_risk = flag["risk_level"]

        if not flags and isinstance(metadata, dict):
            bias_features = metadata.get("bias_by_feature") or metadata.get("fairness_metrics")
            if isinstance(bias_features, list):
                for item in bias_features:
                    attr = item.get("attribute")
                    severity = item.get("severity")
                    if attr and severity in ["CRITICAL", "WARNING"] and attr in candidate_row:
                        flags.append({
                            "attribute": attr,
                            "reason": f"Historical bias detected on {attr}; candidate belongs to a sensitive group.",
                            "risk_level": "Moderate" if severity == "WARNING" else "High"
                        })
                        highest_risk = "High" if severity == "CRITICAL" else "Moderate"

        bias_flag = bool(flags)
        overall_risk = highest_risk if bias_flag else "Low"
        recommendation = (
            "Review this prediction before taking action and consider fairness interventions for the flagged groups."
            if bias_flag
            else "Proceed with the prediction, but continue monitoring fairness in real time."
        )

        human_summary = (
            f"The model predicted {prediction} with confidence {confidence:.2f}. "
            f"Bias risk is {overall_risk}. "
            f"{len(flags)} attribute(s) raised concerns."
        )
        if bias_flag:
            human_summary += " Review the flagged items and validate the decision with fairness checks."

        return {
            "prediction": prediction,
            "confidence": float(round(confidence, 4)),
            "bias_flag": bias_flag,
            "flags": flags,
            "overall_risk": overall_risk,
            "recommendation": recommendation,
            "human_summary": human_summary
        }


def firewall_check(candidate: Any, bias_data: Dict[str, Any], model_pipeline: Optional[Pipeline] = None) -> Dict[str, Any]:
    firewall = BiasFirewall()
    result = firewall.evaluate(candidate, model_pipeline, bias_data)
    verdict = "BIASED" if result["bias_flag"] else "FAIR"
    details = {flag["attribute"]: {"reason": flag["reason"], "risk_level": flag["risk_level"]} for flag in result["flags"]}
    reason = (
        f"Potential discrimination detected in: {', '.join([flag['attribute'] for flag in result['flags']])}"
        if result["bias_flag"] else
        "No significant bias detected across evaluated attributes"
    )
    suggestion = result["recommendation"]

    return {
        "verdict": verdict,
        "risk_score": float(len(result["flags"]) / max(len(result.get("flags", [])), 1)),
        "reason": reason,
        "details": details,
        "suggestion": suggestion
    }
