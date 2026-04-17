import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict
import hashlib
import logging
from collections import OrderedDict

from ml.pipeline import MLPipeline
from gemini_helper import generate_suggestions, generate_detailed_summary, generate_bias_explanation
from fairness.metrics import FairnessMetrics
from fairness.scoring import FairnessScore
from config import MODEL_CACHE_MAX_SIZE
from database import Analysis

logger = logging.getLogger(__name__)

MODEL_CACHE = OrderedDict()


def get_file_hash(file_path):
    hash_sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()


def analyze_bias(file_path, user_id=None, save_to_db=False):
    source_path = Path(file_path).resolve()
    cache_key = get_file_hash(file_path)

    if cache_key in MODEL_CACHE:
        logger.info("Cache hit for file analysis")
        result = MODEL_CACHE[cache_key].copy()
        if save_to_db and user_id:
            Analysis.create(user_id, result.get("dataset_info", {}), result.get("fairness_score", 0.0), result)
        return result

    required_columns = [
        "age", "workclass", "fnlwgt", "education", "education_num",
        "marital_status", "occupation", "relationship", "race",
        "sex", "capital_gain", "capital_loss", "hours_per_week",
        "native_country", "income"
    ]

    try:
        df = pd.read_csv(file_path)
        if df.empty:
            raise ValueError("The uploaded CSV file is completely empty.")
            
        if not set(required_columns).issubset(df.columns):
            df = pd.read_csv(file_path, names=required_columns, header=None)
    except Exception as e:
        logger.error(f"Failed to read CSV file: {e}")
        raise

    df = df[[col for col in required_columns if col in df.columns]].copy()

    categorical_cols = [
        'workclass', 'education', 'marital_status', 'occupation',
        'relationship', 'race', 'sex', 'native_country'
    ]

    for col in categorical_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    dataset_info = {
        "rows": int(len(df)),
        "features": int(len(df.columns)),
        "columns": df.columns.tolist()
    }

    pipeline = MLPipeline(random_state=42)
    train_result = pipeline.train(df)

    y_true = train_result['y_true']
    y_pred = train_result['y_pred']
    y_pred_proba = train_result['y_pred_proba']
    model_metrics = train_result['metrics']

    df_fairness = train_result['test_df'].copy()

    # TARGET
    if 'income_binary' in df_fairness.columns:
        df_fairness['income_binary'] = df_fairness['income_binary'].astype(int)
    elif 'income' in df_fairness.columns:
        df_fairness['income_binary'] = df_fairness['income'].apply(
            lambda x: 1 if '>50K' in str(x) else 0
        )
    else:
        raise ValueError("Target column missing")

    # AGE GROUP
    df_fairness['age_group'] = df_fairness['age'].apply(
        lambda x: "Young" if x < 30 else "Mid" if x < 50 else "Senior"
    )

    # EDUCATION GROUP
    def education_group(x):
        x = str(x).strip()
        if x in {'Preschool','1st-4th','5th-6th','7th-8th','9th','10th','11th','12th'}:
            return 'Basic'
        elif x in {'HS-grad','Some-college','Assoc-acdm','Assoc-voc'}:
            return 'Intermediate'
        elif x in {'Bachelors','Masters','Doctorate','Prof-school'}:
            return 'Advanced'
        return 'Other'

    df_fairness['education_group'] = df_fairness['education'].apply(education_group)

    # BIAS CALC
    def _selection_rate_bias(df_local: pd.DataFrame, attr: str) -> Dict[str, float]:
        if attr not in df_local.columns:
            return {}
        return {
            str(k).strip(): float(v)
            for k, v in df_local.groupby(attr)['y_pred'].mean().to_dict().items()
        }

    gender_bias = _selection_rate_bias(df_fairness, 'sex')
    age_bias = _selection_rate_bias(df_fairness, 'age_group')
    race_bias = _selection_rate_bias(df_fairness, 'race')
    education_bias = _selection_rate_bias(df_fairness, 'education_group')
    occupation_bias = _selection_rate_bias(df_fairness, 'occupation')

    # FAIRNESS METRICS
    sensitive_features_dict = {
        'gender': df_fairness.get('sex').values,
        'age_group': df_fairness.get('age_group').values,
        'race': df_fairness.get('race').values,
        'education_group': df_fairness.get('education_group').values,
        'occupation': df_fairness.get('occupation').values
    }

    fairness_metrics = FairnessMetrics(
        y_true=y_true,
        y_pred=y_pred,
        y_pred_proba=y_pred_proba,
        sensitive_features_dict=sensitive_features_dict
    )

    fairness_score_obj = FairnessScore(
        fairness_metrics=fairness_metrics,
        protected_attributes=['gender', 'age_group', 'race', 'education_group']
    )

    overall_score, severity = fairness_score_obj.compute_overall_score()
    detailed_analysis = fairness_score_obj.get_detailed_breakdown()
    flagged_metrics = fairness_score_obj.get_flagged_metrics()

    # AI INPUT
    bias_payload = {
        "fairness_score": overall_score,
        "gender_bias": gender_bias,
        "age_bias": age_bias,
        "race_bias": race_bias,
        "education_bias": education_bias
    }

    # GEMINI INTEGRATION
    explanation_result = generate_bias_explanation(bias_payload)
    recommendations_result = generate_suggestions(bias_payload)
    summary_result = generate_detailed_summary(bias_payload)

    result = {
        "model_metrics": model_metrics,
        "fairness_score": overall_score,
        "summary": summary_result["summary"],
        "gender_bias": gender_bias,
        "age_bias": age_bias,
        "race_bias": race_bias,
        "education_bias": education_bias,
        "occupation_bias": occupation_bias,
        "explanation": explanation_result["explanations"],
        "recommendations": recommendations_result["recommendations"],
        "ai_used": summary_result["ai_used"] or recommendations_result["ai_used"] or explanation_result["ai_used"],
        "dataset_info": dataset_info,
        "advanced_fairness": {
            "overall_score": overall_score,
            "severity": severity,
            "interpretation": detailed_analysis.get('interpretation', ''),
            "metric_gaps": detailed_analysis.get('metric_gaps', {}),
            "weights": detailed_analysis.get('weights', {}),
            "thresholds": detailed_analysis.get('thresholds', {}),
            "protected_attributes_evaluated": detailed_analysis.get('protected_attributes_evaluated', [])
        },
        "flagged_metrics": flagged_metrics
    }

    MODEL_CACHE[cache_key] = result
    if len(MODEL_CACHE) > MODEL_CACHE_MAX_SIZE:
        MODEL_CACHE.popitem(last=False)

    if save_to_db and user_id:
        try:
            Analysis.create(user_id, dataset_info, overall_score, result)
        except Exception as e:
            logger.warning(f"Failed to save analysis record: {e}")

    logger.info(f"Analysis completed, score: {overall_score}")
    return result