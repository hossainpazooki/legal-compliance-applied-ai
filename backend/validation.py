"""Pydantic validation layer for runtime type safety.

This module provides validation utilities for:
- Scenario input validation
- Rule evaluation request validation
- API response validation

All types use Pydantic v2 for runtime validation.
"""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field, field_validator


class ScenarioInput(BaseModel):
    """Validated scenario input for rule evaluation."""

    instrument_type: str = Field(..., description="Type of crypto-asset or instrument")
    jurisdiction: str = Field(default="EU", description="Regulatory jurisdiction")
    activity: str | None = Field(default=None, description="Type of regulated activity")

    # Optional attributes
    is_credit_institution: bool = Field(default=False)
    authorized: bool = Field(default=False)
    rwa_authorized: bool = Field(default=False)
    is_regulated_market_issuer: bool = Field(default=False)
    custodian_authorized: bool = Field(default=False)
    assets_segregated: bool = Field(default=False)
    disclosure_current: bool = Field(default=False)
    total_token_value_eur: float | None = Field(default=None, ge=0)

    # Additional attributes (flexible)
    extra_attributes: dict[str, Any] = Field(default_factory=dict)

    @field_validator("instrument_type")
    @classmethod
    def validate_instrument_type(cls, v: str) -> str:
        """Normalize instrument type."""
        return v.lower().strip()

    @field_validator("jurisdiction")
    @classmethod
    def validate_jurisdiction(cls, v: str) -> str:
        """Normalize jurisdiction."""
        return v.upper().strip()

    def to_scenario_dict(self) -> dict[str, Any]:
        """Convert to dict for Scenario construction."""
        result = {
            "instrument_type": self.instrument_type,
            "jurisdiction": self.jurisdiction,
            "is_credit_institution": self.is_credit_institution,
            "authorized": self.authorized,
            "rwa_authorized": self.rwa_authorized,
            "is_regulated_market_issuer": self.is_regulated_market_issuer,
            "custodian_authorized": self.custodian_authorized,
            "assets_segregated": self.assets_segregated,
            "disclosure_current": self.disclosure_current,
        }

        if self.activity:
            result["activity"] = self.activity

        if self.total_token_value_eur is not None:
            result["total_token_value_eur"] = self.total_token_value_eur

        # Merge extra attributes
        result.update(self.extra_attributes)

        return result


class EvaluationRequest(BaseModel):
    """Request to evaluate rules against a scenario."""

    scenario: ScenarioInput
    rule_ids: list[str] | None = Field(
        default=None,
        description="Specific rule IDs to evaluate. If None, evaluates all applicable rules.",
    )


class ObligationResponse(BaseModel):
    """Obligation in an evaluation response."""

    id: str
    description: str | None = None
    deadline: str | None = None


class TraceStepResponse(BaseModel):
    """Single step in a decision trace."""

    node: str
    condition: str
    result: bool
    value_checked: Any = None


class RuleEvaluationResponse(BaseModel):
    """Response from evaluating a single rule."""

    rule_id: str
    applicable: bool
    decision: str | None = None
    obligations: list[ObligationResponse] = Field(default_factory=list)
    trace: list[TraceStepResponse] = Field(default_factory=list)
    error: str | None = None


class EvaluationResponse(BaseModel):
    """Response from rule evaluation."""

    scenario: dict[str, Any]
    results: list[RuleEvaluationResponse]
    engine_type: str = "python"


__all__ = [
    "ScenarioInput",
    "EvaluationRequest",
    "ObligationResponse",
    "TraceStepResponse",
    "RuleEvaluationResponse",
    "EvaluationResponse",
]
