"""Tier 2: Semantic Similarity with Embeddings.

Provides embedding-based semantic similarity checking with graceful fallback
to heuristics when ML dependencies (sentence-transformers) are unavailable.

Classes:
    EmbeddingChecker: Dual-mode semantic checker with ML and heuristic fallback.

Functions:
    check_semantic_alignment: Check rule logic matches source semantically.
    check_obligation_similarity: Check rule obligations match source requirements.
    check_condition_grounding: Check conditions grounded in source text.
    embedding_available: Check if ML embedding is available.
"""

from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from backend.rules import Rule, ConsistencyEvidence

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer


# =============================================================================
# Availability Check
# =============================================================================

_EMBEDDING_AVAILABLE: bool | None = None


def embedding_available() -> bool:
    """Check if sentence-transformers is available."""
    global _EMBEDDING_AVAILABLE
    if _EMBEDDING_AVAILABLE is None:
        try:
            import sentence_transformers  # noqa: F401
            _EMBEDDING_AVAILABLE = True
        except ImportError:
            _EMBEDDING_AVAILABLE = False
    return _EMBEDDING_AVAILABLE


# =============================================================================
# Result Dataclass
# =============================================================================


@dataclass
class SimilarityResult:
    """Result from similarity computation."""

    label: str  # "high", "medium", "low"
    score: float  # 0.0-1.0
    details: str
    matched_segments: list[tuple[str, str, float]] = field(default_factory=list)


# =============================================================================
# EmbeddingChecker
# =============================================================================


