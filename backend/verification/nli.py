"""Tier 3: NLI-based Entailment Checking.

Provides Natural Language Inference (NLI) entailment checking with graceful
fallback to heuristics when ML dependencies (transformers, torch) are unavailable.

Classes:
    NLIChecker: NLI entailment checker with transformer/heuristic fallback.
    NLILabel: Enumeration of NLI labels (entailment, neutral, contradiction).

Functions:
    check_entailment: Check if source entails rule conclusion.
    check_completeness: Check if rule covers source clauses.
    nli_available: Check if ML NLI is available.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING

from backend.rules import Rule, ConsistencyEvidence

if TYPE_CHECKING:
    from transformers import Pipeline


# =============================================================================
# NLI Label Enumeration
# =============================================================================


class NLILabel(str, Enum):
    """NLI classification labels."""

    ENTAILMENT = "entailment"
    NEUTRAL = "neutral"
    CONTRADICTION = "contradiction"


# =============================================================================
# Availability Check
# =============================================================================

_NLI_AVAILABLE: bool | None = None


def nli_available() -> bool:
    """Check if transformers and torch are available for NLI."""
    global _NLI_AVAILABLE
    if _NLI_AVAILABLE is None:
        try:
            import transformers  # noqa: F401
            import torch  # noqa: F401
            _NLI_AVAILABLE = True
        except ImportError:
            _NLI_AVAILABLE = False
    return _NLI_AVAILABLE


# =============================================================================
# Result Dataclass
# =============================================================================


@dataclass
class NLIResult:
    """Result from NLI classification."""

    label: NLILabel
    confidence: float  # 0.0-1.0
    entailment_score: float
    neutral_score: float
    contradiction_score: float


# =============================================================================
# NLIChecker
# =============================================================================


class NLIChecker:
    """NLI entailment checker with transformer/heuristic fallback.

    When transformers/torch are available, uses DeBERTa or RoBERTa models
    for NLI. Falls back to keyword overlap and negation polarity detection
    when ML is unavailable.
    """

    # Model preferences in order
    MODEL_PREFERENCES = [
        "microsoft/deberta-v3-base-mnli",
        "roberta-large-mnli",
        "facebook/bart-large-mnli",
    ]

    # Singleton pipeline instance
    _pipeline: "Pipeline | None" = None
    _pipeline_loaded: bool = False
    _model_name: str | None = None

    def __init__(self, use_ml: bool | None = None):
        """Initialize the NLI checker.

        Args:
            use_ml: Force ML mode (True) or heuristic mode (False).
                   If None, auto-detect based on availability.
        """
        if use_ml is None:
            self.use_ml = nli_available()
        else:
            self.use_ml = use_ml and nli_available()

    @classmethod
    def _get_pipeline(cls) -> "Pipeline | None":
        """Get or load the NLI pipeline (lazy singleton)."""
        if not cls._pipeline_loaded:
            if nli_available():
                try:
                    from transformers import pipeline

                    # Try models in order of preference
                    for model_name in cls.MODEL_PREFERENCES:
                        try:
                            cls._pipeline = pipeline(
                                "text-classification",
                                model=model_name,
                                top_k=None,  # Return all scores
                            )
                            cls._model_name = model_name
                            break
                        except Exception:
                            continue
                except Exception:
                    cls._pipeline = None
            cls._pipeline_loaded = True
        return cls._pipeline

    # -------------------------------------------------------------------------
    # Public Check Methods
    # -------------------------------------------------------------------------

    def check_entailment(
        self,
        rule: Rule,
        source_text: str | None = None,
    ) -> ConsistencyEvidence:
        """Check if source text entails the rule conclusion.

        Tests whether the regulatory source text logically entails
        the conclusions/decisions encoded in the rule.
        """
        if not source_text:
            return self._make_evidence(
                category="entailment",
                label="warning",
                score=0.5,
                details="No source text provided for entailment analysis",
            )

        # Extract hypotheses from rule
        hypotheses = self._extract_hypotheses_from_rule(rule)
        if not hypotheses:
            return self._make_evidence(
                category="entailment",
                label="warning",
                score=0.5,
                details="No hypotheses extracted from rule for entailment",
            )

        # Classify entailment for each hypothesis
        results = []
        for hypothesis in hypotheses:
            result = self._classify_entailment(source_text, hypothesis)
            results.append(result)

        # Aggregate results
        aggregated = self._aggregate_results(results)

        # Map to evidence
        if aggregated.label == NLILabel.ENTAILMENT:
            label = "pass"
            score = aggregated.confidence
        elif aggregated.label == NLILabel.CONTRADICTION:
            label = "fail"
            score = 1 - aggregated.confidence  # Invert for failure score
        else:  # NEUTRAL
            label = "warning"
            score = 0.5

        mode = "ML" if self.use_ml else "heuristic"
        details = f"NLI ({mode}): {aggregated.label.value} (confidence: {aggregated.confidence:.2f})"

        return self._make_evidence(
            category="entailment",
            label=label,
            score=score,
            details=details,
            rule_element="decision_tree",
        )

    def check_completeness(
        self,
        rule: Rule,
        source_text: str | None = None,
    ) -> ConsistencyEvidence:
        """Check if rule covers the clauses in source text.

        Verifies that the rule adequately represents all key normative
        clauses found in the source regulatory text.
        """
        if not source_text:
            return self._make_evidence(
                category="completeness",
                label="warning",
                score=0.5,
                details="No source text provided for completeness analysis",
            )

        # Extract normative clauses from source
        clauses = self._extract_normative_clauses(source_text)
        if not clauses:
            return self._make_evidence(
                category="completeness",
                label="pass",
                score=0.9,
                details="No normative clauses found in source",
            )

        # Get rule representation
        rule_text = self._get_rule_representation(rule)
        if not rule_text:
            return self._make_evidence(
                category="completeness",
                label="warning",
                score=0.5,
                details="Unable to extract rule representation",
            )

        # Check coverage of each clause
        covered = 0
        uncovered_clauses = []

        for clause in clauses:
            # Check if rule entails this clause (or vice versa)
            result = self._classify_entailment(rule_text, clause)
            if result.label == NLILabel.ENTAILMENT or result.label == NLILabel.NEUTRAL:
                covered += 1
            else:
                uncovered_clauses.append(clause[:50] + "...")

        coverage_ratio = covered / len(clauses) if clauses else 0

        if coverage_ratio >= 0.8:
            label = "pass"
        elif coverage_ratio >= 0.5:
            label = "warning"
        else:
            label = "fail"

        details = f"Clause coverage: {covered}/{len(clauses)} ({coverage_ratio:.0%})"
        if uncovered_clauses:
            details += f". Uncovered: {len(uncovered_clauses)} clauses"

        return self._make_evidence(
            category="completeness",
            label=label,
            score=coverage_ratio,
            details=details,
            rule_element="decision_tree, applies_if",
        )

    # -------------------------------------------------------------------------
    # NLI Classification
    # -------------------------------------------------------------------------

    def _classify_entailment(
        self,
        premise: str,
        hypothesis: str,
    ) -> NLIResult:
        """Classify the entailment relationship between premise and hypothesis."""
        if self.use_ml:
            return self._classify_ml(premise, hypothesis)
        else:
            return self._classify_heuristic(premise, hypothesis)

    def _classify_ml(
        self,
        premise: str,
        hypothesis: str,
    ) -> NLIResult:
        """Classify using transformer model."""
        pipeline = self._get_pipeline()
        if pipeline is None:
            return self._classify_heuristic(premise, hypothesis)

        try:
            # Format input for NLI
            # Most models expect premise and hypothesis separated
            input_text = f"{premise} [SEP] {hypothesis}"

            # Some models prefer different format
            if "bart" in (self._model_name or ""):
                input_text = f"{premise}</s></s>{hypothesis}"

            results = pipeline(input_text)

            # Parse results into scores
            scores = {"entailment": 0.0, "neutral": 0.0, "contradiction": 0.0}
            for item in results:
                label_lower = item["label"].lower()
                if "entail" in label_lower:
                    scores["entailment"] = item["score"]
                elif "neutral" in label_lower:
                    scores["neutral"] = item["score"]
                elif "contradict" in label_lower:
                    scores["contradiction"] = item["score"]

            # Determine winning label
            max_label = max(scores, key=scores.get)
            if max_label == "entailment":
                label = NLILabel.ENTAILMENT
            elif max_label == "contradiction":
                label = NLILabel.CONTRADICTION
            else:
                label = NLILabel.NEUTRAL

            return NLIResult(
                label=label,
                confidence=scores[max_label],
                entailment_score=scores["entailment"],
                neutral_score=scores["neutral"],
                contradiction_score=scores["contradiction"],
            )
        except Exception:
            # Fall back to heuristics on error
            return self._classify_heuristic(premise, hypothesis)

    def _classify_heuristic(
        self,
        premise: str,
        hypothesis: str,
    ) -> NLIResult:
        """Classify using heuristics (fallback)."""
        premise_lower = premise.lower()
        hypothesis_lower = hypothesis.lower()

        # 1. Negation polarity detection
        premise_negated = self._has_negation(premise_lower)
        hypothesis_negated = self._has_negation(hypothesis_lower)

        # XOR negation -> likely contradiction
        if premise_negated != hypothesis_negated:
            return NLIResult(
                label=NLILabel.CONTRADICTION,
                confidence=0.6,
                entailment_score=0.2,
                neutral_score=0.2,
                contradiction_score=0.6,
            )

        # 2. Keyword overlap scoring
        premise_tokens = set(re.findall(r"\b[a-zA-Z]{3,}\b", premise_lower))
        hypothesis_tokens = set(re.findall(r"\b[a-zA-Z]{3,}\b", hypothesis_lower))

        if not hypothesis_tokens:
            return NLIResult(
                label=NLILabel.NEUTRAL,
                confidence=0.4,
                entailment_score=0.3,
                neutral_score=0.4,
                contradiction_score=0.3,
            )

        overlap = premise_tokens & hypothesis_tokens
        overlap_ratio = len(overlap) / len(hypothesis_tokens)

        if overlap_ratio > 0.7:
            # High overlap -> entailment
            confidence = 0.5 + (overlap_ratio - 0.7) * 1.0  # 0.5-0.8
            return NLIResult(
                label=NLILabel.ENTAILMENT,
                confidence=min(confidence, 0.8),
                entailment_score=confidence,
                neutral_score=0.15,
                contradiction_score=0.05,
            )
        elif overlap_ratio > 0.4:
            # Medium overlap -> neutral
            return NLIResult(
                label=NLILabel.NEUTRAL,
                confidence=0.5,
                entailment_score=0.3,
                neutral_score=0.5,
                contradiction_score=0.2,
            )
        else:
            # Low overlap -> neutral (not enough info)
            return NLIResult(
                label=NLILabel.NEUTRAL,
                confidence=0.4,
                entailment_score=0.25,
                neutral_score=0.4,
                contradiction_score=0.35,
            )

    def _has_negation(self, text: str) -> bool:
        """Check if text contains negation markers."""
        negation_patterns = [
            r"\bnot\b",
            r"\bno\b",
            r"\bnever\b",
            r"\bwithout\b",
            r"\bprohibited\b",
            r"\bforbidden\b",
            r"\bexcluded\b",
            r"\bdenied\b",
            r"\bn't\b",  # contractions: isn't, doesn't, etc.
        ]
        return any(re.search(p, text, re.IGNORECASE) for p in negation_patterns)

    def _aggregate_results(self, results: list[NLIResult]) -> NLIResult:
        """Aggregate multiple NLI results into a single result."""
        if not results:
            return NLIResult(
                label=NLILabel.NEUTRAL,
                confidence=0.5,
                entailment_score=0.33,
                neutral_score=0.34,
                contradiction_score=0.33,
            )

        # Average the scores
        avg_entailment = sum(r.entailment_score for r in results) / len(results)
        avg_neutral = sum(r.neutral_score for r in results) / len(results)
        avg_contradiction = sum(r.contradiction_score for r in results) / len(results)

        # If any result is contradiction with high confidence, propagate it
        if any(r.label == NLILabel.CONTRADICTION and r.confidence > 0.6 for r in results):
            return NLIResult(
                label=NLILabel.CONTRADICTION,
                confidence=max(r.confidence for r in results if r.label == NLILabel.CONTRADICTION),
                entailment_score=avg_entailment,
                neutral_score=avg_neutral,
                contradiction_score=avg_contradiction,
            )

        # Otherwise, use majority vote
        label_counts = {NLILabel.ENTAILMENT: 0, NLILabel.NEUTRAL: 0, NLILabel.CONTRADICTION: 0}
        for r in results:
            label_counts[r.label] += 1

        winning_label = max(label_counts, key=label_counts.get)
        avg_confidence = sum(r.confidence for r in results) / len(results)

        return NLIResult(
            label=winning_label,
            confidence=avg_confidence,
            entailment_score=avg_entailment,
            neutral_score=avg_neutral,
            contradiction_score=avg_contradiction,
        )

    # -------------------------------------------------------------------------
    # Text Extraction
    # -------------------------------------------------------------------------

    def _extract_hypotheses_from_rule(self, rule: Rule) -> list[str]:
        """Extract hypotheses (claims) from rule to test for entailment."""
        hypotheses = []

        # 1. Rule description
        if rule.description:
            hypotheses.append(rule.description)

        # 2. Decision tree results converted to natural language
        results = self._extract_decision_results(rule)
        for result in results:
            hypothesis = self._result_to_hypothesis(result)
            if hypothesis:
                hypotheses.append(hypothesis)

        # 3. Interpretation notes (first 2 sentences)
        if rule.interpretation_notes:
            sentences = self._split_sentences(rule.interpretation_notes)
            hypotheses.extend(sentences[:2])

        return hypotheses

    def _extract_decision_results(self, rule: Rule) -> list[str]:
        """Extract result strings from decision tree."""
        results = []

        def traverse(node):
            if node is None:
                return
            if hasattr(node, "result") and node.result:
                results.append(node.result)
            if hasattr(node, "true_branch"):
                traverse(node.true_branch)
            if hasattr(node, "false_branch"):
                traverse(node.false_branch)

        if rule.decision_tree:
            traverse(rule.decision_tree)

        return results

    def _result_to_hypothesis(self, result: str) -> str | None:
        """Convert a decision result to a natural language hypothesis."""
        result_lower = result.lower().strip()

        # Map common result codes to hypotheses
        result_mappings = {
            "permitted": "This activity is permitted under the regulation.",
            "prohibited": "This activity is prohibited under the regulation.",
            "required": "This requirement must be fulfilled.",
            "exempt": "This is exempt from the requirements.",
            "subject_to": "This is subject to the specified requirements.",
            "compliant": "This is compliant with the regulation.",
            "non_compliant": "This is not compliant with the regulation.",
            "authorized": "Authorization is granted.",
            "denied": "Authorization is denied.",
            "mandatory": "This is mandatory.",
            "optional": "This is optional.",
        }

        for key, hypothesis in result_mappings.items():
            if key in result_lower:
                return hypothesis

        # If no mapping, use the result directly as hypothesis
        if len(result) > 10:
            return result

        return None

    def _split_sentences(self, text: str) -> list[str]:
        """Split text into sentences."""
        sentences = re.split(r"[.!?]\s+", text)
        return [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]

    def _extract_normative_clauses(self, text: str) -> list[str]:
        """Extract normative clauses (sentences with deontic markers)."""
        deontic_pattern = re.compile(
            r"(shall|must|may|required|permitted|obliged|prohibited|forbidden)",
            re.IGNORECASE
        )

        sentences = self._split_sentences(text)
        return [s for s in sentences if deontic_pattern.search(s)]

    def _get_rule_representation(self, rule: Rule) -> str:
        """Get combined text representation of rule."""
        parts = []

        if rule.description:
            parts.append(rule.description)

        results = self._extract_decision_results(rule)
        parts.extend(results)

        if rule.interpretation_notes:
            parts.append(rule.interpretation_notes[:500])  # Limit length

        return " ".join(parts)

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _make_evidence(
        self,
        category: str,
        label: str,
        score: float,
        details: str,
        source_span: str | None = None,
        rule_element: str | None = None,
    ) -> ConsistencyEvidence:
        """Create a Tier 3 ConsistencyEvidence record."""
        return ConsistencyEvidence(
            tier=3,
            category=category,
            label=label,
            score=score,
            details=details,
            source_span=source_span,
            rule_element=rule_element,
            timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        )


# =============================================================================
# Module-Level Convenience Functions
# =============================================================================

_default_checker: NLIChecker | None = None


def _get_checker() -> NLIChecker:
    """Get or create default NLI checker."""
    global _default_checker
    if _default_checker is None:
        _default_checker = NLIChecker()
    return _default_checker


def check_entailment(
    rule: Rule,
    source_text: str | None = None,
) -> ConsistencyEvidence:
    """Check if source text entails rule conclusion.

    Module-level convenience function using default checker.
    """
    return _get_checker().check_entailment(rule, source_text)


def check_completeness(
    rule: Rule,
    source_text: str | None = None,
) -> ConsistencyEvidence:
    """Check if rule covers source clauses.

    Module-level convenience function using default checker.
    """
    return _get_checker().check_completeness(rule, source_text)


__all__ = [
    "NLIChecker",
    "NLILabel",
    "NLIResult",
    "nli_available",
    "check_entailment",
    "check_completeness",
]
