"""Pydantic schemas for embedding rule API."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class EmbeddingTypeEnum(str, Enum):
    """Types of embeddings generated per rule."""
    SEMANTIC = "semantic"
    STRUCTURAL = "structural"
    ENTITY = "entity"
    LEGAL = "legal"


class EmbeddingRead(BaseModel):
    """Read schema for a rule embedding."""
    id: int
    embedding_type: str
    vector_dim: int
    model_name: str
    source_text: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class EmbeddingWithVector(EmbeddingRead):
    """Embedding with the actual vector (for search results)."""
    vector: list[float] = Field(description="The embedding vector")


class SimilarityResult(BaseModel):
    """Result of a similarity search."""
    rule_id: str
    rule_name: str
    score: float = Field(description="Similarity score (0-1, higher is more similar)")
    embedding_type: str
    matched_text: Optional[str] = None


class SearchRequest(BaseModel):
    """Request for embedding-based search."""
    query: str = Field(description="Text query to search for")
    embedding_types: list[EmbeddingTypeEnum] = Field(
        default_factory=lambda: list(EmbeddingTypeEnum),
        description="Types of embeddings to search (defaults to all)",
    )
    limit: int = Field(default=10, ge=1, le=100, description="Maximum number of results")
    min_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Minimum similarity score")


class ConditionCreate(BaseModel):
    field: str
    operator: str
    value: str
    description: Optional[str] = None


class ConditionRead(BaseModel):
    id: int
    field: str
    operator: str
    value: str
    description: Optional[str]

    model_config = {"from_attributes": True}


class DecisionCreate(BaseModel):
    outcome: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    explanation: Optional[str] = None


class DecisionRead(BaseModel):
    id: int
    outcome: str
    confidence: float
    explanation: Optional[str]

    model_config = {"from_attributes": True}


class LegalSourceCreate(BaseModel):
    citation: str
    document_id: Optional[str] = None
    url: Optional[str] = None


class LegalSourceRead(BaseModel):
    id: int
    citation: str
    document_id: Optional[str]
    url: Optional[str]

    model_config = {"from_attributes": True}


class RuleCreate(BaseModel):
    rule_id: str
    name: str
    description: Optional[str] = None
    conditions: list[ConditionCreate] = Field(default_factory=list)
    decision: Optional[DecisionCreate] = None
    legal_sources: list[LegalSourceCreate] = Field(default_factory=list)
    generate_embeddings: bool = Field(default=True, description="Whether to generate embeddings for this rule")


class RuleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    conditions: Optional[list[ConditionCreate]] = None
    decision: Optional[DecisionCreate] = None
    legal_sources: Optional[list[LegalSourceCreate]] = None
    is_active: Optional[bool] = None
    regenerate_embeddings: bool = Field(default=False, description="Whether to regenerate embeddings")


class RuleRead(BaseModel):
    id: int
    rule_id: str
    name: str
    description: Optional[str]
    created_at: datetime
    updated_at: datetime
    is_active: bool
    conditions: list[ConditionRead]
    decision: Optional[DecisionRead]
    legal_sources: list[LegalSourceRead]
    embeddings: list[EmbeddingRead] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class RuleList(BaseModel):
    id: int
    rule_id: str
    name: str
    description: Optional[str]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
