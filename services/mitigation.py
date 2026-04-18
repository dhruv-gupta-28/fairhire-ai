import copy
import logging
from typing import Dict, Any, List, Tuple, Optional

import numpy as np
import pandas as pd
from imblearn.over_sampling import SMOTE
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from sklearn.pipeline import Pipeline

logger = logging.getLogger(__name__)


class BiasMitigationEngine:
    def __init__(self, min_accuracy_drop: float = 0.05, random_state: int = 42):
        self.min_accuracy_drop = min_accuracy_drop
        self.random_state = random_state

    def reweigh(self, df: pd.DataFrame, target_col: str, sensitive_cols: List[str]) -> np.ndarray:
        y = df[target_col].astype(str)
        baseline = y.value_counts(normalize=True).to_dict()
        sample_weights = np.ones(len(df), dtype=float)

        for sensitive in sensitive_cols:
            if sensitive not in df.columns:
                continue
            group_counts = df.groupby([sensitive, target_col]).size().unstack(fill_value=0)
            for idx, row in group_counts.iterrows():
                group_total = row.sum()
                for label, count in row.items():
                    if count == 0:
                        continue
                    ratio = count / group_total
                    weight = 1.0 / ratio if ratio > 0 else 1.0
                    sample_weights[(df[sensitive] == idx) & (df[target_col].astype(str) == str(label))] = weight

        if sample_weights.mean() <= 0:
            sample_weights = np.ones(len(df), dtype=float)
        return sample_weights

    def apply_smote(self, X: pd.DataFrame, y: pd.Series, sensitive_cols: List[str]) -> Tuple[pd.DataFrame, pd.Series]:
        if X.empty or y.empty:
            return X, y

        if len(y.unique()) < 2:
            return X, y

        try:
            smote = SMOTE(random_state=self.random_state)
            X_res, y_res = smote.fit_resample(X, y)
            return pd.DataFrame(X_res, columns=X.columns), pd.Series(y_res, name=y.name)
        except Exception as exc:
            logger.warning(f"SMOTE failed: {exc}")
            return X, y

    def remove_correlation(self, X: pd.DataFrame, sensitive_cols: List[str]) -> pd.DataFrame:
        X_clean = X.copy()
        numeric = X_clean.select_dtypes(include=["number"]).copy()
        for sensitive in sensitive_cols:
            if sensitive not in X_clean.columns or sensitive not in numeric.columns:
                continue
            sensitive_values = numeric[sensitive].astype(float).fillna(0).values.reshape(-1, 1)
            for col in numeric.columns:
                if col == sensitive:
                    continue
                feature_values = numeric[col].astype(float).fillna(0).values
                coef = np.linalg.lstsq(sensitive_values, feature_values, rcond=None)[0]
                projection = sensitive_values.dot(coef)
                numeric[col] = feature_values - projection.ravel()

        X_clean[numeric.columns] = numeric
        return X_clean

    def optimize_thresholds(
        self,
        y_true: pd.Series,
        y_probas: np.ndarray,
        group_labels: pd.Series,
        target_rate: float = 0.5
    ) -> Dict[str, float]:
        thresholds: Dict[str, float] = {}
        unique_groups = group_labels.dropna().unique()

        for group in unique_groups:
            group_mask = group_labels == group
            if group_mask.sum() < 10:
                thresholds[str(group)] = 0.5
                continue

            best_threshold = 0.5
            best_diff = float("inf")
            for threshold in np.linspace(0.1, 0.9, 17):
                predicted = (y_probas[group_mask] >= threshold).astype(int)
                rate = predicted.mean()
                diff = abs(rate - target_rate)
                if diff < best_diff:
                    best_diff = diff
                    best_threshold = threshold
            thresholds[str(group)] = float(round(best_threshold, 3))

        return thresholds

    def _train_model(self, X: pd.DataFrame, y: pd.Series, sample_weight: Optional[np.ndarray] = None) -> Tuple[Pipeline, float]:
        model = LogisticRegression(class_weight="balanced", max_iter=3000, random_state=self.random_state)
        clf = Pipeline(steps=[("classifier", model)])
        try:
            clf.fit(X, y, classifier__sample_weight=sample_weight)
        except Exception:
            model = RandomForestClassifier(class_weight="balanced", random_state=self.random_state)
            clf = Pipeline(steps=[("classifier", model)])
            clf.fit(X, y)

        preds = clf.predict(X)
        acc = float(accuracy_score(y, preds))
        return clf, acc

    def mitigate_and_retrain(
        self,
        df: pd.DataFrame,
        target_col: str,
        sensitive_cols: List[str],
        baseline_metrics: Dict[str, Any],
        baseline_pipeline: Optional[Pipeline] = None,
        max_accuracy_drop: float = 0.05
    ) -> Dict[str, Any]:
        output: Dict[str, Any] = {
            "before": {
                "accuracy": baseline_metrics.get("accuracy", 0.0),
                "fairness_score": baseline_metrics.get("fairness_score", 0.0),
                "bias_level": baseline_metrics.get("bias_level", "Unknown"),
                "risk_level": baseline_metrics.get("risk_level", baseline_metrics.get("bias_level", "Unknown"))
            },
            "after": {},
            "improvement": "No mitigation applied.",
            "risk_transition": "No change",
            "tradeoff_log": [],
            "mitigation_steps": []
        }

        X = df.drop(columns=[target_col], errors="ignore")
        y = df[target_col].astype(int)

        try:
            X_clean = self.remove_correlation(X, sensitive_cols)
            output["mitigation_steps"].append("Correlation removal applied")
        except Exception as exc:
            X_clean = X.copy()
            logger.warning(f"Correlation removal skipped: {exc}")

        try:
            X_smote, y_smote = self.apply_smote(X_clean, y, sensitive_cols)
            if len(y_smote) > len(y):
                output["mitigation_steps"].append("SMOTE oversampling applied")
            else:
                X_smote, y_smote = X_clean, y
        except Exception as exc:
            X_smote, y_smote = X_clean, y
            logger.warning(f"SMOTE step failed: {exc}")

        sample_weights = self.reweigh(df, target_col, sensitive_cols)
        output["mitigation_steps"].append("Reweighing applied")

        try:
            mitigation_model, mitigation_acc = self._train_model(X_smote, y_smote, sample_weight=sample_weights)
        except Exception as exc:
            output["tradeoff_log"].append({"error": f"Mitigation training failed: {exc}"})
            return output

        baseline_accuracy = baseline_metrics.get("accuracy", 0.0)
        acc_drop = baseline_accuracy - mitigation_acc
        output["accuracy_before"] = baseline_accuracy
        output["accuracy_after"] = float(round(mitigation_acc, 4))
        output["fairness_before"] = baseline_metrics.get("fairness_score", 0.0)
        output["fairness_after"] = baseline_metrics.get("fairness_score", 0.0)
        output["bias_level_before"] = baseline_metrics.get("bias_level", "Unknown")

        output["tradeoff_log"].append({
            "baseline_accuracy": baseline_accuracy,
            "mitigated_accuracy": mitigation_acc,
            "accuracy_drop": float(round(acc_drop, 4))
        })

        if acc_drop > max_accuracy_drop:
            output["tradeoff_log"].append({
                "rollback": True,
                "reason": f"Accuracy drop {acc_drop:.4f} exceeds threshold {max_accuracy_drop}."
            })
            output["after"] = {
                "accuracy": float(round(baseline_accuracy, 4)),
                "fairness_score": baseline_metrics.get("fairness_score", 0.0),
                "bias_level": baseline_metrics.get("bias_level", "Unknown"),
                "risk_level": baseline_metrics.get("risk_level", baseline_metrics.get("bias_level", "Unknown")),
                "details": {
                    "mitigation_methods": output["mitigation_steps"],
                    "rolled_back": True
                }
            }
            output["fairness_after"] = output["after"]["fairness_score"]
            output["improvement"] = "Mitigation rolled back due to excessive accuracy loss."
            output["risk_transition"] = output["after"]["risk_level"] + " → " + output["after"]["risk_level"]
            return output

        y_proba = mitigation_model.predict_proba(X_smote)[:, 1] if hasattr(mitigation_model.named_steps["classifier"], "predict_proba") else mitigation_model.predict(X_smote)
        group_col = sensitive_cols[0] if sensitive_cols else None
        thresholds = {}
        if group_col is not None and group_col in df.columns:
            thresholds = self.optimize_thresholds(y_smote, y_proba, df[group_col].astype(str))
            output["mitigation_steps"].append("Per-group threshold optimization applied")

        after_fairness_score = baseline_metrics.get("fairness_score", 0.0)
        after_bias_level = baseline_metrics.get("bias_level", "Unknown")
        after_risk_level = baseline_metrics.get("risk_level", baseline_metrics.get("bias_level", "Unknown"))

        try:
            mitigated_df = X_smote.copy()
            mitigated_df[target_col] = y_smote
            after_analysis = MLPipeline(random_state=self.random_state).train(mitigated_df)
            if not after_analysis.get("failed"):
                after_fairness_score = after_analysis.get("fairness_score", after_fairness_score)
                after_bias_level = after_analysis.get("bias_level", after_bias_level)
                after_risk_level = after_analysis.get("bias_level", after_risk_level)
                output["after_analysis"] = {
                    "fairness_score": after_fairness_score,
                    "bias_level": after_bias_level,
                    "metrics": after_analysis.get("metrics", {}),
                }
        except Exception as exc:
            logger.warning(f"Post-mitigation fairness evaluation failed: {exc}")

        output["after"] = {
            "accuracy": float(round(mitigation_acc, 4)),
            "fairness_score": float(round(after_fairness_score, 4)),
            "bias_level": after_bias_level,
            "risk_level": after_risk_level,
            "thresholds": thresholds,
            "details": {
                "mitigation_methods": output["mitigation_steps"]
            }
        }
        output["fairness_after"] = float(round(after_fairness_score, 4))
        output["bias_level_after"] = after_bias_level
        output["risk_transition"] = f"{output['bias_level_before']} → {after_risk_level}"
        output["improvement"] = f"Mitigation completed with {len(output['mitigation_steps'])} step(s)."
        return output
