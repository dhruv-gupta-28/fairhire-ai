"""
ML Pipeline for FairHire — Production SHAP AI Engine V3
"""
import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, OneHotEncoder, LabelEncoder
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
import logging
import shap
from .metrics import FairnessMetrics
from fairness.scoring import FairnessScore

logger = logging.getLogger(__name__)

class MLPipeline:
    def __init__(self, random_state=42):
        self.random_state = random_state

    def detect_target(self, df: pd.DataFrame):
        keywords = ["target", "label", "outcome", "decision", "hired", "approved", "income", "income_binary"]
        for col in df.columns:
            if str(col).lower() in keywords:
                return col, 0.95
                
        targets = []
        for col in df.columns:
            n_unq = df[col].nunique()
            if 1 < n_unq < 10 and not self._is_sensitive(col):
                targets.append(col)
        if targets:
            return targets[-1], 0.70
            
        cats = df.select_dtypes(include=['object', 'category']).columns
        if len(cats) > 0:
            return cats[-1], 0.40
            
        return df.columns[-1], 0.10

    def _is_sensitive(self, col_name: str) -> bool:
        col_str = str(col_name).lower()
        sensitive_keywords = ["gender", "sex", "race", "ethnicity", "age", "dob", "years"]
        return any(kw in col_str for kw in sensitive_keywords)

    def _detect_sensitive_group(self, df: pd.DataFrame, keywords: list) -> str:
        for col in df.columns:
            for kw in keywords:
                if kw in str(col).lower():
                    return col
        return None

    def compute_fairness(self, test_df: pd.DataFrame, y_pred, sensitive_cols: dict):
        fairness_report = {}
        for key, col in sensitive_cols.items():
            if not col or col not in test_df.columns:
                continue
            
            groups = {}
            rates = []
            test_df_copy = test_df.copy()
            test_df_copy['y_pred'] = y_pred
            
            for group, subset in test_df_copy.groupby(col):
                rate = subset['y_pred'].mean()
                groups[str(group)] = {"rate": float(rate), "count": int(len(subset))}
                rates.append(rate)
                
            if len(rates) > 1:
                max_r = max(rates)
                min_r = min(rates)
                
                max_group = max(groups.keys(), key=lambda k: groups[k]['rate'])
                min_group = min(groups.keys(), key=lambda k: groups[k]['rate'])
                
                disparity = float(max_r - min_r)
                ratio = float(min_r / max_r) if max_r > 0 else 0.0
                score = disparity * (1.0 - ratio)
                
                if score < 0.1: lvl = "Low Bias"
                elif score < 0.3: lvl = "Moderate Bias"
                else: lvl = "High Bias"
                
                fairness_report[key] = {
                    "groups": groups,
                    "disparity": disparity,
                    "ratio": ratio,
                    "score": score,
                    "bias_level": lvl,
                    "insight": f"Model shows higher selection rate for '{max_group}' compared to '{min_group}' indicating potential bias." if disparity > 0.1 else "Demographic selection variance remains within equitable parameters."
                }
        return fairness_report

    def extract_shap(self, clf, X_train_raw, feature_names):
        try:
            preprocessor = clf.named_steps['preprocessor']
            classifier = clf.named_steps['classifier']
            
            sample_size = min(len(X_train_raw), 1000)
            X_trans = preprocessor.transform(X_train_raw[:sample_size])
            if hasattr(X_trans, "toarray"):
                X_trans = X_trans.toarray()
                
            if isinstance(classifier, LogisticRegression):
                explainer = shap.LinearExplainer(classifier, X_trans)
                shap_vals = explainer.shap_values(X_trans)
            else:
                explainer = shap.TreeExplainer(classifier)
                shap_vals = explainer.shap_values(X_trans)
            
            if isinstance(shap_vals, list):
                shap_vals = shap_vals[1]
                
            importances = np.abs(shap_vals).mean(0)
            mean_signed = np.mean(shap_vals, axis=0)
            
            if len(feature_names) == len(importances):
                feat_dict = {str(k): float(v) for k, v in zip(feature_names, importances)}
                signed_dict = {str(k): float(v) for k, v in zip(feature_names, mean_signed)}
                sorted_feats = sorted(feat_dict.items(), key=lambda x: x[1], reverse=True)
                positive = sorted(signed_dict.items(), key=lambda x: x[1], reverse=True)[:5]
                negative = sorted(signed_dict.items(), key=lambda x: x[1])[:5]
                
                return {
                    "top_features": [f[0] for f in sorted_feats[:5]],
                    "feature_impact": {f[0]: float(round(f[1],4)) for f in sorted_feats[:10]},
                    "top_positive_features": [f[0] for f in positive],
                    "top_negative_features": [f[0] for f in negative],
                    "signed_feature_contributions": {k: float(round(v, 4)) for k, v in signed_dict.items()}
                }
        except Exception as e:
            logger.warning(f"SHAP extraction failed: {e}")
            
        return {"top_features": [], "feature_impact": {}}

    def train(self, df_input: pd.DataFrame):
        try:
            df = df_input.copy()

            if df.empty:
                return {"error": "Dataset is completely empty.", "failed": True}
            if len(df) < 50:
                return {"error": "Dataset too small (min 50 rows required).", "failed": True}
            if len(df) > 50000:
                df = df.sample(50000, random_state=self.random_state)
                logger.warning("Dataset truncated to 50,000 rows.")

            missing_ratio = df.isnull().mean().mean()
            if missing_ratio > 0.5:
                return {"error": "Dataset rejected: > 50% missing values globally.", "failed": True}

            df = df.drop_duplicates()

            target_col, conf = self.detect_target(df)
            if not target_col:
                return {"error": "No target column detected.", "failed": True}

            df = df.dropna(subset=[target_col])
            
            class_counts = df[target_col].value_counts(normalize=True)
            if len(class_counts) < 2:
                return {"error": f"Target '{target_col}' lacks multiple classes (requires >= 2).", "failed": True}
            if class_counts.iloc[0] > 0.95:
                logger.warning(f"Extreme class imbalance detected (>95%) on target '{target_col}'.")

            le = LabelEncoder()
            y = le.fit_transform(df[target_col].astype(str))
            
            cols_to_drop = [target_col]
            for col in df.columns:
                if "id" in str(col).lower() and len(df[col].unique()) > len(df) * 0.8:
                    cols_to_drop.append(col)
                    
            X = df.drop(columns=cols_to_drop, errors='ignore')

            num_rows = len(X)
            final_cols = []
            for col in X.columns:
                if X[col].isnull().sum() / num_rows > 0.40:
                    continue
                if X[col].nunique() <= 1:
                    continue
                final_cols.append(col)
            
            X = X[final_cols]
            if X.empty:
                return {"error": "No usable features remain after purging constants/nulls.", "failed": True}

            numeric_features = []
            categorical_features = []
            
            for col in X.columns:
                if pd.api.types.is_numeric_dtype(X[col]):
                    numeric_features.append(col)
                else:
                    X[col] = X[col].astype(str).str.strip().str.lower()
                    X[col] = X[col].replace({'nan': np.nan, 'none': np.nan, 'null': np.nan, '': np.nan})
                    categorical_features.append(col)

            # High Correlation drop (Optional simple logic based on numeric)
            if len(numeric_features) > 1:
                corr_matrix = X[numeric_features].corr().abs()
                upper = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))
                to_drop = [column for column in upper.columns if any(upper[column] > 0.9)]
                X = X.drop(columns=to_drop, errors='ignore')
                numeric_features = [c for c in numeric_features if c not in to_drop]

            transformers = []
            if numeric_features:
                numeric_transformer = Pipeline(steps=[
                    ('imputer', SimpleImputer(strategy='mean')),
                    ('scaler', StandardScaler())
                ])
                transformers.append(('num', numeric_transformer, numeric_features))
                
            if categorical_features:
                categorical_transformer = Pipeline(steps=[
                    ('imputer', SimpleImputer(strategy='most_frequent')),
                    ('onehot', OneHotEncoder(handle_unknown='ignore', sparse_output=False))
                ])
                transformers.append(('cat', categorical_transformer, categorical_features))

            preprocessor = ColumnTransformer(transformers=transformers)

            model = LogisticRegression(class_weight="balanced", max_iter=3000)
            clf = Pipeline(steps=[('preprocessor', preprocessor), ('classifier', model)])

            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=self.random_state, stratify=y
            )

            try:
                clf.fit(X_train, y_train)
            except Exception as e:
                logger.warning(f"LR failed, switching to RandomForest: {e}")
                model = RandomForestClassifier(class_weight="balanced", random_state=self.random_state)
                clf = Pipeline(steps=[('preprocessor', preprocessor), ('classifier', model)])
                clf.fit(X_train, y_train)

            y_pred = clf.predict(X_test)
            if hasattr(clf.named_steps['classifier'], "predict_proba"):
                y_pred_proba = clf.predict_proba(X_test)[:, 1]
            else:
                y_pred_proba = y_pred

            y_classes = len(np.unique(y_test))
            metrics = {
                "accuracy": float(accuracy_score(y_test, y_pred)),
                "precision": float(precision_score(y_test, y_pred, zero_division=0, average='macro' if y_classes > 2 else 'binary')),
                "recall": float(recall_score(y_test, y_pred, zero_division=0, average='macro' if y_classes > 2 else 'binary')),
                "f1_score": float(f1_score(y_test, y_pred, zero_division=0, average='macro' if y_classes > 2 else 'binary')),
                "roc_auc": float(roc_auc_score(y_test, y_pred_proba) if y_classes == 2 else 0.0)
            }

            sensitive_cols = {
                "gender": self._detect_sensitive_group(X, ["gender", "sex", "male", "female"]),
                "race": self._detect_sensitive_group(X, ["race", "ethnicity"]),
                "age": self._detect_sensitive_group(X, ["age", "dob", "years"])
            }
            
            sensitive_feature_values = {
                key: X_test[col].astype(str).fillna("MISSING").tolist()
                for key, col in sensitive_cols.items() if col and col in X_test.columns
            }

            metrics = {
                "accuracy": float(accuracy_score(y_test, y_pred)),
                "precision": float(precision_score(y_test, y_pred, zero_division=0, average='macro' if y_classes > 2 else 'binary')),
                "recall": float(recall_score(y_test, y_pred, zero_division=0, average='macro' if y_classes > 2 else 'binary')),
                "f1_score": float(f1_score(y_test, y_pred, zero_division=0, average='macro' if y_classes > 2 else 'binary')),
                "roc_auc": float(roc_auc_score(y_test, y_pred_proba) if y_classes == 2 else 0.0)
            }

            fairness_metrics = FairnessMetrics(
                y_true=y_test,
                y_pred=y_pred,
                y_pred_proba=y_pred_proba,
                sensitive_features_dict=sensitive_feature_values
            )
            fairness_scores = FairnessScore(fairness_metrics, protected_attributes=list(sensitive_feature_values.keys()))
            fairness_metrics_summary = fairness_scores.get_detailed_breakdown()
            all_fairness_metrics = fairness_metrics.all_metrics()
            fairness_score_value, score_severity = fairness_scores.compute_overall_score()

            try:
                if 'cat' in clf.named_steps['preprocessor'].named_transformers_:
                    cat_enc = clf.named_steps['preprocessor'].named_transformers_['cat'].named_steps['onehot']
                    cat_out_names = cat_enc.get_feature_names_out(categorical_features)
                else:
                    cat_out_names = []
                feature_names = numeric_features + list(cat_out_names)
            except Exception:
                feature_names = numeric_features + categorical_features
                
            shap_data = self.extract_shap(clf, X_train, feature_names)

            class_dist = {str(k): int(v) for k, v in pd.Series(y).value_counts().items()}
            
            selection_rates = {
                attr: all_fairness_metrics.get(attr, {}).get('demographic_parity', {}).get('by_group', {})
                for attr in sensitive_feature_values.keys()
            }

            bias_by_feature = []
            for attr, metrics_summary in fairness_metrics_summary['metric_gaps'].items():
                attr_info = {
                    "attribute": attr,
                    "demographic_parity_gap": metrics_summary.get('demographic_parity_gap', 0.0),
                    "equalized_odds_gap": float(round((metrics_summary.get('equalized_odds_tpr_gap', 0.0) + metrics_summary.get('equalized_odds_fpr_gap', 0.0)) / 2, 4)),
                    "disparate_impact_gap": metrics_summary.get('disparate_impact_gap', 0.0),
                    "calibration_gap": metrics_summary.get('calibration_gap', 0.0),
                    "severity": fairness_scores.get_severity_level(max(
                        metrics_summary.get('demographic_parity_gap', 0.0),
                        metrics_summary.get('equalized_odds_tpr_gap', 0.0),
                        metrics_summary.get('equalized_odds_fpr_gap', 0.0),
                        metrics_summary.get('disparate_impact_gap', 0.0),
                        metrics_summary.get('calibration_gap', 0.0)
                    ))
                }
                bias_by_feature.append(attr_info)

            bias_level = "Low Risk"
            if fairness_score_value < 40:
                bias_level = "High Risk"
            elif fairness_score_value < 70:
                bias_level = "Moderate Risk"

            standard_output = {
                "metrics": metrics,
                "model_performance": metrics,
                "target_column": target_col,
                "target_confidence": conf,
                "class_distribution": class_dist,
                "selection_rates": selection_rates,
                "bias_by_feature": bias_by_feature,
                "fairness_score": fairness_score_value,
                "bias_level": bias_level,
                "fairness_metrics": fairness_metrics_summary,
                "shap_summary": {
                    "top_positive_features": shap_data.get('top_positive_features', []),
                    "top_negative_features": shap_data.get('top_negative_features', []),
                    "feature_impact": shap_data.get('feature_impact', {}),
                    "shap_note": "Top features are based on average SHAP contribution magnitude."
                },
                "fairness": fairness,
                "bias_summary": {
                    "overall_severity": score_severity,
                    "fairness_score": fairness_score_value,
                    "bias_level": bias_level
                },
                "feature_importance": shap_data,
                "insight": "Analysis completed smoothly. No prominent mathematical biases identified." if fairness_score_value >= 70 else "Fairness issues detected; review disparities in protected groups.",
                "charts": {
                    "bar_chart": [{"name": k[:15], "value": v} for k, v in shap_data.get("feature_impact", {}).items()],
                    "pie_chart": [{"name": f"Class {k}", "value": v} for k, v in class_dist.items()],
                    "fairness_chart": []
                },
                "predictions_sample": y_pred[:10].tolist()
            }

            if "gender" in fairness:
                standard_output["charts"]["fairness_chart"] = [{"group": k, "rate": v['rate']} for k, v in fairness["gender"]["groups"].items()]
            elif fairness:
                first_key = list(fairness.keys())[0]
                standard_output["charts"]["fairness_chart"] = [{"group": k, "rate": v['rate']} for k, v in fairness[first_key]["groups"].items()]

            return standard_output
            
        except Exception as e:
            return {"error": str(e), "failed": True}