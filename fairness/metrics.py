"""
FairnessMetrics: Compute advanced multi-metric fairness evaluation.
"""

import numpy as np
from typing import Dict, List, Optional


class FairnessMetrics:

    def __init__(self, y_true, y_pred, y_pred_proba, sensitive_features_dict):
        n = len(y_true)

        if len(y_pred) != n or len(y_pred_proba) != n:
            raise ValueError("Length mismatch in predictions")

        for k, v in sensitive_features_dict.items():
            if len(v) != n:
                raise ValueError(f"{k} length mismatch")

        self.y_true = np.array(y_true, dtype=int)
        self.y_pred = np.array(y_pred, dtype=int)
        self.y_pred_proba = np.array(y_pred_proba, dtype=float)
        self.sensitive_features_dict = {
            k: np.array(v) for k, v in sensitive_features_dict.items()
        }

    # ---------------- UTIL ----------------
    def _safe_groups(self, feature):
        return np.unique(feature)

    def _safe_mean(self, arr):
        return float(arr.mean()) if len(arr) > 0 else 0.0

    # ---------------- DEMOGRAPHIC PARITY ----------------
    def demographic_parity_difference(self, attr):
        feature = self.sensitive_features_dict.get(attr)

        if feature is None:
            return {"difference": 0.0, "by_group": {}}

        rates = {}
        for g in self._safe_groups(feature):
            mask = feature == g
            if mask.sum() > 0:
                rates[str(g)] = self._safe_mean(self.y_pred[mask])

        if len(rates) < 2:
            return {"difference": 0.0, "by_group": rates}

        gap = max(rates.values()) - min(rates.values())

        return {
            "difference": round(float(gap), 4),
            "by_group": rates
        }

    # ---------------- EQUALIZED ODDS ----------------
    def equalized_odds_difference(self, attr):
        feature = self.sensitive_features_dict.get(attr)

        if feature is None:
            return {"tpr_gap": 0.0, "fpr_gap": 0.0}

        tprs, fprs = [], []

        for g in self._safe_groups(feature):
            mask = feature == g
            yt = self.y_true[mask]
            yp = self.y_pred[mask]

            tp = ((yp == 1) & (yt == 1)).sum()
            fn = ((yp == 0) & (yt == 1)).sum()
            fp = ((yp == 1) & (yt == 0)).sum()
            tn = ((yp == 0) & (yt == 0)).sum()

            if (tp + fn) > 0:
                tprs.append(tp / (tp + fn))
            if (fp + tn) > 0:
                fprs.append(fp / (fp + tn))

        tpr_gap = max(tprs) - min(tprs) if len(tprs) > 1 else 0.0
        fpr_gap = max(fprs) - min(fprs) if len(fprs) > 1 else 0.0

        return {
            "tpr_gap": round(float(tpr_gap), 4),
            "fpr_gap": round(float(fpr_gap), 4)
        }

    # ---------------- DISPARATE IMPACT ----------------
    def disparate_impact_ratio(self, attr):
        dp = self.demographic_parity_difference(attr)
        vals = list(dp["by_group"].values())

        if len(vals) < 2:
            return {"ratio": 1.0}

        min_v, max_v = min(vals), max(vals)

        if max_v == 0:
            return {"ratio": 1.0}

        ratio = min_v / max_v

        return {"ratio": round(float(ratio), 4)}

    # ---------------- CALIBRATION ----------------
    def calibration_gap(self, attr):
        feature = self.sensitive_features_dict.get(attr)

        if feature is None:
            return {"gap": 0.0}

        values = []

        for g in self._safe_groups(feature):
            mask = feature == g
            yt = self.y_true[mask]
            yp = self.y_pred_proba[mask]

            if len(yt) > 0 and yt.mean() > 0:
                values.append(yp.mean() / yt.mean())

        if len(values) < 2:
            return {"gap": 0.0}

        gap = max(values) - min(values)

        return {"gap": round(float(gap), 4)}

    # ---------------- SUMMARY ----------------
    def all_metrics(self, attrs: Optional[List[str]] = None):
        if attrs is None:
            attrs = list(self.sensitive_features_dict.keys())

        results = {}

        for attr in attrs:
            results[attr] = {
                "demographic_parity": self.demographic_parity_difference(attr),
                "equalized_odds": self.equalized_odds_difference(attr),
                "disparate_impact": self.disparate_impact_ratio(attr),
                "calibration": self.calibration_gap(attr)
            }

        return results