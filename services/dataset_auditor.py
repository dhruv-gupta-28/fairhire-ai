import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional

SENSITIVE_KEYWORDS = ["gender", "sex", "race", "ethnicity", "age", "dob", "veteran", "disability"]
TARGET_KEYWORDS = ["target", "label", "outcome", "decision", "hired", "approved", "selected", "offer"]


class DatasetAuditor:
    def __init__(self, min_target_balance: float = 0.05):
        self.min_target_balance = min_target_balance

    def _detect_target(self, df: pd.DataFrame) -> Optional[str]:
        for col in df.columns:
            if str(col).strip().lower() in TARGET_KEYWORDS:
                return col

        for col in df.columns:
            values = df[col].dropna().unique()
            if 1 < len(values) <= 10 and df[col].dtype in ["int64", "int32", "float64", "object", "category"]:
                if all(str(x).strip().lower() in ["0", "1", "yes", "no", "true", "false"] for x in values):
                    return col
        return None

    def _detect_sensitive_columns(self, df: pd.DataFrame) -> List[str]:
        found = []
        for col in df.columns:
            name = str(col).lower()
            if any(keyword in name for keyword in SENSITIVE_KEYWORDS):
                found.append(col)
        return found

    def _proxy_variables(self, df: pd.DataFrame, sensitive_cols: List[str]) -> List[Dict[str, Any]]:
        proxies = []
        numeric = df.select_dtypes(include=["number"]).copy()
        for sensitive in sensitive_cols:
            if sensitive not in df.columns or sensitive not in numeric.columns:
                continue
            for col in numeric.columns:
                if col == sensitive:
                    continue
                try:
                    corr = abs(numeric[sensitive].corr(numeric[col]))
                    if pd.notna(corr) and corr >= 0.45:
                        proxies.append({
                            "feature": col,
                            "sensitive_attribute": sensitive,
                            "correlation": float(round(corr, 3)),
                            "severity": "WARNING" if corr < 0.7 else "CRITICAL"
                        })
                except Exception:
                    continue
        return proxies

    def _outliers(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        outlier_results = []
        numeric = df.select_dtypes(include=["number"]).copy()
        for col in numeric.columns:
            if numeric[col].dropna().empty:
                continue
            series = numeric[col].dropna()
            q1 = series.quantile(0.25)
            q3 = series.quantile(0.75)
            iqr = q3 - q1
            if iqr <= 0:
                continue
            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr
            count = int(((series < lower) | (series > upper)).sum())
            if count > 0:
                outlier_results.append({
                    "column": col,
                    "outlier_count": count,
                    "outlier_ratio": float(round(count / len(series), 4)),
                    "severity": "WARNING" if count / len(series) < 0.05 else "CRITICAL"
                })
        return outlier_results

    def audit(self, file_path: str) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "summary": [],
            "warnings": [],
            "audit_details": {},
            "audit_score": 100,
            "severity": "INFO"
        }

        try:
            df = pd.read_csv(file_path)
        except Exception as exc:
            return {
                "error": f"Unable to read dataset: {exc}",
                "failed": True
            }

        if df.empty:
            return {
                "error": "Dataset is empty.",
                "failed": True
            }

        missing = df.isnull().mean().round(4).to_dict()
        missing_summary = [{"column": col, "missing_rate": float(rate)} for col, rate in missing.items() if rate > 0]

        sensitive_cols = self._detect_sensitive_columns(df)
        target_col = self._detect_target(df)

        class_imbalance = {}
        if target_col and target_col in df.columns:
            counts = df[target_col].value_counts(normalize=True, dropna=True).to_dict()
            class_imbalance = {str(k): float(round(v, 4)) for k, v in counts.items()}
            if len(counts) == 2:
                min_rate = min(counts.values())
                if min_rate < self.min_target_balance:
                    result["warnings"].append({
                        "type": "CLASS_IMBALANCE",
                        "message": f"Target '{target_col}' has strong imbalance: smallest class is {min_rate:.2%}.",
                        "severity": "CRITICAL"
                    })

        if not sensitive_cols:
            result["warnings"].append({
                "type": "SENSITIVE_ATTRIBUTE_MISSING",
                "message": "No obvious sensitive attributes were detected by keyword scanning.",
                "severity": "INFO"
            })

        proxy_findings = self._proxy_variables(df, sensitive_cols)
        outliers = self._outliers(df)

        if missing_summary:
            result["audit_details"]["missing_values"] = missing_summary
            result["warnings"].append({
                "type": "MISSING_VALUES",
                "message": "Dataset contains missing values across features.",
                "severity": "WARNING"
            })

        if sensitive_cols:
            result["audit_details"]["sensitive_attributes"] = sensitive_cols

        if target_col:
            result["audit_details"]["target_column"] = target_col
            result["audit_details"]["class_distribution"] = class_imbalance
        else:
            result["warnings"].append({
                "type": "TARGET_DETECTION",
                "message": "No strongly identifiable target column was detected.",
                "severity": "WARNING"
            })

        if proxy_findings:
            result["audit_details"]["proxy_variables"] = proxy_findings
            result["warnings"].append({
                "type": "PROXY_DETECTION",
                "message": "Detected features with high correlation to sensitive attributes.",
                "severity": "CRITICAL" if any(item["severity"] == "CRITICAL" for item in proxy_findings) else "WARNING"
            })

        if outliers:
            result["audit_details"]["outliers"] = outliers
            result["warnings"].append({
                "type": "OUTLIERS",
                "message": "Numeric feature outliers were detected.",
                "severity": "WARNING"
            })

        if result["warnings"]:
            severities = {item["severity"] for item in result["warnings"]}
            if "CRITICAL" in severities:
                result["severity"] = "CRITICAL"
                result["audit_score"] = 45
            elif "WARNING" in severities:
                result["severity"] = "WARNING"
                result["audit_score"] = 65
            else:
                result["severity"] = "INFO"
                result["audit_score"] = 85
        else:
            result["severity"] = "INFO"
            result["audit_score"] = 95

        result["summary"] = [
            f"Detected {len(sensitive_cols)} sensitive attribute(s)." if sensitive_cols else "No sensitive attributes detected.",
            f"Target column identified as '{target_col}'." if target_col else "Target column not clearly identified.",
            f"Proxy variable analysis found {len(proxy_findings)} potential proxies.",
            f"Outlier analysis flagged {len(outliers)} numeric feature issues."
        ]

        result["audit_details"]["dataset_shape"] = {"rows": int(df.shape[0]), "columns": int(df.shape[1])}
        result["audit_details"]["detected_sensitive_attributes"] = sensitive_cols
        return result
