"""Tier 4: Cross-Rule Consistency Checking.

Provides multi-rule coherence verification including:
- Contradiction detection between rule outcomes
- Hierarchy consistency (lex specialis - more specific rules take precedence)
- Temporal consistency (no conflicting rules active in same period)

All checks are deterministic (no ML required).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.rules import (
        Rule,
        DecisionNode,
        DecisionLeaf,
        ConditionSpec,
        ConditionGroupSpec,
    )

from backend.rules import ConsistencyEvidence


# =============================================================================
# Result Dataclasses
# =============================================================================


@dataclass
class ContradictionResult:
    """Result of contradiction detection between rules."""

    has_contradiction: bool
    contradicting_rule_ids: list[str] = field(default_factory=list)
    contradiction_pairs: list[dict] = field(default_factory=list)
    severity: str = "none"  # "none", "low", "medium", "high"
    details: str = ""


@dataclass
class HierarchyResult:
    """Result of hierarchy (lex specialis) consistency check."""

    is_consistent: bool
    violations: list[dict] = field(default_factory=list)
    specificity_scores: dict[str, int] = field(default_factory=dict)
    details: str = ""


@dataclass
class TemporalResult:
    """Result of temporal consistency check."""

    is_consistent: bool
    overlapping_conflicts: list[dict] = field(default_factory=list)
    timeline_gaps: list[dict] = field(default_factory=list)
    details: str = ""


# =============================================================================
# Cross-Rule Checker
# =============================================================================


class CrossRuleChecker:
    """Multi-rule coherence checking with 3 sub-checks.

    Checks:
    1. no_contradiction - No conflicting outcomes between rules
    2. hierarchy_consistent - Lex specialis respected (specific > general)
    3. temporal_consistent - No date conflicts between active rules

    Weight: 0.7 (structural analysis without source text comparison)
    """

    # Pairs of contradicting outcomes (symmetric)
    CONTRADICTING_OUTCOMES: set[tuple[str, str]] = {
        ("permitted", "prohibited"),
        ("required", "forbidden"),
        ("authorized", "denied"),
        ("compliant", "non_compliant"),
        ("exempt", "subject_to"),
        ("allowed", "forbidden"),
        ("mandatory", "optional"),
    }

    # Unbounded date sentinels
    MIN_DATE = date(1900, 1, 1)
    MAX_DATE = date(2999, 12, 31)

    def __init__(self, related_rules: list["Rule"] | None = None):
        """Initialize checker with related rules for comparison.

        Args:
            related_rules: Other rules to check against. If None, checks
                will be limited or skip comparison.
        """
        self.related_rules = related_rules or []

    def check_all(self, rule: "Rule") -> list[ConsistencyEvidence]:
        """Run all cross-rule consistency checks.

        Args:
            rule: The primary rule to verify.

        Returns:
            List of 3 ConsistencyEvidence items (contradiction, hierarchy, temporal).
        """
        return [
            self.check_contradiction(rule),
            self.check_hierarchy(rule),
            self.check_temporal_consistency(rule),
        ]

    def check_contradiction(self, rule: "Rule") -> ConsistencyEvidence:
        """Check for contradicting outcomes between rules.

        Detects when two rules with overlapping conditions produce
        mutually exclusive outcomes (e.g., "permitted" vs "prohibited").

        Args:
            rule: The primary rule to check.

        Returns:
            ConsistencyEvidence for the no_contradiction check.
        """
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        if not self.related_rules:
            return ConsistencyEvidence(
                tier=4,
                category="no_contradiction",
                label="pass",
                score=1.0,
                details="No related rules provided for comparison.",
                timestamp=timestamp,
            )

        # Extract outcomes from primary rule
        primary_outcomes = self._extract_outcomes(rule)

        contradictions: list[dict] = []
        contradicting_ids: list[str] = []

        for other in self.related_rules:
            # Skip self-comparison
            if other.rule_id == rule.rule_id:
                continue

            other_outcomes = self._extract_outcomes(other)

            # Check each outcome pair
            for p_outcome in primary_outcomes:
                for o_outcome in other_outcomes:
                    if self._are_contradicting(p_outcome, o_outcome):
                        # Check condition overlap
                        conditions_overlap = self._conditions_overlap(rule, other)

                        contradictions.append({
                            "rule1_id": rule.rule_id,
                            "rule1_outcome": p_outcome,
                            "rule2_id": other.rule_id,
                            "rule2_outcome": o_outcome,
                            "conditions_overlap": conditions_overlap,
                        })

                        if other.rule_id not in contradicting_ids:
                            contradicting_ids.append(other.rule_id)

        result = ContradictionResult(
            has_contradiction=len(contradictions) > 0,
            contradicting_rule_ids=contradicting_ids,
            contradiction_pairs=contradictions,
        )

        # Determine severity and label
        if not contradictions:
            result.severity = "none"
            result.details = "No contradicting outcomes found with related rules."
            label = "pass"
            score = 1.0
        else:
            # Check if any contradictions have overlapping conditions (high severity)
            has_overlap = any(c["conditions_overlap"] for c in contradictions)

            if has_overlap:
                result.severity = "high"
                result.details = (
                    f"Found {len(contradictions)} contradiction(s) with overlapping conditions. "
                    f"Conflicting rules: {', '.join(contradicting_ids)}."
                )
                label = "fail"
                score = 0.2
            else:
                result.severity = "low"
                result.details = (
                    f"Found {len(contradictions)} potential contradiction(s) but conditions appear disjoint. "
                    f"Rules: {', '.join(contradicting_ids)}."
                )
                label = "warning"
                score = 0.7

        return ConsistencyEvidence(
            tier=4,
            category="no_contradiction",
            label=label,
            score=score,
            details=result.details,
            rule_element="decision_tree",
            timestamp=timestamp,
        )

    def check_hierarchy(self, rule: "Rule") -> ConsistencyEvidence:
        """Check lex specialis hierarchy consistency.

        More specific rules should take precedence over general rules.
        Flags when rules with different specificity levels have conflicting outcomes.

        Args:
            rule: The primary rule to check.

        Returns:
            ConsistencyEvidence for the hierarchy_consistent check.
        """
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        if not self.related_rules:
            return ConsistencyEvidence(
                tier=4,
                category="hierarchy_consistent",
                label="pass",
                score=1.0,
                details="No related rules provided for hierarchy comparison.",
                timestamp=timestamp,
            )

        primary_specificity = self._calculate_specificity(rule)
        primary_outcomes = self._extract_outcomes(rule)

        violations: list[dict] = []
        specificity_scores: dict[str, int] = {rule.rule_id: primary_specificity}

        for other in self.related_rules:
            if other.rule_id == rule.rule_id:
                continue

            other_specificity = self._calculate_specificity(other)
            specificity_scores[other.rule_id] = other_specificity
            other_outcomes = self._extract_outcomes(other)

            # Check for conflicting outcomes
            has_conflict = False
            for p_outcome in primary_outcomes:
                for o_outcome in other_outcomes:
                    if self._are_contradicting(p_outcome, o_outcome):
                        has_conflict = True
                        break
                if has_conflict:
                    break

            if has_conflict and primary_specificity != other_specificity:
                # Record which rule is more specific
                more_specific = (
                    rule.rule_id if primary_specificity > other_specificity
                    else other.rule_id
                )
                less_specific = (
                    other.rule_id if primary_specificity > other_specificity
                    else rule.rule_id
                )

                violations.append({
                    "more_specific_rule": more_specific,
                    "less_specific_rule": less_specific,
                    "more_specific_score": max(primary_specificity, other_specificity),
                    "less_specific_score": min(primary_specificity, other_specificity),
                    "note": "More specific rule should take precedence per lex specialis.",
                })

        result = HierarchyResult(
            is_consistent=len(violations) == 0,
            violations=violations,
            specificity_scores=specificity_scores,
        )

        if not violations:
            result.details = (
                f"Rule specificity score: {primary_specificity}. "
                "No lex specialis violations found."
            )
            return ConsistencyEvidence(
                tier=4,
                category="hierarchy_consistent",
                label="pass",
                score=1.0,
                details=result.details,
                rule_element="applies_if,decision_tree",
                timestamp=timestamp,
            )
        else:
            result.details = (
                f"Found {len(violations)} hierarchy violation(s). "
                f"Rule specificity: {primary_specificity}. "
                "Consider ordering rules to ensure more specific rules take precedence."
            )
            return ConsistencyEvidence(
                tier=4,
                category="hierarchy_consistent",
                label="warning",
                score=0.6,
                details=result.details,
                rule_element="applies_if,decision_tree",
                timestamp=timestamp,
            )

    def check_temporal_consistency(self, rule: "Rule") -> ConsistencyEvidence:
        """Check for temporal conflicts between rule validity periods.

        Flags when rules with conflicting outcomes are both active
        during overlapping time periods.

        Args:
            rule: The primary rule to check.

        Returns:
            ConsistencyEvidence for the temporal_consistent check.
        """
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        if not self.related_rules:
            return ConsistencyEvidence(
                tier=4,
                category="temporal_consistent",
                label="pass",
                score=1.0,
                details="No related rules provided for temporal comparison.",
                timestamp=timestamp,
            )

        primary_outcomes = self._extract_outcomes(rule)
        overlapping_conflicts: list[dict] = []

        for other in self.related_rules:
            if other.rule_id == rule.rule_id:
                continue

            other_outcomes = self._extract_outcomes(other)

            # Check for conflicting outcomes first
            has_conflict = False
            for p_outcome in primary_outcomes:
                for o_outcome in other_outcomes:
                    if self._are_contradicting(p_outcome, o_outcome):
                        has_conflict = True
                        break
                if has_conflict:
                    break

            if not has_conflict:
                continue

            # Check temporal overlap
            overlaps, overlap_start, overlap_end = self._periods_overlap(
                rule.effective_from,
                rule.effective_to,
                other.effective_from,
                other.effective_to,
            )

            if overlaps:
                overlapping_conflicts.append({
                    "rule1_id": rule.rule_id,
                    "rule2_id": other.rule_id,
                    "overlap_start": overlap_start.isoformat() if overlap_start else None,
                    "overlap_end": overlap_end.isoformat() if overlap_end else None,
                    "note": "Conflicting rules are active during the same period.",
                })

        result = TemporalResult(
            is_consistent=len(overlapping_conflicts) == 0,
            overlapping_conflicts=overlapping_conflicts,
        )

        if not overlapping_conflicts:
            result.details = (
                f"Rule validity: {rule.effective_from or 'unbounded'} to "
                f"{rule.effective_to or 'unbounded'}. No temporal conflicts found."
            )
            return ConsistencyEvidence(
                tier=4,
                category="temporal_consistent",
                label="pass",
                score=1.0,
                details=result.details,
                rule_element="effective_from,effective_to",
                timestamp=timestamp,
            )
        else:
            conflict_ids = [c["rule2_id"] for c in overlapping_conflicts]
            result.details = (
                f"Found {len(overlapping_conflicts)} temporal conflict(s). "
                f"Conflicting rules active in same period: {', '.join(conflict_ids)}."
            )
            return ConsistencyEvidence(
                tier=4,
                category="temporal_consistent",
                label="warning",
                score=0.5,
                details=result.details,
                rule_element="effective_from,effective_to",
                timestamp=timestamp,
            )

    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------

    def _extract_outcomes(self, rule: "Rule") -> list[str]:
        """Extract all possible outcomes from a rule's decision tree.

        Traverses the decision tree to collect all result values from
        DecisionLeaf nodes.

        Args:
            rule: The rule to extract outcomes from.

        Returns:
            List of outcome strings (e.g., ["permitted", "prohibited"]).
        """
        outcomes: list[str] = []

        if rule.decision_tree is None:
            return outcomes

        def traverse(node: "DecisionNode | DecisionLeaf") -> None:
            # Import here to avoid circular imports
            from backend.rules import DecisionLeaf, DecisionNode

            if isinstance(node, DecisionLeaf):
                if node.result:
                    # Normalize to lowercase for comparison
                    outcomes.append(node.result.lower().strip())
            elif isinstance(node, DecisionNode):
                if node.true_branch:
                    traverse(node.true_branch)
                if node.false_branch:
                    traverse(node.false_branch)

        traverse(rule.decision_tree)
        return outcomes

    def _are_contradicting(self, outcome1: str, outcome2: str) -> bool:
        """Check if two outcomes are contradicting.

        Args:
            outcome1: First outcome string (lowercase).
            outcome2: Second outcome string (lowercase).

        Returns:
            True if outcomes are in CONTRADICTING_OUTCOMES set.
        """
        # Check both orderings since set contains tuples
        pair1 = (outcome1, outcome2)
        pair2 = (outcome2, outcome1)

        return pair1 in self.CONTRADICTING_OUTCOMES or pair2 in self.CONTRADICTING_OUTCOMES

    def _conditions_overlap(self, rule1: "Rule", rule2: "Rule") -> bool:
        """Heuristically check if two rules' conditions could overlap.

        This is a conservative check - returns True if conditions might
        trigger for the same scenario.

        Args:
            rule1: First rule.
            rule2: Second rule.

        Returns:
            True if conditions appear to overlap.
        """
        # If either rule has no applicability conditions, it applies broadly
        if rule1.applies_if is None or rule2.applies_if is None:
            return True

        # Extract field names from conditions
        fields1 = self._extract_condition_fields(rule1.applies_if)
        fields2 = self._extract_condition_fields(rule2.applies_if)

        # If they test different fields entirely, likely disjoint
        if fields1 and fields2 and not fields1.intersection(fields2):
            return False

        # Conservative: assume overlap if we can't prove disjoint
        return True

    def _extract_condition_fields(
        self, condition: "ConditionSpec | ConditionGroupSpec"
    ) -> set[str]:
        """Extract all field names from a condition or condition group.

        Args:
            condition: A ConditionSpec or ConditionGroupSpec.

        Returns:
            Set of field names referenced in the conditions.
        """
        from backend.rules import ConditionSpec, ConditionGroupSpec

        fields: set[str] = set()

        if isinstance(condition, ConditionSpec):
            if condition.field:
                fields.add(condition.field)
        elif isinstance(condition, ConditionGroupSpec):
            items = []
            if condition.all:
                items.extend(condition.all)
            if condition.any:
                items.extend(condition.any)

            for item in items:
                fields.update(self._extract_condition_fields(item))

        return fields

    def _calculate_specificity(self, rule: "Rule") -> int:
        """Calculate the specificity score for a rule.

        More specific rules have higher scores. Specificity is determined by:
        1. Number of conditions in applies_if (nested groups count each)
        2. Number of decision tree nodes (more branches = more specific)

        Args:
            rule: The rule to score.

        Returns:
            Integer specificity score (higher = more specific).
        """
        specificity = 0

        # Count conditions in applies_if
        if rule.applies_if:
            specificity += self._count_conditions(rule.applies_if)

        # Count decision tree nodes
        if rule.decision_tree:
            specificity += self._count_tree_nodes(rule.decision_tree)

        return specificity

    def _count_conditions(
        self, condition: "ConditionSpec | ConditionGroupSpec"
    ) -> int:
        """Count the number of conditions in a condition specification.

        Args:
            condition: A ConditionSpec or ConditionGroupSpec.

        Returns:
            Total count of individual conditions.
        """
        from backend.rules import ConditionSpec, ConditionGroupSpec

        if isinstance(condition, ConditionSpec):
            return 1
        elif isinstance(condition, ConditionGroupSpec):
            count = 0
            if condition.all:
                for item in condition.all:
                    count += self._count_conditions(item)
            if condition.any:
                for item in condition.any:
                    count += self._count_conditions(item)
            return count

        return 0

    def _count_tree_nodes(self, node: "DecisionNode | DecisionLeaf") -> int:
        """Count the number of nodes in a decision tree.

        Args:
            node: Root node of the tree.

        Returns:
            Total node count.
        """
        from backend.rules import DecisionLeaf, DecisionNode

        if isinstance(node, DecisionLeaf):
            return 1
        elif isinstance(node, DecisionNode):
            count = 1  # Count this node
            if node.true_branch:
                count += self._count_tree_nodes(node.true_branch)
            if node.false_branch:
                count += self._count_tree_nodes(node.false_branch)
            return count

        return 0

    def _periods_overlap(
        self,
        start1: date | None,
        end1: date | None,
        start2: date | None,
        end2: date | None,
    ) -> tuple[bool, date | None, date | None]:
        """Check if two date periods overlap.

        None dates are treated as unbounded (MIN_DATE or MAX_DATE).

        Args:
            start1: Start of first period (None = unbounded start).
            end1: End of first period (None = unbounded end).
            start2: Start of second period.
            end2: End of second period.

        Returns:
            Tuple of (overlaps, overlap_start, overlap_end).
        """
        # Normalize None to unbounded sentinels
        s1 = start1 or self.MIN_DATE
        e1 = end1 or self.MAX_DATE
        s2 = start2 or self.MIN_DATE
        e2 = end2 or self.MAX_DATE

        overlap_start = max(s1, s2)
        overlap_end = min(e1, e2)

        overlaps = overlap_start <= overlap_end

        # Return None for unbounded overlap boundaries
        return_start = overlap_start if overlaps else None
        return_end = overlap_end if overlaps else None

        return overlaps, return_start, return_end


# =============================================================================
# Module-Level Convenience Functions
# =============================================================================


def check_cross_rule_consistency(
    rule: "Rule",
    related_rules: list["Rule"] | None = None,
) -> list[ConsistencyEvidence]:
    """Check cross-rule consistency (Tier 4).

    Convenience function that runs all 3 cross-rule checks:
    - no_contradiction: Check for conflicting outcomes
    - hierarchy_consistent: Check lex specialis hierarchy
    - temporal_consistent: Check for temporal conflicts

    Args:
        rule: The primary rule to verify.
        related_rules: Other rules to compare against.

    Returns:
        List of 3 ConsistencyEvidence items.
    """
    checker = CrossRuleChecker(related_rules=related_rules)
    return checker.check_all(rule)


def check_contradiction(
    rule: "Rule",
    related_rules: list["Rule"] | None = None,
) -> ConsistencyEvidence:
    """Check for contradicting outcomes between rules.

    Args:
        rule: The primary rule to check.
        related_rules: Other rules to compare against.

    Returns:
        ConsistencyEvidence for the no_contradiction check.
    """
    checker = CrossRuleChecker(related_rules=related_rules)
    return checker.check_contradiction(rule)


def check_hierarchy(
    rule: "Rule",
    related_rules: list["Rule"] | None = None,
) -> ConsistencyEvidence:
    """Check lex specialis hierarchy consistency.

    Args:
        rule: The primary rule to check.
        related_rules: Other rules to compare against.

    Returns:
        ConsistencyEvidence for the hierarchy_consistent check.
    """
    checker = CrossRuleChecker(related_rules=related_rules)
    return checker.check_hierarchy(rule)


def check_temporal_consistency(
    rule: "Rule",
    related_rules: list["Rule"] | None = None,
) -> ConsistencyEvidence:
    """Check for temporal conflicts between rules.

    Args:
        rule: The primary rule to check.
        related_rules: Other rules to compare against.

    Returns:
        ConsistencyEvidence for the temporal_consistent check.
    """
    checker = CrossRuleChecker(related_rules=related_rules)
    return checker.check_temporal_consistency(rule)
