# Engine Design: Internal Knowledge Engineering Workbench

This document describes the architecture of the internal Knowledge Engineering (KE) workbench built on top of the Droit regulatory reasoning system.

## System Overview

The workbench provides tools for Knowledge Engineers to:
- Create and maintain regulatory rules
- Verify rule consistency against source legal text
- Monitor rule quality over time
- Prioritize rules for human review

## Architecture Layers

```
┌─────────────────────────────────────────────────────────────────┐
│                    Layer 6: KE Interfaces                       │
│      (FastAPI /ke endpoints, Streamlit dashboard, CLI tools)    │
├─────────────────────────────────────────────────────────────────┤
│                 Layer 5: Visualization (Optional)               │
│      (Supertree charts, tree adapters, HTML rendering)          │
├─────────────────────────────────────────────────────────────────┤
│                    Layer 4: Internal RAG                        │
│           (RuleContextRetriever, document indexing)             │
├─────────────────────────────────────────────────────────────────┤
│              Layer 3B: Semantic Consistency Engine              │
│     (ConsistencyEngine, Tier 0-4 verification, analytics)       │
├─────────────────────────────────────────────────────────────────┤
│              Layer 3A: Symbolic Decision Engine                 │
│          (DecisionEngine, RuleLoader, condition eval)           │
├─────────────────────────────────────────────────────────────────┤
│                Layer 2: Rule DSL (YAML + Pydantic)              │
│           (Rule, ConditionSpec, DecisionTree, etc.)             │
├─────────────────────────────────────────────────────────────────┤
│                  Layer 1: Ontology (OCaml + Python)             │
│        (Actor, Instrument, Activity, Provision, etc.)           │
└─────────────────────────────────────────────────────────────────┘
```

## Layer 3A: Symbolic Decision Engine

The decision engine evaluates rules against scenarios deterministically.

### Key Components

- **RuleLoader** ([loader.py](../backend/rules/loader.py)): Loads YAML rules, parses decision trees and conditions
- **DecisionEngine** ([engine.py](../backend/rules/engine.py)): Evaluates scenarios against rules
- **Rule Schema** ([schema.py](../backend/rules/schema.py)): Pydantic models for rule structure

### Decision Flow

```
Scenario → RuleLoader → Applicable Rules → Decision Tree Traversal → DecisionResult
```

### Output Structure

```python
class DecisionResult:
    rule_id: str
    applicable: bool
    decision: str | None
    trace: list[TraceStep]       # Decision path for explainability
    obligations: list[Obligation]
    rule_metadata: RuleMetadata  # Includes consistency status
```

## Layer 3B: Semantic Consistency Engine

Verifies that rules accurately represent source legal text.

### Components

- **ConsistencyEngine** ([consistency_engine.py](../backend/verify/consistency_engine.py)): Runs verification checks
- **ErrorPatternAnalyzer** ([error_patterns.py](../backend/analytics/error_patterns.py)): Detects systematic issues
- **DriftDetector** ([drift.py](../backend/analytics/drift.py)): Tracks quality changes over time

### Verification Tiers

| Tier | Status | Description |
|------|--------|-------------|
| 0 | Implemented | Schema validation, required fields, date consistency |
| 1 | Implemented | Deontic alignment, keyword overlap, negation consistency |
| 2 | Stub | Semantic similarity (requires sentence-transformers) |
| 3 | Stub | NLI entailment (requires NLI model) |
| 4 | Stub | Cross-rule consistency |

### Consistency Block Structure

Every rule can have a `consistency` block:

```yaml
consistency:
  summary:
    status: verified | needs_review | inconsistent | unverified
    confidence: 0.95
    last_verified: "2024-12-10T14:30:00Z"
    verified_by: system | human:username
  evidence:
    - tier: 0
      category: schema_valid
      label: pass
      score: 1.0
      details: "All required fields present"
```

### Key Design Decisions

1. **No external LLM calls**: All verification is local
2. **Deterministic base**: Tier 0-1 are rule-based, not ML-based
3. **Writeback**: Results are stored in rule YAML files
4. **Human override**: Humans can mark rules as verified regardless of automated checks

## Layer 4: Internal RAG

Provides context retrieval for rule verification - NOT for public Q&A.

### Components

- **RuleContextRetriever** ([rule_context.py](../backend/rag/rule_context.py)): Rule-specific retrieval
- **BM25Index** ([bm25.py](../backend/rag/bm25.py)): Keyword-based retrieval
- **Retriever** ([retriever.py](../backend/rag/retriever.py)): Hybrid BM25 + optional vectors

