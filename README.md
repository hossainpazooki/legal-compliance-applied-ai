# Droit

**Regulatory Knowledge Engineering Workbench for MiCA, RWA Tokenization, and Stablecoin Frameworks**

A computational law platform that transforms regulatory documents into executable knowledge through ontology extraction, declarative rules, and traceable decision logic.

---

## Why This Exists

Financial regulation is complex, multi-jurisdictional, and constantly evolving. Traditional compliance relies on legal memos and manual interpretation—approaches that don't scale and can't be audited systematically.

**Droit** takes a different approach: encode regulations as *executable rules* with full traceability back to source legal text. Each decision produces a machine-readable trace showing exactly which provisions applied and why. This enables:

- **Automated compliance checking** against real regulatory frameworks (MiCA, DLT Pilot, GENIUS Act)
- **Knowledge engineering workflows** for legal teams to model, verify, and maintain rules
- **Semantic consistency verification** ensuring rules faithfully represent source provisions
- **Gap analysis** identifying legal provisions without corresponding rule coverage

The system currently models the EU's Markets in Crypto-Assets Regulation (MiCA), the DLT Pilot Regime, an illustrative RWA tokenization framework, and the proposed US GENIUS Act for stablecoin oversight.

---

## Architecture

```mermaid
flowchart TB
    subgraph Corpus["Legal Corpus"]
        LC1[MiCA 2023]
        LC2[DLT Pilot 2022]
        LC3[GENIUS Act 2025]
        LC4[RWA Framework]
    end

    subgraph Core["Core Engine"]
        ONT[Ontology Layer<br/>Actor, Instrument, Activity, Provision]
        DSL[Rule DSL<br/>YAML Rulebooks]
        DE[Decision Engine<br/>Trace Generation]
        CE[Consistency Engine<br/>Tier 0-4 Verification]
    end

    subgraph RAG["Internal RAG"]
        IDX[Document Index<br/>BM25 + Optional Vectors]
        CTX[Context Retrieval<br/>Source Spans, Related Provisions]
    end

    subgraph UI["Interfaces"]
        API[FastAPI<br/>/decide, /rules, /ke/*]
        ST[Streamlit KE Workbench<br/>Decision Trees, Evidence, Review Queue]
        CH[Charts<br/>Rulebook Outline, Coverage, Ontology]
    end

    Corpus --> IDX
    IDX --> CTX
    CTX --> CE
    ONT --> DSL
    DSL --> DE
    DE --> API
    CE --> API
    API --> ST
    ST --> CH
```

### Component Summary

| Component | Purpose | Key Modules |
|-----------|---------|-------------|
| **Legal Corpus** | Normalized excerpts of source regulations | `data/legal/mica_2023/`, `genius_act_2025/`, etc. |
| **Ontology** | Typed domain model (Actor, Instrument, Activity, Provision) | `backend/ontology/`, `ocaml/core/ontology.ml` |
| **Rule DSL** | YAML-based declarative rules with decision trees | `backend/rules/`, `ocaml/core/rule_dsl.ml` |
| **Decision Engine** | Evaluates scenarios, produces traces and obligations | `backend/rules/engine.py` |
| **Consistency Engine** | Tier 0-4 verification of rules against source text | `backend/verify/consistency_engine.py` |
| **Internal RAG** | Context retrieval for KE workflows (not public Q&A) | `backend/rag/rule_context.py` |
| **KE Workbench** | Streamlit UI for rule inspection and review | `frontend/ke_dashboard.py` |
| **Charts** | Interactive tree visualizations | `backend/visualization/`, `frontend/pages/charts.py` |

---

## Key Features

- **Multi-rulebook support** — MiCA (EU crypto-assets), RWA tokenization, DLT Pilot Regime, GENIUS Act (US stablecoins)
- **Executable rules with decision traces** — Every evaluation produces a step-by-step trace linking back to source provisions
- **Tiered semantic consistency checks** — Tier 0 (schema), Tier 1 (lexical), Tier 2-4 (semantic/NLI, stub)
- **Internal RAG for legal context** — Source text retrieval, related provisions, coverage gap detection
- **KE workbench** — Decision tree viewer, evidence panel, review queue, analytics dashboard
- **Interactive charts** — Rulebook outline, ontology browser, corpus-rule links, legal corpus coverage
- **Pure Python deployment** — Runs on Streamlit Cloud without OCaml compilation