class EmbeddingChecker:
    """Dual-mode semantic checker with ML and heuristic fallback.

    When sentence-transformers is available, uses all-MiniLM-L6-v2 model
    for embeddings. Falls back to TF-IDF weighted keyword overlap and
    n-gram matching when ML is unavailable.
    """

    HIGH_THRESHOLD = 0.75   # >= 0.75 -> "high" (pass)
    MEDIUM_THRESHOLD = 0.50  # >= 0.50 -> "medium" (warning)
    # < 0.50 -> "low" (fail)

    MODEL_NAME = "all-MiniLM-L6-v2"
    EMBEDDING_DIM = 384

    # Singleton model instance
    _model: "SentenceTransformer | None" = None
    _model_loaded: bool = False

    def __init__(self, use_ml: bool | None = None):
        """Initialize the embedding checker.

        Args:
            use_ml: Force ML mode (True) or heuristic mode (False).
                   If None, auto-detect based on availability.
        """
        if use_ml is None:
            self.use_ml = embedding_available()
        else:
            self.use_ml = use_ml and embedding_available()

    @classmethod
    def _get_model(cls) -> "SentenceTransformer | None":
        """Get or load the embedding model (lazy singleton)."""
        if not cls._model_loaded:
            if embedding_available():
                try:
                    from sentence_transformers import SentenceTransformer
                    cls._model = SentenceTransformer(cls.MODEL_NAME)
                except Exception:
                    cls._model = None
            cls._model_loaded = True
        return cls._model

    # -------------------------------------------------------------------------
    # Public Check Methods
    # -------------------------------------------------------------------------

    def check_semantic_alignment(
        self,
        rule: Rule,
        source_text: str | None = None,
    ) -> ConsistencyEvidence:
        """Check semantic similarity between rule logic and source.

        Compares the rule's description, decision results, and interpretation
        notes against the source text to measure semantic alignment.
        """
        if not source_text:
            return self._make_evidence(
                category="semantic_alignment",
                label="warning",
                score=0.5,
                details="No source text provided for semantic analysis",
            )

        # Extract text from rule
        rule_text = self._extract_rule_text(rule)
        if not rule_text:
            return self._make_evidence(
                category="semantic_alignment",
                label="warning",
                score=0.5,
                details="No text extracted from rule for semantic analysis",
            )

        # Compute similarity
        result = self._compute_similarity(rule_text, source_text)

        # Map to evidence label
        if result.score >= self.HIGH_THRESHOLD:
            label = "pass"
        elif result.score >= self.MEDIUM_THRESHOLD:
            label = "warning"
        else:
            label = "fail"

        return self._make_evidence(
            category="semantic_alignment",
            label=label,
            score=result.score,
            details=result.details,
            source_span=self._get_best_matching_span(result),
            rule_element="description, decision_tree",
        )

    def check_obligation_similarity(
        self,
        rule: Rule,
        source_text: str | None = None,
    ) -> ConsistencyEvidence:
        """Check rule obligations match source requirements.

        Extracts obligation-related sentences from source (those with
        deontic markers) and compares against rule decision outcomes.
        """
        if not source_text:
            return self._make_evidence(
                category="obligation_similarity",
                label="warning",
                score=0.5,
                details="No source text provided for obligation analysis",
            )

        # Extract deontic sentences from source
        deontic_sentences = self._extract_deontic_sentences(source_text)
        if not deontic_sentences:
            return self._make_evidence(
                category="obligation_similarity",
                label="pass",
                score=0.9,
                details="No deontic obligations found in source text",
            )

        # Extract obligations from rule
        rule_obligations = self._extract_rule_obligations(rule)
        if not rule_obligations:
            return self._make_evidence(
                category="obligation_similarity",
                label="warning",
                score=0.5,
                details="No obligations found in rule to compare",
            )

        # Compute pairwise similarities
        source_combined = " ".join(deontic_sentences)
        rule_combined = " ".join(rule_obligations)

        result = self._compute_similarity(rule_combined, source_combined)

        # Map to evidence label
        if result.score >= self.HIGH_THRESHOLD:
            label = "pass"
        elif result.score >= self.MEDIUM_THRESHOLD:
            label = "warning"
        else:
            label = "fail"

        return self._make_evidence(
            category="obligation_similarity",
            label=label,
            score=result.score,
            details=f"Obligation match: {result.details}",
            source_span=deontic_sentences[0] if deontic_sentences else None,
            rule_element="decision_tree.obligations",
        )

    def check_condition_grounding(
        self,
        rule: Rule,
        source_text: str | None = None,
    ) -> ConsistencyEvidence:
        """Check conditions are grounded in source text.

        Verifies that the fields and values used in rule conditions
        have semantic grounding in the source regulatory text.
        """
        if not source_text:
            return self._make_evidence(
                category="condition_grounding",
                label="warning",
                score=0.5,
                details="No source text provided for condition grounding",
            )

        # Extract conditions from rule
        conditions = self._extract_conditions(rule)
        if not conditions:
            return self._make_evidence(
                category="condition_grounding",
                label="pass",
                score=1.0,
                details="No conditions in rule to ground",
            )

        # Check each condition for grounding
        grounded = 0
        ungrounded = []
        matched_segments = []

        for condition_text in conditions:
            result = self._compute_similarity(condition_text, source_text)
            if result.score >= self.MEDIUM_THRESHOLD:
                grounded += 1
                if result.matched_segments:
                    matched_segments.extend(result.matched_segments[:1])
            else:
                ungrounded.append(condition_text)

        grounding_ratio = grounded / len(conditions) if conditions else 0

        if grounding_ratio >= 0.8:
            label = "pass"
            score = grounding_ratio
        elif grounding_ratio >= 0.5:
            label = "warning"
            score = grounding_ratio
        else:
            label = "fail"
            score = grounding_ratio

        details = f"Condition grounding: {grounded}/{len(conditions)} conditions grounded"
        if ungrounded:
            details += f". Ungrounded: {', '.join(ungrounded[:3])}"

        return self._make_evidence(
            category="condition_grounding",
            label=label,
            score=score,
            details=details,
            rule_element="applies_if",
        )

    # -------------------------------------------------------------------------
    # Similarity Computation
    # -------------------------------------------------------------------------

    def _compute_similarity(
        self,
        text1: str,
        text2: str,
    ) -> SimilarityResult:
        """Compute similarity between two texts."""
        if self.use_ml:
            return self._compute_ml_similarity(text1, text2)
        else:
            return self._compute_heuristic_similarity(text1, text2)

    def _compute_ml_similarity(
        self,
        text1: str,
        text2: str,
    ) -> SimilarityResult:
        """Compute similarity using sentence-transformers."""
        model = self._get_model()
        if model is None:
            return self._compute_heuristic_similarity(text1, text2)

        try:
            # Encode texts
            embeddings = model.encode([text1, text2], convert_to_numpy=True)
            emb1, emb2 = embeddings[0], embeddings[1]

            # Cosine similarity
            score = float(self._cosine_similarity(emb1, emb2))

            # Determine label
            if score >= self.HIGH_THRESHOLD:
                label = "high"
            elif score >= self.MEDIUM_THRESHOLD:
                label = "medium"
            else:
                label = "low"

            return SimilarityResult(
                label=label,
                score=score,
                details=f"ML embedding similarity: {score:.3f}",
                matched_segments=[(text1[:100], text2[:100], score)],
            )
        except Exception as e:
            # Fall back to heuristics on error
            return self._compute_heuristic_similarity(text1, text2)

    def _compute_heuristic_similarity(
        self,
        text1: str,
        text2: str,
    ) -> SimilarityResult:
        """Compute similarity using heuristics (fallback)."""
        # Tokenize
        tokens1 = self._tokenize(text1)
        tokens2 = self._tokenize(text2)

        if not tokens1 or not tokens2:
            return SimilarityResult(
                label="low",
                score=0.0,
                details="Unable to tokenize texts for comparison",
            )

        # 1. TF-IDF weighted keyword overlap
        tfidf_score = self._tfidf_overlap(tokens1, tokens2)

        # 2. N-gram matching (2-grams and 3-grams)
        ngram_score = self._ngram_similarity(text1, text2)

        # 3. Jaccard similarity
        jaccard_score = self._jaccard_similarity(tokens1, tokens2)

        # Weighted combination
        score = 0.4 * tfidf_score + 0.35 * ngram_score + 0.25 * jaccard_score

        if score >= self.HIGH_THRESHOLD:
            label = "high"
        elif score >= self.MEDIUM_THRESHOLD:
            label = "medium"
        else:
            label = "low"

        return SimilarityResult(
            label=label,
            score=score,
            details=f"Heuristic similarity: {score:.3f} (tfidf={tfidf_score:.2f}, ngram={ngram_score:.2f}, jaccard={jaccard_score:.2f})",
            matched_segments=[],
        )

    # -------------------------------------------------------------------------
    # Heuristic Methods
    # -------------------------------------------------------------------------

    def _tokenize(self, text: str) -> list[str]:
        """Tokenize text into lowercase words."""
        return re.findall(r"\b[a-zA-Z]{2,}\b", text.lower())

    def _tfidf_overlap(self, tokens1: list[str], tokens2: list[str]) -> float:
        """Compute TF-IDF weighted keyword overlap."""
        # Build document frequency
        all_tokens = set(tokens1) | set(tokens2)
        if not all_tokens:
            return 0.0

        # Simple IDF: common words get lower weight
        tf1 = {t: tokens1.count(t) for t in set(tokens1)}
        tf2 = {t: tokens2.count(t) for t in set(tokens2)}

        # Count documents containing each term
        df = {}
        for t in all_tokens:
            df[t] = (1 if t in tf1 else 0) + (1 if t in tf2 else 0)

        # IDF with smoothing
        num_docs = 2
        idf = {t: math.log((num_docs + 1) / (df[t] + 1)) + 1 for t in all_tokens}

        # TF-IDF vectors
        vec1 = [tf1.get(t, 0) * idf[t] for t in all_tokens]
        vec2 = [tf2.get(t, 0) * idf[t] for t in all_tokens]

        # Cosine similarity
        return self._cosine_similarity(vec1, vec2)

    def _ngram_similarity(self, text1: str, text2: str, n_values: list[int] = [2, 3]) -> float:
        """Compute character n-gram similarity."""
        text1_lower = text1.lower()
        text2_lower = text2.lower()

        total_score = 0.0
        for n in n_values:
            ngrams1 = set(text1_lower[i:i+n] for i in range(len(text1_lower) - n + 1))
            ngrams2 = set(text2_lower[i:i+n] for i in range(len(text2_lower) - n + 1))

            if ngrams1 and ngrams2:
                intersection = ngrams1 & ngrams2
                union = ngrams1 | ngrams2
                total_score += len(intersection) / len(union)

        return total_score / len(n_values) if n_values else 0.0

    def _jaccard_similarity(self, tokens1: list[str], tokens2: list[str]) -> float:
        """Compute Jaccard similarity between token sets."""
        set1 = set(tokens1)
        set2 = set(tokens2)
        if not set1 and not set2:
            return 0.0
        intersection = set1 & set2
        union = set1 | set2
        return len(intersection) / len(union)

    @staticmethod
    def _cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
        """Compute cosine similarity between two vectors."""
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot_product / (norm1 * norm2)

    # -------------------------------------------------------------------------
    # Text Extraction
    # -------------------------------------------------------------------------

    def _extract_rule_text(self, rule: Rule) -> str:
        """Extract combined text from rule for embedding."""
        parts = []

        if rule.description:
            parts.append(rule.description)

        # Extract decision tree results
        results = self._extract_decision_results(rule)
        parts.extend(results)

        if rule.interpretation_notes:
            parts.append(rule.interpretation_notes)

        return " ".join(parts)

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

    def _extract_deontic_sentences(self, text: str) -> list[str]:
        """Extract sentences containing deontic markers."""
        deontic_pattern = re.compile(
            r"(shall|must|may|required|permitted|obliged|prohibited|forbidden)",
            re.IGNORECASE
        )

        # Split into sentences
        sentences = re.split(r"[.!?]\s+", text)
        deontic_sentences = [s.strip() for s in sentences if deontic_pattern.search(s)]

        return deontic_sentences

    def _extract_rule_obligations(self, rule: Rule) -> list[str]:
        """Extract obligation texts from rule."""
        obligations = []

        # From decision tree results
        obligations.extend(self._extract_decision_results(rule))

        # From description if it contains deontic markers
        if rule.description:
            deontic_pattern = re.compile(
                r"(shall|must|required|obliged)",
                re.IGNORECASE
            )
            if deontic_pattern.search(rule.description):
                obligations.append(rule.description)

        return obligations

    def _extract_conditions(self, rule: Rule) -> list[str]:
        """Extract condition texts from rule."""
        conditions = []

        def extract_from_spec(cond) -> list[str]:
            texts = []
            if hasattr(cond, "field") and hasattr(cond, "value"):
                field = cond.field
                op = getattr(cond, "operator", "==")
                value = cond.value
                texts.append(f"{field} {op} {value}")
            if hasattr(cond, "all") and cond.all:
                for c in cond.all:
                    texts.extend(extract_from_spec(c))
            if hasattr(cond, "any") and cond.any:
                for c in cond.any:
                    texts.extend(extract_from_spec(c))
            return texts

        if rule.applies_if:
            conditions.extend(extract_from_spec(rule.applies_if))

        # Also extract from decision tree conditions
        def extract_from_tree(node):
            if node is None:
                return
            if hasattr(node, "condition") and node.condition:
                conditions.extend(extract_from_spec(node.condition))
            if hasattr(node, "true_branch"):
                extract_from_tree(node.true_branch)
            if hasattr(node, "false_branch"):
                extract_from_tree(node.false_branch)

        if rule.decision_tree:
            extract_from_tree(rule.decision_tree)

        return conditions

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
        """Create a Tier 2 ConsistencyEvidence record."""
        return ConsistencyEvidence(
            tier=2,
            category=category,
            label=label,
            score=score,
            details=details,
            source_span=source_span,
            rule_element=rule_element,
            timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        )

    def _get_best_matching_span(self, result: SimilarityResult, max_len: int = 100) -> str | None:
        """Get the best matching source span from result."""
        if not result.matched_segments:
            return None
        # Return source segment from first match
        _, source_seg, _ = result.matched_segments[0]
        return source_seg[:max_len] if source_seg else None