### Usage Pattern

```python
retriever = RuleContextRetriever(rule_loader=loader)
retriever.index_document("mica_2023", mica_text)

# Get source context for a rule
context = retriever.get_rule_context(rule)
source_text = retriever.get_source_text(rule)

# Pass to consistency engine
result = consistency_engine.verify_rule(rule, source_text)
```

### Capabilities

- Index legal documents by article/section
- Retrieve source passages for rules
- Find cross-references in text
- Locate related rules by source/tags

### KE Workbench UI Integration

The internal RAG layer powers several KE workbench UI features:

- **Source & Context panel**: Displays the primary text span backing a rule, with before/after context paragraphs and document/article metadata.
- **Similar / related provisions panel**: Uses structural filtering (same document_id) and similarity thresholds to show related rules without noise. Displays "no results above threshold" when appropriate.
- **Corpus search (sidebar)**: Supports dual-mode search:
  - *Article lookup mode*: Queries like "Art. 36(1)" or "Article 45" perform exact article matching against rule `source.article` fields.
  - *Semantic search mode*: Natural language queries perform BM25 retrieval, with results mapped back to rules via `(document_id, article)` matching.

**Important**: Internal RAG is NOT exposed as a public `/ask` endpoint in this repo. It is strictly for KE tooling.

### Legal Corpus Integration

The workbench includes a small embedded legal corpus for MiCA, the EU DLT Pilot Regime, and the GENIUS Act (US stablecoin framework). These are normalized excerpts, not full official texts.

#### Corpus Structure

```
data/legal/
├── mica_2023/
│   ├── meta.yaml           # Document metadata
│   └── text_normalized.txt # Normalized excerpts
├── dlt_pilot_2022/
│   ├── meta.yaml
│   └── text_normalized.txt
└── genius_act_2025/
    ├── meta.yaml
    └── text_normalized.txt
```

Each `meta.yaml` contains:
- `document_id`: Join key to rule `source.document_id`
- `title`: Human-readable document title
- `citation`: Official citation (e.g., "Regulation (EU) 2023/1114")
- `jurisdiction`: "EU" or "US"
- `source_url`: Link to official text

#### Corpus Loader

```python
from backend.rag import load_legal_document, load_all_legal_documents

# Load a specific document
doc = load_legal_document("mica_2023")
print(doc.title, doc.citation)
print(doc.find_article_text("36"))  # Get Article 36 text

# Load all documents
docs = load_all_legal_documents()
```

#### Rule-Corpus Mapping

Rules reference legal corpus via `source.document_id`:
- MiCA rules: `document_id: mica_2023`
- DLT Pilot rules: `document_id: dlt_pilot_2022`
- GENIUS rules: `document_id: genius_act_2025`

The `RuleLoader.validate_corpus_coverage()` method checks which rules have corresponding legal corpus entries.

#### Coverage Gap Detection

When searching the corpus, hits are tagged with:
- `source_type: "legal_text"` for legal corpus hits
- `has_rule_coverage: False` when a legal passage has no mapped rule

This enables gap-finding UX: show ⚠️ "no formal rule yet" for legal text passages without corresponding rules.

## Layer 5: Visualization (Optional)

Provides tree-based visualizations for regulatory charts. Gracefully degrades when Supertree is not installed.

### Components

- **supertree_adapters.py**: Pure-Python adapters that convert rules/traces into nested dict/list structures
- **supertree_utils.py**: Rendering helpers with optional Supertree dependency

### Available Charts

| Chart | Function | Description |
|-------|----------|-------------|
| Rulebook Outline | `build_rulebook_outline()` | Hierarchical view of rules by document |
| Decision Trace | `build_decision_trace_tree()` | Evaluation path through a rule |
| Ontology Browser | `build_ontology_tree()` | Actor/Instrument/Activity type hierarchy |
| Corpus Links | `build_corpus_rule_links()` | Document → Article → Rule traceability |
| Decision Tree | `build_decision_tree_structure()` | Rule's internal decision logic |

### Optional Dependency

```bash
pip install -r requirements-visualization.txt
```

When Supertree is not installed:
- `is_supertree_available()` returns `False`
- Render functions return fallback HTML with install instructions
- Data adapters work normally (no external dependencies)

### Usage Pattern

```python
from backend.visualization import (
    build_rulebook_outline,
    render_rulebook_outline_html,
    is_supertree_available,
)

# Get tree data (always works)
rules = loader.get_all_rules()
tree_data = build_rulebook_outline(rules)

# Render HTML (graceful fallback if Supertree not installed)
html = render_rulebook_outline_html(tree_data)
```

