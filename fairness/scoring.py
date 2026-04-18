from typing import Dict, List, Optional
from .metrics import FairnessMetrics
import numpy as np


class FairnessScore:

    DEFAULT_WEIGHTS = {
        'demographic_parity': 0.25,
        'equalized_odds': 0.25,
        'disparate_impact': 0.25,
        'calibration': 0.25
    }

    THRESHOLD_ACCEPTABLE = 0.10
    THRESHOLD_WARNING = 0.15

    def __init__(
        self,
        fairness_metrics: FairnessMetrics,
        protected_attributes: Optional[List[str]] = None,
        weights: Optional[Dict[str, float]] = None
    ):
        self.metrics = fairness_metrics
        self.protected_attributes = protected_attributes or list(
            fairness_metrics.sensitive_features_dict.keys()
        )
        self.weights = weights or self.DEFAULT_WEIGHTS

        if abs(sum(self.weights.values()) - 1.0) > 1e-6:
            raise ValueError("Weights must sum to 1")

        self._cached_metrics = None
        self._cached_overall_score = None
        self._cached_flagged = None

    def _get_all_metrics(self):
        if self._cached_metrics is None:
            self._cached_metrics = self.metrics.all_metrics(self.protected_attributes)
        return self._cached_metrics

    def _non_linear_penalty(self, gap: float) -> float:
        """
        Penalty curve:
        - gap < 0.10: low penalty (acceptable range)
        - gap 0.10-0.20: moderate ramp
        - gap 0.20-0.40: significant but not saturating
        - gap > 0.40: heavy penalty, saturates at 1.0 only above 0.60
        """
        gap = max(0.0, min(1.0, gap))

        if gap < 0.10:
            return gap * 0.5
        elif gap < 0.20:
            return 0.05 + (gap - 0.10) * 1.0
        elif gap < 0.40:
            return 0.15 + (gap - 0.20) * 1.5
        else:
            return min(1.0, 0.45 + (gap - 0.40) * 2.75)

    def compute_metric_gaps(self):
        all_metrics = self._get_all_metrics()
        gaps = {}

        for attr in self.protected_attributes:
            attr_metrics = all_metrics.get(attr, {})

            gaps[attr] = {
                'demographic_parity_gap': attr_metrics.get('demographic_parity', {}).get('difference', 0.0),
                'equalized_odds_tpr_gap': attr_metrics.get('equalized_odds', {}).get('tpr_gap', 0.0),
                'equalized_odds_fpr_gap': attr_metrics.get('equalized_odds', {}).get('fpr_gap', 0.0),
                'disparate_impact_gap': 1.0 - attr_metrics.get('disparate_impact', {}).get('ratio', 1.0),
                'calibration_gap': attr_metrics.get('calibration', {}).get('gap', 0.0)
            }

        return gaps

    def compute_overall_score(self):
        if self._cached_overall_score is not None:
            return self._cached_overall_score

        gaps = self.compute_metric_gaps()

        metric_aggregates = {
            'demographic_parity': [],
            'equalized_odds': [],
            'disparate_impact': [],
            'calibration': []
        }

        for attr_gaps in gaps.values():
            metric_aggregates['demographic_parity'].append(attr_gaps['demographic_parity_gap'])
            metric_aggregates['equalized_odds'].append(
                (attr_gaps['equalized_odds_tpr_gap'] + attr_gaps['equalized_odds_fpr_gap']) / 2
            )
            metric_aggregates['disparate_impact'].append(attr_gaps['disparate_impact_gap'])
            metric_aggregates['calibration'].append(attr_gaps['calibration_gap'])

        avg_gaps = {
            k: float(np.max(v)) if v else 0.0
            for k, v in metric_aggregates.items()
        }

        penalized = {
            k: self._non_linear_penalty(v)
            for k, v in avg_gaps.items()
        }

        weighted_penalty = sum(
            self.weights[k] * penalized[k]
            for k in self.weights
        )

        score = max(0.0, min(100.0, (1.0 - weighted_penalty) * 100))
        score = float(round(score, 2))

        if score >= 80:
            severity = 'ACCEPTABLE'
        elif score >= 60:
            severity = 'WARNING'
        else:
            severity = 'CRITICAL'

        self._cached_overall_score = (score, severity)
        return self._cached_overall_score

    def get_severity_level(self, gap):
        if gap < self.THRESHOLD_ACCEPTABLE:
            return 'ACCEPTABLE'
        elif gap < self.THRESHOLD_WARNING:
            return 'WARNING'
        else:
            return 'CRITICAL'

    def get_flagged_metrics(self):
        if self._cached_flagged is not None:
            return self._cached_flagged

        gaps = self.compute_metric_gaps()
        flagged = {}

        for attr, attr_gaps in gaps.items():
            attr_flagged = {}

            for metric_name, gap_value in attr_gaps.items():
                severity = self.get_severity_level(gap_value)

                if severity in ['WARNING', 'CRITICAL']:
                    attr_flagged[metric_name] = {
                        'gap': float(round(gap_value, 4)),
                        'severity': severity
                    }

            if attr_flagged:
                flagged[attr] = attr_flagged

        self._cached_flagged = flagged
        return flagged

    def get_detailed_breakdown(self):
        score, severity = self.compute_overall_score()

        return {
            'overall_score': score,
            'severity': severity,
            'metric_gaps': self.compute_metric_gaps(),
            'flagged_metrics': self.get_flagged_metrics(),
            'weights': self.weights,
            'protected_attributes_evaluated': self.protected_attributes,
            'interpretation': "Lower gaps indicate fairer and more equitable outcomes across groups."
        }