---

## Screenshots

<!-- TODO: Add actual screenshots -->
![KE Workbench - Decision Tree with Evidence Panel](docs/img/ke-workbench.png)
*Decision tree visualization with consistency overlay and rule-level evidence*

![Charts - Rulebook Outline](docs/img/rulebook-outline.png)
*Hierarchical view of legal corpus with article-level rule coverage*

---

## Getting Started

### Prerequisites

- Python 3.11+
- Git

### Installation

```bash
# Clone the repository
git clone https://github.com/hossainpazooki/RWAs.git
cd RWAs

# Create virtual environment
python -m venv .venv

# Activate (Windows PowerShell)
.\.venv\Scripts\Activate

# Activate (macOS/Linux)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Run Tests

```bash
pytest tests/ -v
```

### Launch KE Workbench

```bash
streamlit run frontend/ke_dashboard.py
```

The workbench opens at `http://localhost:8501` with:
- Rule selection and decision tree visualization
- Consistency evidence panel
- Source context and related provisions
- Charts page for rulebook/coverage analysis

### Run API Server (Optional)

```bash
uvicorn backend.api.main:app --reload
```

API available at `http://localhost:8000` with endpoints:
- `POST /decide` — Evaluate scenario against rules
- `GET /rules` — List loaded rules
- `GET /ke/*` — Internal KE endpoints

### Optional Dependencies

```bash
# ML features (vector search, semantic similarity)
pip install -r requirements-ml.txt

# Visualization enhancements
pip install -r requirements-visualization.txt
```

---

## Repository Structure

```
RWAs/
├── backend/
│   ├── ontology/          # Domain types (Actor, Instrument, Provision, etc.)
│   ├── rules/             # YAML rule files + decision engine
│   │   ├── mica_authorization.yaml
│   │   ├── mica_stablecoin.yaml
│   │   └── rwa_authorization.yaml
│   ├── verify/            # Semantic consistency engine
│   ├── analytics/         # Error patterns, drift detection
│   ├── rag/               # Internal retrieval (BM25, context)
│   ├── visualization/     # Tree adapters, chart rendering
│   └── api/               # FastAPI routes
├── frontend/
│   ├── ke_dashboard.py    # Main Streamlit app
│   └── pages/             # Charts, Review Queue
├── ocaml/
│   └── core/              # OCaml ontology + rule DSL (source of truth)
├── data/
│   └── legal/             # Legal corpus (MiCA, DLT Pilot, GENIUS)
├── docs/                  # Design documentation
├── tests/                 # Test suite (375+ tests)
└── requirements.txt
```

---

## Conceptual Layers

### Layer 1-2: Ontology & Rule DSL (OCaml + Python)

The formal type system for regulatory knowledge:

- **Ontology types**: `Actor`, `Instrument`, `Activity`, `Provision`, `Obligation`
- **Relation types**: `IMPOSES_OBLIGATION_ON`, `PERMITS`, `PROHIBITS`, `EXEMPTS`
- **Rule DSL**: YAML schema with `applies_if` conditions and `decision_tree` logic
- OCaml source in `ocaml/core/`, Python mirrors in `backend/ontology/`

### Layer 3A: Decision Engine

Deterministic rule evaluation with full traceability:

- **RuleLoader**: Parses YAML rules into executable structures
- **DecisionEngine**: Evaluates scenarios against applicable rules
- **TraceStep**: Records each condition evaluation for explainability
- See `backend/rules/engine.py`

### Layer 3B: Semantic Consistency Engine

Automated verification of rules against source legal text:

| Tier | Status | Description |
|------|--------|-------------|
| 0 | Implemented | Schema validation, required fields, date consistency |
| 1 | Implemented | Deontic alignment, keyword overlap, negation checks |
| 2 | Stub | Semantic similarity (requires sentence-transformers) |
| 3 | Stub | NLI entailment checking |
| 4 | Stub | Cross-rule consistency |

