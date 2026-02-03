# Consistency Engine Implementation Summary

This document summarizes the completed implementation of the 5-tier semantic consistency verification system for the ke-workbench regulatory rule validation framework.

## Implementation Status

| Tier | Name | Status | Module | Dependencies |
|------|------|--------|--------|--------------|
| 0 | Schema & Structural | **Implemented** | `service.py` | None (pure Python) |
| 1 | Lexical & Heuristic | **Implemented** | `service.py` | None (regex, heuristics) |
| 2 | Semantic Similarity | **Implemented** | `embeddings.py` | Optional: sentence-transformers |
| 3 | NLI Entailment | **Implemented** | `nli.py` | Optional: transformers, torch |
| 4 | Cross-Rule Consistency | **Implemented** | `cross_rule.py` | None (pure Python) |

All tiers are fully implemented with graceful fallback to heuristics when ML dependencies are unavailable.

---

## Module Structure

```
services/ke-workbench/backend/verification/
├── __init__.py          # Exports all verification components
├── service.py           # ConsistencyEngine, Tier 0-3 checks
├── embeddings.py        # Tier 2: EmbeddingChecker with ML/fallback
├── nli.py               # Tier 3: NLIChecker with ML/fallback
└── cross_rule.py        # Tier 4: CrossRuleChecker (structural analysis)
```

---

## Tier 0: Schema & Structural Validation

**Location**: `service.py` (lines 52-241)

### Checks Implemented

| Check | Function | Description |
|-------|----------|-------------|
| `schema_valid` | `check_schema_valid()` | Rule parses against DSL schema |
| `required_fields` | `check_required_fields()` | rule_id, source present |
| `source_exists` | `check_source_exists()` | Source document resolves |
| `date_consistency` | `check_date_consistency()` | effective_from <= effective_to |
| `id_format` | `check_id_format()` | rule_id follows naming convention |
| `decision_tree_valid` | `check_decision_tree_valid()` | Tree structure well-formed |

### Characteristics
- **Deterministic**: Same input always produces same output
- **Fast**: <100ms execution
- **No dependencies**: Pure Python validation
- **Weight**: 1.0 (highest trust)

---

## Tier 1: Lexical & Heuristic Analysis

**Location**: `service.py` (lines 244-603)

### Checks Implemented

| Check | Function | Description |
|-------|----------|-------------|
| `deontic_alignment` | `check_deontic_alignment()` | shall/must/may match rule modality |
| `actor_mentioned` | `check_actor_mentioned()` | Actor types in source text |
| `instrument_mentioned` | `check_instrument_mentioned()` | Instrument types in source |
| `keyword_overlap` | `check_keyword_overlap()` | Key terms from rule in source |
| `negation_consistency` | `check_negation_consistency()` | Negations reflected in rule logic |
| `exception_coverage` | `check_exception_coverage()` | Exceptions have branches |

### Characteristics
- **Surface-level**: Text pattern matching without semantic understanding
- **Regex-based**: Deontic markers, entity patterns
- **Fast**: <100ms execution
- **Weight**: 0.8

---

## Tier 2: Semantic Similarity (Embedding-based)

**Location**: `embeddings.py`

### Architecture

```python
class EmbeddingChecker:
    """Dual-mode semantic checker with ML and heuristic fallback."""

    HIGH_THRESHOLD = 0.75   # >= 0.75 -> "high" (pass)
    MEDIUM_THRESHOLD = 0.50 # >= 0.50 -> "medium" (warning)
    # < 0.50 -> "low" (fail)
```

### Checks Implemented

| Check | Method | Description |
|-------|--------|-------------|
| `semantic_alignment` | `check_semantic_alignment()` | Rule logic matches source semantically |
| `obligation_similarity` | `check_obligation_similarity()` | Rule obligations match source requirements |
| `condition_grounding` | `check_condition_grounding()` | Conditions grounded in source text |

