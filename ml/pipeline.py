"""
ML Pipeline for FairHire — FIXED + PRODUCTION READY
"""

import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import joblib
from config import MODEL_FOLDER
import logging

logger = logging.getLogger(__name__)


class MLPipeline:
    def __init__(self, random_state=42):
        self.random_state = random_state
        self.model = None
        self.scaler = None
        self.ohe_columns = None
        self.model_path = MODEL_FOLDER / "model.joblib"
        self.scaler_path = MODEL_FOLDER / "scaler.joblib"
        self.ohe_path = MODEL_FOLDER / "ohe_columns.joblib"
        self._load_if_exists()

    def _load_if_exists(self):
        try:
            if self.model_path.exists():
                self.model = joblib.load(self.model_path)
                logger.info("Model loaded from disk")
            if self.scaler_path.exists():
                self.scaler = joblib.load(self.scaler_path)
            if self.ohe_path.exists():
                self.ohe_columns = joblib.load(self.ohe_path)
                logger.info("Scaler and OHE columns loaded")
        except Exception as e:
            logger.warning(f"Failed to load model components: {e}")
            self.model = None
            self.scaler = None
            self.ohe_columns = None

    # ---------------- PREPROCESS ---------------- #
    def _preprocess(self, df_input, fit=True):
        df = df_input.copy()

        # ---- CLEAN STRINGS (CRITICAL FIX) ----
        for col in df.columns:
            if df[col].dtype == object:
                df[col] = df[col].astype(str).str.strip()

        # ---- NUMERIC ----
        numeric_cols = ['age', 'education_num', 'hours_per_week']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        df = df.dropna()

        if len(df) == 0:
            raise ValueError("Data parse failure: All rows were corrupted or dropped. Please ensure 'age', 'education_num', and 'hours_per_week' are strictly numeric figures without strings or NaNs.")

        # ---- DROP USELESS ----
        drop_cols = ['fnlwgt', 'native_country', 'capital_gain', 'capital_loss']
        df = df.drop(columns=[c for c in drop_cols if c in df.columns], errors='ignore')

        # ---- REMOVE TARGET ----
        df = df.drop(columns=['income', 'income_binary', 'target'], errors='ignore')

        # ---- ENCODING ----
        categorical_cols = [
            'workclass', 'education', 'marital_status',
            'occupation', 'relationship', 'race', 'sex'
        ]
        categorical_cols = [c for c in categorical_cols if c in df.columns]

        df_encoded = pd.get_dummies(df, columns=categorical_cols, drop_first=False)

        # ---- ALIGN ----
        if fit:
            self.ohe_columns = df_encoded.columns.tolist()
        else:
            for col in self.ohe_columns:
                if col not in df_encoded.columns:
                    df_encoded[col] = 0
            df_encoded = df_encoded[self.ohe_columns]

        # ---- SCALE ----
        if fit:
            self.scaler = StandardScaler()
            df_encoded[numeric_cols] = self.scaler.fit_transform(df_encoded[numeric_cols])
        else:
            df_encoded[numeric_cols] = self.scaler.transform(df_encoded[numeric_cols])

        return df_encoded.astype(float)

    # ---------------- TRAIN ---------------- #
    def train(self, df_input):
        df = df_input.copy()

        # ---- TARGET ----
        if 'income_binary' in df.columns:
            df['target'] = df['income_binary']
        elif 'income' in df.columns:
            df['target'] = df['income'].apply(lambda x: 1 if '>50K' in str(x) else 0)
        else:
            raise ValueError("Target column missing")

        # ---- SPLIT ----
        train_df, test_df = train_test_split(
            df,
            test_size=0.2,
            random_state=self.random_state,
            stratify=df['target']
        )

        # ---- PREPROCESS ----
        X_train = self._preprocess(train_df, fit=True)
        X_test = self._preprocess(test_df, fit=False)

        y_train = train_df['target'].values
        y_test = test_df['target'].values

        # ---- MODEL ----
        self.model = LogisticRegression(
            max_iter=3000,
            class_weight='balanced'
        )

        self.model.fit(X_train, y_train)

        # ---- PREDICT ----
        y_pred = self.model.predict(X_test)
        y_pred_proba = self.model.predict_proba(X_test)[:, 1]

        # ---- METRICS ----
        metrics = {
            "accuracy": round(float(accuracy_score(y_test, y_pred)), 4),
            "precision": round(float(precision_score(y_test, y_pred, zero_division=0)), 4),
            "recall": round(float(recall_score(y_test, y_pred, zero_division=0)), 4),
            "f1": round(float(f1_score(y_test, y_pred, zero_division=0)), 4),
            "auc": round(float(roc_auc_score(y_test, y_pred_proba)), 4),
        }

        # ---- ATTACH PRED ----
        test_df = test_df.reset_index(drop=True)
        test_df['y_pred'] = y_pred
        test_df['y_pred_proba'] = y_pred_proba

        logger.info("Model trained successfully")

        # Save model components
        try:
            joblib.dump(self.model, self.model_path)
            joblib.dump(self.scaler, self.scaler_path)
            joblib.dump(self.ohe_columns, self.ohe_path)
            logger.info("Model saved to disk")
        except Exception as e:
            logger.error(f"Failed to save model: {e}")

        return {
            "y_true": y_test,
            "y_pred": y_pred,
            "y_pred_proba": y_pred_proba,
            "metrics": metrics,
            "test_df": test_df
        }

    # ---------------- SAVE ---------------- #
    def save_model(self, name="model.joblib"):
        if self.model is None:
            raise ValueError("No model")

        path = MODEL_FOLDER / name
        joblib.dump(self.model, path)
        return str(path)

    # ---------------- LOAD ---------------- #
    def load_model(self, path):
        self.model = joblib.load(path)

    # ---------------- PREDICT ---------------- #
    def predict(self, df):
        X = self._preprocess(df, fit=False)
        return self.model.predict(X)

    def predict_proba(self, df):
        X = self._preprocess(df, fit=False)
        return self.model.predict_proba(X)[:, 1]