"""Verification domain - rule consistency checking and validation.

Provides 5-tier semantic consistency verification:
- Tier 0: Schema & Structural Validation
- Tier 1: Lexical & Heuristic Analysis
- Tier 2: Semantic Similarity (ML sentence-transformers + fallback)
- Tier 3: NLI Entailment (ML transformers/torch + fallback)
- Tier 4: Cross-Rule Consistency (deterministic)
"""

from .service import (
    ConsistencyEngine,
    verify_rule,
    # Tier 0 checks
    check_schema_valid,
    check_required_fields,
    check_source_exists,
    check_date_consistency,
    check_id_format,
    check_decision_tree_valid,
    # Tier 1 checks
    check_deontic_alignment,
    check_actor_mentioned,
    check_instrument_mentioned,
    check_keyword_overlap,
    check_negation_consistency,
    check_exception_coverage,
    # Utilities
    compute_summary,
)

# Tier 2: Embeddings
from .embeddings import (
    embedding_available,
    check_semantic_alignment,
    check_obligation_similarity,
    check_condition_grounding,
    EmbeddingChecker,
    SimilarityResult,
)

# Tier 3: NLI
from .nli import (
    nli_available,
    check_entailment,
    check_completeness,
    NLIChecker,
    NLILabel,
    NLIResult,
)

# Tier 4: Cross-Rule
from .cross_rule import (
    check_cross_rule_consistency,
    check_contradiction,
    check_hierarchy,
    check_temporal_consistency,
    CrossRuleChecker,
    ContradictionResult,
    HierarchyResult,
    TemporalResult,
)

__all__ = [
    # Engine and main entry
    "ConsistencyEngine",
    "verify_rule",
    # Tier 0 checks
    "check_schema_valid",
    "check_required_fields",
    "check_source_exists",
    "check_date_consistency",
    "check_id_format",
    "check_decision_tree_valid",
    # Tier 1 checks
    "check_deontic_alignment",
    "check_actor_mentioned",
    "check_instrument_mentioned",
    "check_keyword_overlap",
    "check_negation_consistency",
    "check_exception_coverage",
    # Tier 2: Embeddings
    "embedding_available",
    "check_semantic_alignment",
    "check_obligation_similarity",
    "check_condition_grounding",
    "EmbeddingChecker",
    "SimilarityResult",
    # Tier 3: NLI
    "nli_available",
    "check_entailment",
    "check_completeness",
    "NLIChecker",
    "NLILabel",
    "NLIResult",
    # Tier 4: Cross-Rule
    "check_cross_rule_consistency",
    "check_contradiction",
    "check_hierarchy",
    "check_temporal_consistency",
    "CrossRuleChecker",
    "ContradictionResult",
    "HierarchyResult",
    "TemporalResult",
    # Utilities
    "compute_summary",
]