### ML Backend (sentence-transformers)
- **Model**: `all-MiniLM-L6-v2` (384 dimensions, ~80MB)
- **Loading**: Lazy singleton pattern (load once, reuse)
- **Similarity**: Cosine similarity between embeddings
- **Performance**: First call ~1-3s (model load), subsequent ~50-150ms

### Fallback Heuristics (when ML unavailable)
- **TF-IDF weighted keyword overlap**
- **Character n-gram (2-gram, 3-gram) matching**
- **Hash-based pseudo-embeddings** (deterministic 384-dim vectors)
- **Jaccard similarity** for set comparison

### Text Extraction Pipeline

```
Rule -> [description, decision results, interpretation_notes] -> Combined text
Source -> Sentence splitting -> Deontic marker filtering -> Requirement sentences

Similarity = cosine(encode(rule_text), encode(source_text))
```

### Label Mapping
- `score >= 0.75` -> `"high"` -> `label="pass"`
- `score >= 0.50` -> `"medium"` -> `label="warning"`
- `score < 0.50` -> `"low"` -> `label="fail"`

**Weight**: 0.9

---

## Tier 3: NLI-based Entailment

**Location**: `nli.py`

### Architecture

```python
class NLIChecker:
    """NLI entailment checker with transformer/heuristic fallback."""

class NLILabel(Enum):
    ENTAILMENT = "entailment"
    NEUTRAL = "neutral"
    CONTRADICTION = "contradiction"
```

### Checks Implemented

| Check | Method | Description |
|-------|--------|-------------|
| `entailment` | `check_entailment()` | Source entails rule conclusion |
| `completeness` | `check_completeness()` | Rule covers source clauses |

### ML Backend (transformers + torch)
- **Preferred Models** (in order):
  1. `microsoft/deberta-v3-base-mnli`
  2. `roberta-large-mnli`
  3. `facebook/bart-large-mnli`
- **Loading**: Lazy singleton pattern
- **Output**: 3-class probabilities (entailment, neutral, contradiction)
- **Performance**: First call ~2-5s, subsequent ~100-300ms

### Fallback Heuristics
1. **Negation polarity detection**
   - Premise negated XOR hypothesis negated -> CONTRADICTION (0.6 confidence)
2. **Keyword overlap scoring**
   - `>70%` overlap -> ENTAILMENT (0.5-0.8 confidence)
   - `40-70%` overlap -> NEUTRAL (0.5 confidence)
   - `<40%` overlap -> NEUTRAL (0.4 confidence)

### Hypothesis Extraction Pipeline

```python
def extract_hypothesis_from_rule(rule) -> list[str]:
    hypotheses = []
    # 1. Rule description
    if rule.description:
        hypotheses.append(rule.description)
    # 2. Decision tree results -> natural language
    for result in decision_tree_results:
        hypotheses.append(result_to_hypothesis(result))
    # 3. Interpretation notes (first 2 sentences)
    if rule.interpretation_notes:
        hypotheses.extend(split_sentences(notes)[:2])
    return hypotheses
```

### Label Mapping
- `ENTAILMENT` -> `label="pass"`, `score=confidence`
- `CONTRADICTION` -> `label="fail"`, `score=1-confidence`
- `NEUTRAL` -> `label="warning"`, `score=0.5`

**Weight**: 0.95 (highest ML tier weight)

---

## Tier 4: Cross-Rule Consistency

**Location**: `cross_rule.py`

### Architecture

```python
class CrossRuleChecker:
    """Multi-rule coherence checking with 3 sub-checks."""

    CONTRADICTING_OUTCOMES = {
        ("permitted", "prohibited"),
        ("required", "forbidden"),
        ("authorized", "denied"),
        ("compliant", "non_compliant"),
        ("exempt", "subject_to"),
        ("allowed", "forbidden"),
        ("mandatory", "optional"),
    }

    MIN_DATE = date(1900, 1, 1)  # Unbounded start
    MAX_DATE = date(2999, 12, 31) # Unbounded end
```

### Checks Implemented (Returns 3 Evidence Items)

