import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import shap
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

logger = logging.getLogger(__name__)

SENSITIVE_KEYWORDS = ["gender", "sex", "race", "ethnicity", "age", "dob", "veteran", "disability"]


class DecisionExplainer:
    def __init__(self, sensitivity_threshold: float = 0.05):
        self.sensitivity_threshold = sensitivity_threshold

    def _build_input_frame(self, input_row: Any) -> pd.DataFrame:
        if isinstance(input_row, pd.Series):
            return input_row.to_frame().T
        if isinstance(input_row, dict):
            return pd.DataFrame([input_row])
        if isinstance(input_row, pd.DataFrame) and len(input_row) == 1:
            return input_row.copy()
        if isinstance(input_row, pd.DataFrame) and len(input_row) > 1:
            return input_row.iloc[[0]].copy()
        raise ValueError("Input row must be a dict, pandas Series, or single-row DataFrame.")

    def _detect_sensitive_features(self, feature_names: List[str]) -> List[str]:
        return [name for name in feature_names if any(keyword in str(name).lower() for keyword in SENSITIVE_KEYWORDS)]

    def explain_instance(self, model_pipeline: Pipeline, input_row: Any, feature_names: Optional[List[str]] = None) -> Dict[str, Any]:
        if not hasattr(model_pipeline, "predict"):
            raise ValueError("model_pipeline must be a scikit-learn compatible Pipeline with predict/predict_proba.")

        input_df = self._build_input_frame(input_row)
        if input_df.empty:
            raise ValueError("Input row is empty.")

        try:
            classifier = model_pipeline
            preprocessor = None
            if hasattr(model_pipeline, "named_steps"):
                if "classifier" in model_pipeline.named_steps:
                    classifier = model_pipeline.named_steps["classifier"]
                if "preprocessor" in model_pipeline.named_steps:
                    preprocessor = model_pipeline.named_steps["preprocessor"]
                elif len(model_pipeline.steps) > 1:
                    preprocessor = Pipeline(model_pipeline.steps[:-1])
                    classifier = model_pipeline.steps[-1][1]

            if preprocessor is not None:
                X_explain = preprocessor.transform(input_df)
            else:
                X_explain = input_df

            if hasattr(model_pipeline, "predict_proba"):
                confidence = float(np.max(model_pipeline.predict_proba(input_df)[:, 1]))
            else:
                confidence = 1.0

            prediction = int(model_pipeline.predict(input_df)[0])

            explainer = shap.Explainer(classifier, X_explain)
            shap_result = explainer(X_explain)
            shap_vals = np.array(shap_result.values).reshape(-1)

            if feature_names is None:
                feature_names = input_df.columns.tolist()

            contributions = {
                str(name): float(round(val, 4))
                for name, val in zip(feature_names, shap_vals)
            }

            sorted_contributions = sorted(contributions.items(), key=lambda item: item[1], reverse=True)
            top_positive = [name for name, _ in sorted_contributions if _ > 0][:5]
            top_negative = [name for name, _ in sorted_contributions if _ < 0][-5:]

            sensitive_features = self._detect_sensitive_features(feature_names)
            sensitive_alert = False
            sensitive_details = []
            for name, value in contributions.items():
                if name in sensitive_features and abs(value) >= self.sensitivity_threshold:
                    sensitive_alert = True
                    sensitive_details.append({
                        "feature": name,
                        "contribution": value,
                        "message": f"Sensitive attribute '{name}' influenced the decision."
                    })

            summary_lines: List[str] = [
                f"Predicted class: {prediction}.",
                f"Model confidence: {confidence:.2f}."
            ]
            if sensitive_alert:
                summary_lines.append(
                    "⚠️ Sensitive attribute influence detected in the decision explanation."
                )
            else:
                summary_lines.append(
                    "No sensitive attribute had a dominant contribution in this prediction."
                )

            return {
                "prediction": prediction,
                "confidence": confidence,
                "feature_contributions": contributions,
                "top_positive_drivers": top_positive,
                "top_negative_drivers": top_negative,
                "sensitive_alert": sensitive_alert,
                "sensitive_details": sensitive_details,
                "summary": " ".join(summary_lines)
            }
        except Exception as exc:
            logger.warning(f"Decision explanation failed: {exc}")
            return {
                "error": "Failed to generate explanation.",
                "details": str(exc)
            }