## Layer 6: KE Interfaces

### API Endpoints

The `/ke` prefix provides internal endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/ke/verify` | POST | Verify single rule |
| `/ke/verify-all` | POST | Verify all rules |
| `/ke/analytics/summary` | GET | Overall statistics |
| `/ke/analytics/patterns` | GET | Detected error patterns |
| `/ke/analytics/matrix` | GET | Category × outcome matrix |
| `/ke/analytics/review-queue` | GET | Prioritized review list |
| `/ke/drift/baseline` | POST | Set drift baseline |
| `/ke/drift/detect` | GET | Detect drift from baseline |
| `/ke/drift/history` | GET | Metrics history |
| `/ke/drift/authors` | GET | Per-author statistics |
| `/ke/context/{rule_id}` | GET | Rule source context |
| `/ke/related/{rule_id}` | GET | Related rules |
| `/ke/rules/{rule_id}/review` | POST | Submit human review |
| `/ke/rules/{rule_id}/reviews` | GET | Get review history |
| `/ke/charts/supertree-status` | GET | Check Supertree availability |
| `/ke/charts/rulebook-outline` | GET | Rulebook outline tree data |
| `/ke/charts/rulebook-outline/html` | GET | Rulebook outline as HTML |
| `/ke/charts/ontology` | GET | Ontology tree data |
| `/ke/charts/ontology/html` | GET | Ontology as HTML |
| `/ke/charts/corpus-links` | GET | Corpus-rule links tree data |
| `/ke/charts/corpus-links/html` | GET | Corpus-rule links as HTML |
| `/ke/charts/decision-tree/{rule_id}` | GET | Decision tree for a rule |
| `/ke/charts/decision-trace/{rule_id}` | POST | Evaluate and get trace tree |
| `/ke/charts/decision-trace/{rule_id}/html` | POST | Trace as HTML |

### Review Queue Priority

Rules are prioritized for review based on:
1. Consistency status (inconsistent > needs_review > unverified)
2. Confidence score (lower = higher priority)
3. Time since last verification
4. Rule importance (future: usage frequency)

## Analytics

### Error Pattern Detection

Identifies systematic issues across rules:

```python
analyzer = ErrorPatternAnalyzer(rule_loader=loader)
patterns = analyzer.detect_patterns(min_affected=2)

# Example pattern:
# {
#   "pattern_id": "high_fail_deontic_alignment",
#   "category": "deontic_alignment",
#   "severity": "high",
#   "affected_rule_count": 5,
#   "recommendation": "Review deontic verb usage vs rule modality"
# }
```

### Drift Detection

Tracks quality changes over time:

```python
detector = DriftDetector(rule_loader=loader)
detector.set_baseline()  # Capture initial state

# Later...
report = detector.detect_drift()
# report.drift_severity: "none" | "minor" | "moderate" | "major"
```

## Testing Strategy

The workbench has comprehensive test coverage:

| Test File | Coverage |
|-----------|----------|
| `test_rules_schema.py` | Consistency models, save/load |
| `test_consistency_engine.py` | Tier 0-1 checks, summary computation |
| `test_rag_internal.py` | Context retrieval, cross-references |
| `test_analytics.py` | Error patterns, drift detection |
| `test_api_ke.py` | All KE endpoints |

Run all tests:
```bash
pytest tests/ -v
```

## Future Enhancements

### Tier 2+: ML-Based Verification

When ML dependencies are available:
- Semantic similarity via sentence-transformers
- NLI-based entailment checking
- Cross-rule contradiction detection

### Confident Learning Integration

Per the spec in `semantic_consistency_regulatory_kg.md`:
- Identify likely label errors in rule annotations
- Estimate per-category noise rates
- Generate cleaned training data for ML models

### CLI Tools

Future CLI commands for KE workflows:
- `droit verify <rule_id>` - Verify single rule
- `droit verify --all` - Verify all rules
- `droit review` - Interactive review queue
- `droit drift` - Show drift report

## Integration with OCaml Core

The Python workbench reads from YAML rules that are the executable form of the OCaml type system:

```
OCaml ontology.ml  ───►  docs/ontology_design.md
        │
        ▼
OCaml rule_dsl.ml  ───►  YAML rule files  ◄───  Python loader
        │                      │
        ▼                      ▼
  docs/rule_dsl.md      Python DecisionEngine
```

The OCaml types remain the source of truth. Python mirrors them via Pydantic models but defers to OCaml for formal verification (future).