| Check | Method | Description |
|-------|--------|-------------|
| `no_contradiction` | `check_contradiction()` | No conflicting outcomes |
| `hierarchy_consistent` | `check_hierarchy()` | Lex specialis respected |
| `temporal_consistent` | `check_temporal_consistency()` | No date conflicts |

### Contradiction Detection Algorithm

```
1. Extract outcomes from both rules' decision trees
2. Compare outcome pairs against CONTRADICTING_OUTCOMES set
3. Check condition overlap (same scenario triggers both)
4. Severity assignment:
   - conditions_overlap=True  -> "high" (score=0.2)
   - conditions_overlap=False -> "low"  (score=0.7)
```

### Hierarchy Consistency (Lex Specialis)

```python
def _calculate_specificity(rule) -> int:
    specificity = 0
    # Count conditions in applies_if (nested groups count each)
    if rule.applies_if:
        specificity += count_conditions(rule.applies_if)
    # Count decision tree nodes (more branches = more specific)
    if rule.decision_tree:
        specificity += count_tree_nodes(rule.decision_tree)
    return specificity
```

- More specific rules should take precedence
- Flag when different specificity levels have conflicting outcomes

### Temporal Consistency

```python
def _periods_overlap(start1, end1, start2, end2) -> (bool, date, date):
    # None dates treated as unbounded
    s1 = start1 or MIN_DATE
    e1 = end1 or MAX_DATE
    s2 = start2 or MIN_DATE
    e2 = end2 or MAX_DATE

    overlap_start = max(s1, s2)
    overlap_end = min(e1, e2)

    return overlap_start <= overlap_end, overlap_start, overlap_end
```

- Check date range overlaps
- Flag conflicting rules active in same period

### Label Mapping
- **Contradiction**:
  - No contradiction -> `pass` (score=1.0)
  - High severity -> `fail` (score=0.2)
  - Medium severity -> `warning` (score=0.5)
  - Low severity -> `warning` (score=0.7)
- **Hierarchy**: consistent -> `pass` (1.0), else `warning` (0.6)
- **Temporal**: consistent -> `pass` (1.0), else `warning` (0.5)

**Weight**: 0.7 (structural analysis without source text comparison)

---

## Result Dataclasses

### Tier 2: Similarity Results

```python
@dataclass
class SimilarityResult:
    label: str          # "high", "medium", "low"
    score: float        # 0.0-1.0
    details: str        # Human-readable explanation
    matched_segments: list[tuple[str, str, float]]  # (rule_text, source_text, score)
```

### Tier 3: NLI Results

```python
@dataclass
class NLIResult:
    label: NLILabel         # ENTAILMENT, NEUTRAL, CONTRADICTION
    confidence: float       # 0.0-1.0
    entailment_score: float
    neutral_score: float
    contradiction_score: float
```

### Tier 4: Cross-Rule Results

```python
@dataclass
class ContradictionResult:
    has_contradiction: bool
    contradicting_rule_ids: list[str]
    contradiction_pairs: list[dict]
    severity: str  # "none", "low", "medium", "high"
    details: str

@dataclass
class HierarchyResult:
    is_consistent: bool
    violations: list[dict]
    specificity_scores: dict[str, int]
    details: str

@dataclass
class TemporalResult:
    is_consistent: bool
    overlapping_conflicts: list[dict]
    timeline_gaps: list[dict]
    details: str
```

---

## ConsistencyEngine Integration

**Location**: `service.py`

