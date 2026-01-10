"""Embedding service module for rule search.

Supports 4 types of embeddings per rule:
- Semantic: from natural language description
- Structural: from serialized conditions/logic
- Entity: from extracted field names
- Legal: from legal source citations
"""

from .models import (
    EmbeddingRule,
    EmbeddingCondition,
    EmbeddingDecision,
    EmbeddingLegalSource,
    RuleEmbedding,
    EmbeddingType,
)
from .schemas import (
    ConditionCreate,
    ConditionRead,
    DecisionCreate,
    DecisionRead,
    LegalSourceCreate,
    LegalSourceRead,
    RuleCreate,
    RuleUpdate,
    RuleRead,
    RuleList,
    EmbeddingRead,
    EmbeddingWithVector,
    SimilarityResult,
    SearchRequest,
    EmbeddingTypeEnum,
)
from .service import EmbeddingRuleService
from .generator import EmbeddingGenerator, ml_available

__all__ = [
    # Models
    "EmbeddingRule",
    "EmbeddingCondition",
    "EmbeddingDecision",
    "EmbeddingLegalSource",
    "RuleEmbedding",
    "EmbeddingType",
    # Schemas
    "ConditionCreate",
    "ConditionRead",
    "DecisionCreate",
    "DecisionRead",
    "LegalSourceCreate",
    "LegalSourceRead",
    "RuleCreate",
    "RuleUpdate",
    "RuleRead",
    "RuleList",
    "EmbeddingRead",
    "EmbeddingWithVector",
    "SimilarityResult",
    "SearchRequest",
    "EmbeddingTypeEnum",
    # Services
    "EmbeddingRuleService",
    "EmbeddingGenerator",
    "ml_available",
]
