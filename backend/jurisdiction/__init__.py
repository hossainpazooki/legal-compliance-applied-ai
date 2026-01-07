"""
Jurisdiction module for cross-border compliance navigation.

Implements v4 architecture for multi-jurisdiction evaluation.
"""

from .resolver import resolve_jurisdictions, get_equivalences
from .evaluator import evaluate_jurisdiction
from .conflicts import detect_conflicts
from .pathway import synthesize_pathway, aggregate_obligations, estimate_timeline

__all__ = [
    "resolve_jurisdictions",
    "get_equivalences",
    "evaluate_jurisdiction",
    "detect_conflicts",
    "synthesize_pathway",
    "aggregate_obligations",
    "estimate_timeline",
]