```python
class ConsistencyEngine:
    """Orchestrates all verification tiers."""

    def verify_rule(
        self,
        rule: Rule,
        source_text: str | None = None,
        tiers: list[int] = [0, 1, 2, 3, 4],
    ) -> ConsistencyBlock:
        evidence = []

        # Run tier 0 checks (always)
        evidence.extend(self._run_tier0(rule))

        # Run tier 1 checks (always, if source_text available)
        if source_text and 1 in tiers:
            evidence.extend(self._run_tier1(rule, source_text))

        # Run tier 2+ checks (on-demand)
        if 2 in tiers:
            evidence.append(check_semantic_alignment(rule, source_text))
            evidence.append(check_obligation_similarity(rule, source_text))
            evidence.append(check_condition_grounding(rule, source_text))
        if 3 in tiers:
            evidence.append(check_entailment(rule, source_text))
            evidence.append(check_completeness(rule, source_text))
        if 4 in tiers:
            evidence.extend(check_cross_rule_consistency(rule))  # Returns list[3]

        # Compute summary
        summary = compute_summary(evidence)

        return ConsistencyBlock(summary=summary, evidence=evidence)
```

---

## Test Coverage

| Test File | Coverage |
|-----------|----------|
| `tests/test_tier2_embeddings.py` | EmbeddingChecker, ML/fallback modes, all 3 checks |
| `tests/test_tier4_cross_rule.py` | CrossRuleChecker, all 3 sub-checks, helper methods |

### Key Test Scenarios

**Tier 2 Tests**:
- High similarity maps to pass
- Low similarity maps to fail
- Graceful degradation without ML dependencies
- Condition grounding ratio calculation
- Obligation matching with deontic markers

**Tier 4 Tests**:
- Contradicting outcomes detection (permitted/prohibited)
- Disjoint conditions skip contradiction check
- Self-comparison skipped
- Specificity calculation (conditions + tree depth)
- Temporal overlap detection
- Unbounded date handling (MIN_DATE/MAX_DATE)

---

## Dependency Management

### Optional Dependencies

```toml
[project.optional-dependencies]
embeddings = ["sentence-transformers>=2.2.0"]
nli = ["transformers>=4.30.0", "torch>=2.0.0"]
verification = [
    "sentence-transformers>=2.2.0",
    "transformers>=4.30.0",
    "torch>=2.0.0",
]
```

### Runtime Availability Checks

```python
from backend.verification import embedding_available, nli_available

if embedding_available():
    print("Tier 2: Using ML embeddings")
else:
    print("Tier 2: Using heuristic fallback")

if nli_available():
    print("Tier 3: Using transformer NLI")
else:
    print("Tier 3: Using heuristic fallback")
```

---

## Performance Characteristics

| Tier | Mode | Latency | Notes |
|------|------|---------|-------|
| 0 | - | <50ms | Deterministic validation |
| 1 | - | <100ms | Regex/pattern matching |
| 2 | ML | 50-150ms | After model load (~1-3s first call) |
| 2 | Heuristic | <50ms | TF-IDF + n-gram |
| 3 | ML | 100-300ms | After model load (~2-5s first call) |
| 3 | Heuristic | <50ms | Keyword overlap |
| 4 | - | 50-200ms | Depends on related rules count |

### Optimization Strategies
1. **Lazy model loading**: Models loaded on first use, singleton pattern
2. **Embedding caching**: Store embeddings for repeated rules
3. **Tier selection**: Run only necessary tiers via `tiers` parameter
4. **Batch processing**: Process multiple hypotheses in single forward pass

---

## API Usage

```python
from backend.verification import (
    ConsistencyEngine,
    check_semantic_alignment,
    check_cross_rule_consistency,
)

# Full verification
engine = ConsistencyEngine()
result = engine.verify_rule(rule, source_text, tiers=[0, 1, 2, 3, 4])
print(result.summary.status)  # "verified" | "needs_review" | "inconsistent"

# Individual checks
semantic_evidence = check_semantic_alignment(rule, source_text)
print(f"Semantic: {semantic_evidence.label} ({semantic_evidence.score:.2f})")

cross_rule_evidence = check_cross_rule_consistency(rule, related_rules=[other_rule])
for ev in cross_rule_evidence:
    print(f"{ev.category}: {ev.label}")
```

---

## References

- [Semantic Consistency Specification](../semantic_consistency_regulatory_kg.md)
- [Verification Service Plan](./verification_service.md)
- [SCRUM 22-24 Implementation Tickets](../../scrum_structure.md)