# =============================================================================
# Module-Level Convenience Functions
# =============================================================================

_default_checker: EmbeddingChecker | None = None


def _get_checker() -> EmbeddingChecker:
    """Get or create default embedding checker."""
    global _default_checker
    if _default_checker is None:
        _default_checker = EmbeddingChecker()
    return _default_checker


def check_semantic_alignment(
    rule: Rule,
    source_text: str | None = None,
) -> ConsistencyEvidence:
    """Check semantic similarity between rule logic and source.

    Module-level convenience function using default checker.
    """
    return _get_checker().check_semantic_alignment(rule, source_text)


def check_obligation_similarity(
    rule: Rule,
    source_text: str | None = None,
) -> ConsistencyEvidence:
    """Check rule obligations match source requirements.

    Module-level convenience function using default checker.
    """
    return _get_checker().check_obligation_similarity(rule, source_text)


def check_condition_grounding(
    rule: Rule,
    source_text: str | None = None,
) -> ConsistencyEvidence:
    """Check conditions are grounded in source text.

    Module-level convenience function using default checker.
    """
    return _get_checker().check_condition_grounding(rule, source_text)


__all__ = [
    "EmbeddingChecker",
    "SimilarityResult",
    "embedding_available",
    "check_semantic_alignment",
    "check_obligation_similarity",
    "check_condition_grounding",
]
