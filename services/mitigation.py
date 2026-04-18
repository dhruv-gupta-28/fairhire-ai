import copy
import logging
from typing import Dict, Any, List, Tuple, Optional

import numpy as np
import pandas as pd
from imblearn.over_sampling import SMOTE
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OrdinalEncoder
from fairness.metrics import FairnessMetrics
from fairness.scoring import FairnessScore

from ml.pipeline import MLPipeline

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

        cat_cols = X.select_dtypes(include=["object", "category"]).columns.tolist()
        X_encoded = X.copy()
        encoder = OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)

        if cat_cols:
            X_encoded[cat_cols] = encoder.fit_transform(X[cat_cols].astype(str))

        try:
            smote = SMOTE(random_state=self.random_state)
            X_res, y_res = smote.fit_resample(X_encoded, y)
            X_res = pd.DataFrame(X_res, columns=X.columns)

            if cat_cols:
                encoded_values = np.round(X_res[cat_cols].values).astype(int)
                max_categories = np.array([len(categories) - 1 for categories in encoder.categories_], dtype=int)
                encoded_values = np.clip(encoded_values, 0, max_categories)
                X_res[cat_cols] = encoder.inverse_transform(encoded_values)

            return X_res, pd.Series(y_res, name=y.name)
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
        target_rate: float = 0.75
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
            for threshold in np.linspace(0.0, 1.0, 21):
                predicted = (y_probas[group_mask] >= threshold).astype(int)
                rate = predicted.mean()
                diff = abs(rate - target_rate)
                if diff < best_diff:
                    best_diff = diff
                    best_threshold = threshold
            thresholds[str(group)] = float(round(best_threshold, 3))

        return thresholds

    def _train_model(self, X: pd.DataFrame, y: pd.Series, sample_weight: Optional[np.ndarray] = None) -> Tuple[Pipeline, float]:
        from sklearn.compose import ColumnTransformer
        from sklearn.impute import SimpleImputer
        from sklearn.preprocessing import OneHotEncoder, StandardScaler

        numeric_cols = X.select_dtypes(include=["number"]).columns.tolist()
        categorical_cols = X.select_dtypes(include=["object", "category"]).columns.tolist()

        transformers = []
        if numeric_cols:
            transformers.append(
                (
                    "num",
                    Pipeline(
                        steps=[
                            ("imputer", SimpleImputer(strategy="mean")),
                            ("scaler", StandardScaler()),
                        ]
                    ),
                    numeric_cols,
                )
            )
        if categorical_cols:
            transformers.append(
                (
                    "cat",
                    Pipeline(
                        steps=[
                            ("imputer", SimpleImputer(strategy="most_frequent")),
                            (
                                "onehot",
                                OneHotEncoder(
                                    handle_unknown="ignore", sparse_output=False
                                ),
                            ),
                        ]
                    ),
                    categorical_cols,
                )
            )

        preprocessor = ColumnTransformer(transformers=transformers)

        try:
            clf = Pipeline(
                steps=[
                    ("preprocessor", preprocessor),
                    (
                        "classifier",
                        LogisticRegression(
                            class_weight="balanced",
                            max_iter=3000,
                            random_state=self.random_state,
                        ),
                    ),
                ]
            )
            clf.fit(X, y, classifier__sample_weight=sample_weight)
        except Exception:
            clf = Pipeline(
                steps=[
                    ("preprocessor", preprocessor),
                    (
                        "classifier",
                        RandomForestClassifier(
                            class_weight="balanced", random_state=self.random_state
                        ),
                    ),
                ]
            )
            clf.fit(X, y)

        _, X_val, _, y_val = train_test_split(
            X, y, test_size=0.2, random_state=self.random_state
        )
        acc = float(accuracy_score(y_val, clf.predict(X_val)))
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

        if 'age' in X.columns:
            try:
                X['age_group'] = pd.qcut(
                    pd.to_numeric(X['age'], errors='coerce'),
                    q=5,
                    duplicates='drop'
                ).astype(str).fillna('Unknown')
                if 'age' in sensitive_cols:
                    sensitive_cols = ['age_group' if c == 'age' else c for c in sensitive_cols]
                if 'age_group' not in sensitive_cols:
                    sensitive_cols.append('age_group')
            except Exception as exc:
                logger.warning(f"Age bucketing skipped in mitigation: {exc}")

        try:
            X_clean = self.remove_correlation(X, sensitive_cols)
            output["mitigation_steps"].append("Correlation removal applied")
        except Exception as exc:
            X_clean = X.copy()
            logger.warning(f"Correlation removal skipped: {exc}")

        X_train, X_test, y_train, y_test = train_test_split(
            X_clean,
            y,
            test_size=0.2,
            random_state=self.random_state,
            stratify=y if len(pd.Series(y).unique()) > 1 else None
        )

        try:
            X_smote, y_smote = self.apply_smote(X_train, y_train, sensitive_cols)
            if len(y_smote) > len(y_train):
                output["mitigation_steps"].append("SMOTE oversampling applied")
            else:
                X_smote, y_smote = X_train, y_train
        except Exception as exc:
            X_smote, y_smote = X_train, y_train
            logger.warning(f"SMOTE step failed: {exc}")

        sample_weights = None
        try:
            reweigh_df = X_smote.copy()
            reweigh_df[target_col] = y_smote.values
            sample_weights = self.reweigh(reweigh_df, target_col, sensitive_cols)
            output["mitigation_steps"].append("Reweighing applied")
        except Exception as exc:
            logger.warning(f"Reweighing failed: {exc}")

        try:
            mitigation_model, _ = self._train_model(X_smote, y_smote, sample_weight=sample_weights)
        except Exception as exc:
            output["tradeoff_log"].append({"error": f"Mitigation training failed: {exc}"})
            return output

        raw_mitigation_acc = float(accuracy_score(y_test, mitigation_model.predict(X_test)))

        baseline_accuracy = baseline_metrics.get("accuracy", 0.0)
        output["accuracy_before"] = baseline_accuracy
        output["fairness_before"] = baseline_metrics.get("fairness_score", 0.0)
        output["bias_level_before"] = baseline_metrics.get("bias_level", "Unknown")

        y_pred_test = mitigation_model.predict(X_test)
        if hasattr(mitigation_model.named_steps["classifier"], "predict_proba"):
            y_proba_test = mitigation_model.predict_proba(X_test)[:, 1]
        else:
            y_proba_test = y_pred_test

        preferred_order = ["gender", "sex", "race", "ethnicity", "age_group", "age"]
        group_col = next(
            (col for col in preferred_order if col in sensitive_cols and col in X_test.columns),
            None
        )
        thresholds = {}
        y_pred_final = y_pred_test
        if group_col is not None and group_col in X_test.columns:
            thresholds = self.optimize_thresholds(
                y_test,
                y_proba_test,
                X_test[group_col].astype(str)
            )
            output["mitigation_steps"].append("Per-group threshold optimization applied")
            y_pred_final = np.zeros_like(y_pred_test)
            for group, threshold in thresholds.items():
                mask = X_test[group_col].astype(str) == str(group)
                y_pred_final[mask] = (y_proba_test[mask] >= threshold).astype(int)
        else:
            thresholds = {}

        after_fairness_score = baseline_metrics.get("fairness_score", 0.0)
        after_bias_level = baseline_metrics.get("bias_level", "Unknown")
        after_risk_level = baseline_metrics.get("risk_level", baseline_metrics.get("bias_level", "Unknown"))

        try:
            sensitive_feature_values_test = {
                col: X_test[col].astype(str).fillna("MISSING").tolist()
                for col in sensitive_cols if col and col in X_test.columns
            }
            after_metrics = FairnessMetrics(
                y_true=y_test,
                y_pred=y_pred_final,
                y_pred_proba=y_proba_test,
                sensitive_features_dict=sensitive_feature_values_test
            )
            after_scores = FairnessScore(
                after_metrics,
                protected_attributes=list(sensitive_feature_values_test.keys())
            )
            after_fairness_score, after_bias_level = after_scores.compute_overall_score()
            after_risk_level = after_bias_level
            output["after_analysis"] = {
                "fairness_score": after_fairness_score,
                "bias_level": after_bias_level,
                "metrics": {
                    "accuracy": float(accuracy_score(y_test, y_pred_final)),
                    "thresholds": thresholds
                },
            }
        except Exception as exc:
            logger.warning(f"Post-mitigation fairness evaluation failed: {exc}")

        after_accuracy = float(round(accuracy_score(y_test, y_pred_final), 4))
        accuracy_drop = float(round(baseline_accuracy - after_accuracy, 4))

        output["tradeoff_log"].append({
            "baseline_accuracy": baseline_accuracy,
            "mitigated_accuracy": raw_mitigation_acc,
            "thresholded_accuracy": after_accuracy,
            "accuracy_drop": accuracy_drop
        })

        if accuracy_drop > max_accuracy_drop:
            output["tradeoff_log"].append({
                "rollback": True,
                "reason": f"Accuracy drop {accuracy_drop:.4f} exceeds threshold {max_accuracy_drop}."
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
            output["bias_level_after"] = output["after"]["bias_level"]
            output["risk_transition"] = output["after"]["risk_level"] + " → " + output["after"]["risk_level"]
            output["improvement"] = "Mitigation rolled back due to excessive accuracy loss."
            return output

        output["after"] = {
            "accuracy": after_accuracy,
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
