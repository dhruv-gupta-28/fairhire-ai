"""
ML Pipeline for FairHire — Fully Generic and Intelligent
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
import joblib
from config import MODEL_FOLDER

logger = logging.getLogger(__name__)

class MLPipeline:
    def __init__(self, random_state=42):
        self.random_state = random_state

    def detect_target(self, df: pd.DataFrame) -> str:
        # Priority 1: Name match
        target_keywords = ["target", "label", "outcome", "decision", "hired", "approved", "income", "income_binary"]
        for col in df.columns:
            if str(col).lower() in target_keywords:
                return col
        
        # Priority 2: Low unique values (<10)
        potential_targets = []
        for col in df.columns:
            n_unique = df[col].nunique()
            if 1 < n_unique < 10:
                potential_targets.append(col)
        if potential_targets:
            return potential_targets[-1] # Usually at the end
            
        # Priority 3: Last categorical column
        categorical_cols = df.select_dtypes(include=['object', 'category']).columns
        if len(categorical_cols) > 0:
            return categorical_cols[-1]
            
        return df.columns[-1]

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
                
            if rates:
                max_r = max(rates)
                min_r = min(rates)
                fairness_report[key] = {
                    "groups": groups,
                    "disparity": float(max_r - min_r),
                    "ratio": float(min_r / max_r) if max_r > 0 else 0.0
                }
        return fairness_report

    def train(self, df_input: pd.DataFrame):
        df = df_input.copy()

        # EDA: Remove duplicates
        df = df.drop_duplicates()

        # Identify target
        target_col = self.detect_target(df)
        if not target_col:
            raise ValueError("No target column could be detected.")

        # Drop NaNs in target
        df = df.dropna(subset=[target_col])
        if df[target_col].nunique() < 2:
            raise ValueError(f"Target column '{target_col}' has fewer than 2 classes. At least 2 distinct classes are required.")

        # Encode target
        le = LabelEncoder()
        y = le.fit_transform(df[target_col].astype(str))
        
        # Drop ID and target columns from X
        cols_to_drop = [target_col]
        for col in df.columns:
            if "id" in str(col).lower() and len(df[col].unique()) == len(df):
                cols_to_drop.append(col)
        
        X = df.drop(columns=cols_to_drop, errors='ignore')

        # EDA: Missing values and constant cols
        num_rows = len(X)
        final_cols = []
        for col in X.columns:
            missing_ratio = X[col].isnull().sum() / num_rows
            if missing_ratio > 0.40:
                continue
            if X[col].nunique() <= 1:
                continue
            final_cols.append(col)
        
        X = X[final_cols]
        if X.empty:
            raise ValueError("No valid features remaining after purging empty or constant columns.")

        # Feature separation
        numeric_features = []
        categorical_features = []
        
        for col in X.columns:
            if pd.api.types.is_numeric_dtype(X[col]):
                numeric_features.append(col)
            else:
                categorical_features.append(col)
                X[col] = X[col].astype(str).str.strip().str.lower()
                X[col] = X[col].replace({'nan': np.nan, 'none': np.nan, 'null': np.nan, '': np.nan})

        # Preprocessing Pipeline
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

        # Model Strategy
        model = LogisticRegression(class_weight="balanced", max_iter=3000)
        clf = Pipeline(steps=[('preprocessor', preprocessor), ('classifier', model)])

        # Split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=self.random_state, stratify=y
        )

        try:
            clf.fit(X_train, y_train)
        except Exception as e:
            logger.error(f"Logistic Regression failed, falling back to Random Forest: {e}")
            model = RandomForestClassifier(class_weight="balanced", random_state=self.random_state)
            clf = Pipeline(steps=[('preprocessor', preprocessor), ('classifier', model)])
            clf.fit(X_train, y_train)

        logger.info("Model trained successfully.")

        # Predict
        y_pred = clf.predict(X_test)
        if hasattr(clf.named_steps['classifier'], "predict_proba"):
            y_pred_proba = clf.predict_proba(X_test)[:, 1]
        else:
            y_pred_proba = y_pred

        # Metrics
        y_test_classes = len(np.unique(y_test))
        metrics = {
            "accuracy": float(accuracy_score(y_test, y_pred)),
            "precision": float(precision_score(y_test, y_pred, zero_division=0, average='macro' if y_test_classes > 2 else 'binary')),
            "recall": float(recall_score(y_test, y_pred, zero_division=0, average='macro' if y_test_classes > 2 else 'binary')),
            "f1_score": float(f1_score(y_test, y_pred, zero_division=0, average='macro' if y_test_classes > 2 else 'binary')),
            "roc_auc": float(roc_auc_score(y_test, y_pred_proba) if y_test_classes == 2 else 0.0)
        }

        # Fairness
        sensitive_cols = {
            "gender": self._detect_sensitive_group(X, ["gender", "sex", "male", "female"]),
            "race": self._detect_sensitive_group(X, ["race", "ethnicity"]),
            "age": self._detect_sensitive_group(X, ["age", "dob", "years"])
        }
        
        fairness = self.compute_fairness(X_test, y_pred, sensitive_cols)

        return {
            "metrics": metrics,
            "target_column": target_col,
            "feature_summary": {
                "num_features": len(numeric_features),
                "cat_features": len(categorical_features)
            },
            "fairness": fairness,
            "predictions_sample": y_pred[:10].tolist(),
            "class_distribution": {str(k): int(v) for k, v in pd.Series(y).value_counts().items()},
            "raw_test_df": X_test.copy(),
            "y_true": y_test,
            "y_pred": y_pred,
            "y_pred_proba": y_pred_proba
        }