See `backend/verify/consistency_engine.py` and [Semantic Consistency Spec](docs/semantic_consistency_regulatory_kg.md).

### Layer 4: Internal RAG

Context retrieval for KE workflows (not public-facing):

- **Document indexing**: BM25 with optional vector embeddings
- **Source retrieval**: Get legal text backing a rule
- **Related provisions**: Find similar rules with structural filtering
- **Coverage gaps**: Identify legal text without mapped rules
- See `backend/rag/rule_context.py`

### Layer 5: KE Interfaces

Tools for knowledge engineers:

- **Streamlit workbench**: Decision tree viewer, evidence panel, review queue
- **Charts**: Rulebook outline, ontology browser, corpus coverage
- **FastAPI /ke endpoints**: Programmatic access to verification and analytics
- See `frontend/ke_dashboard.py`, `backend/api/routes_ke.py`

---

## Rulebooks Modeled

| Document ID | Framework | Jurisdiction | Status | Example Rules |
|-------------|-----------|--------------|--------|---------------|
| `mica_2023` | Markets in Crypto-Assets (MiCA) | EU | Modeled | `mica_art36_public_offer_authorization`, `mica_art38_reserve_assets` |
| `rwa_eu_2025` | RWA Tokenization | EU | Illustrative | `rwa_tokenization_authorization`, `rwa_custody_requirements` |
| `dlt_pilot_2022` | DLT Pilot Regime | EU | Corpus only | Future rule modeling planned |
| `genius_act_2025` | GENIUS Act (Stablecoins) | US | Illustrative | Based on proposed bill; some provisions fictionalized |

**Note**: MiCA rules are based on the published regulation. RWA and GENIUS rules are illustrative models for demonstration purposes.

---

## How to Extend

### Add a New Rulebook

1. Create legal corpus entry in `data/legal/{document_id}/`:
   - `meta.yaml` with document metadata
   - `text_normalized.txt` with normalized excerpts

2. Create rule file in `backend/rules/{document_id}.yaml`

3. Map rules to corpus via `source.document_id`

### Add Rules to Existing Rulebook

1. Edit the appropriate YAML file in `backend/rules/`
2. Follow the [Rule DSL specification](docs/rule_dsl.md)
3. Run `pytest tests/test_rules.py -v` to validate

### Modify Semantic Checks

1. Edit `backend/verify/consistency_engine.py`
2. Add new check methods following existing patterns
3. Update tests in `tests/test_consistency_engine.py`

### Documentation

- Update `docs/*.md` when changing ontology, DSL, or engine behavior
- Keep `CLAUDE.md` current for AI assistant context

---

## Status & Disclaimers

**This is a research/demo project, not legal advice.**

- Rules are interpretive models of regulatory text, not authoritative legal guidance
- The GENIUS Act rulebook is based on a proposed bill and includes fictionalized provisions
- Coverage is illustrative—not all provisions from source documents are modeled
- Always consult qualified legal counsel for compliance decisions

---

## Documentation

- [Knowledge Model](docs/knowledge_model.md) — Ontology design, type definitions, worked examples
- [Rule DSL](docs/rule_dsl.md) — YAML rule specification, operators, decision trees
- [Engine Design](docs/engine_design.md) — KE workbench architecture, layer descriptions
- [Semantic Consistency](docs/semantic_consistency_regulatory_kg.md) — Verification tiers, evidence structures

---

## License

MIT License. See [LICENSE](LICENSE) for details.

---

## Credits

Built with assistance from [Claude Code](https://claude.ai/code) (Anthropic).

Regulatory frameworks referenced:
- [MiCA - Regulation (EU) 2023/1114](https://eur-lex.europa.eu/eli/reg/2023/1114/oj)
- [DLT Pilot - Regulation (EU) 2022/858](https://eur-lex.europa.eu/eli/reg/2022/858/oj)
- [GENIUS Act - S.394 (118th Congress)](https://www.congress.gov/bill/118th-congress/senate-bill/394)
