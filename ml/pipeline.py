"""
ML Pipeline for FairHire — Next-Gen Production SHAP AI Engine
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
import joblib
from config import MODEL_FOLDER

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
            if 1 < n_unq < 10:
                targets.append(col)
        if targets:
            return targets[-1], 0.70
            
        cats = df.select_dtypes(include=['object', 'category']).columns
        if len(cats) > 0:
            return cats[-1], 0.40
            
        return df.columns[-1], 0.10

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
                disparity = float(max_r - min_r)
                ratio = float(min_r / max_r) if max_r > 0 else 0.0
                
                if disparity < 0.1: lvl = "Low Bias"
                elif disparity < 0.3: lvl = "Moderate Bias"
                else: lvl = "High Bias"
                
                fairness_report[key] = {
                    "groups": groups,
                    "disparity": disparity,
                    "ratio": ratio,
                    "bias_level": lvl
                }
        return fairness_report

    def extract_shap(self, clf, X_train_raw, feature_names):
        try:
            preprocessor = clf.named_steps['preprocessor']
            classifier = clf.named_steps['classifier']
            
            # Using only 200 samples natively limits computation load dramatically so SHAP responds fast
            X_trans = preprocessor.transform(X_train_raw[:200])
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
            
            if len(feature_names) == len(importances):
                feat_dict = {str(k): float(v) for k, v in zip(feature_names, importances)}
                sorted_feats = sorted(feat_dict.items(), key=lambda x: x[1], reverse=True)
                
                return {
                    "top_features": [f[0] for f in sorted_feats[:5]],
                    "feature_impact": {f[0]: float(round(f[1],4)) for f in sorted_feats[:10]}
                }
        except Exception as e:
            logger.warning(f"SHAP extraction failed natively: {e}")
            
        return {"top_features": [], "feature_impact": {}}

    def train(self, df_input: pd.DataFrame):
        try:
            df = df_input.copy()

            if df.empty:
                raise ValueError("Dataset is completely empty.")
            if len(df) < 50:
                raise ValueError("Dataset too small (min 50 rows required).")
            if len(df) > 50000:
                raise ValueError("Dataset exceeds size limit (max 50,000 rows).")

            missing_ratio = df.isnull().mean().mean()
            if missing_ratio > 0.5:
                raise ValueError("Dataset rejected: > 50% missing values globally.")

            df = df.drop_duplicates()

            target_col, conf = self.detect_target(df)
            if not target_col:
                raise ValueError("No target column detected.")

            df = df.dropna(subset=[target_col])
            if df[target_col].nunique() < 2:
                raise ValueError(f"Target '{target_col}' lacks multiple classes (requires >= 2).")

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
                raise ValueError("No usable features remain after purging constants/nulls.")

            numeric_features = []
            categorical_features = []
            
            for col in X.columns:
                if pd.api.types.is_numeric_dtype(X[col]):
                    numeric_features.append(col)
                else:
                    X[col] = X[col].astype(str).str.strip().str.lower()
                    X[col] = X[col].replace({'nan': np.nan, 'none': np.nan, 'null': np.nan, '': np.nan})
                    categorical_features.append(col)

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

            logger.info("Model trained successfully.")

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
            
            fairness = self.compute_fairness(X_test, y_pred, sensitive_cols)

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
            
            bar_chart = [{"name": k, "value": v} for k, v in shap_data.get("feature_impact", {}).items()]
            pie_chart = [{"name": f"Class {k}", "value": v} for k, v in class_dist.items()]
            
            fairness_chart = []
            if "gender" in fairness:
                fairness_chart = [{"group": k, "rate": v['rate']} for k, v in fairness["gender"]["groups"].items()]
            elif fairness:
                first_key = list(fairness.keys())[0]
                fairness_chart = [{"group": k, "rate": v['rate']} for k, v in fairness[first_key]["groups"].items()]

            overall_bias_levels = [v.get("bias_level", "Low Bias") for v in fairness.values()] + ["Low Bias"]
            highest_severity = max(overall_bias_levels, key=lambda x: {"Low Bias": 0, "Moderate Bias": 1, "High Bias": 2}[x])
            
            # Simple score deduction based on severity mapping
            overall_severity_deduction = {"Low Bias": 0, "Moderate Bias": 20, "High Bias": 50}[highest_severity]

            return {
                "metrics": metrics,
                "target_column": target_col,
                "target_confidence": conf,
                "feature_summary": {
                    "num_features": len(numeric_features),
                    "cat_features": len(categorical_features)
                },
                "fairness": fairness,
                "feature_importance": shap_data,
                "bias_summary": {
                    "overall_severity": highest_severity,
                    "fairness_score": float(100 - overall_severity_deduction)
                },
                "charts": {
                    "bar_chart": bar_chart,
                    "pie_chart": pie_chart,
                    "fairness_chart": fairness_chart
                },
                "predictions_sample": y_pred[:10].tolist(),
                "class_distribution": class_dist,
                "raw_test_df": X_test.copy()
            }
        except Exception as e:
            return {"error": str(e), "failed": True}