"""
Fairness module: Multi-metric evaluation system for hiring bias detection.

Phase 2: Advanced fairness metrics aligned with industry standards.
Preserves Phase 1 test-set-only evaluation and backward compatibility.
"""

from .metrics import FairnessMetrics
from .scoring import FairnessScore

__all__ = ["FairnessMetrics", "FairnessScore"]