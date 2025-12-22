README
Title + elevator pitch — "Regulatory Knowledge Engineering Workbench for MiCA, RWA Tokenization, and Stablecoin Frameworks"
Why This Exists — Computational law angle, problem statement, what the system enables
Architecture — Mermaid flowchart showing Legal Corpus → Core Engine → RAG → Interfaces, plus component summary table
Key Features — 7 bullet points covering multi-rulebook, traces, consistency, RAG, workbench, charts, pure Python
Screenshots — Placeholders for KE workbench and charts (TODO comments)
Getting Started — Clone, venv, install, test, run workbench, optional API
Repository Structure — Clean tree with one-line descriptions
Conceptual Layers — Layer 1-2 (Ontology), Layer 3A (Decision Engine), Layer 3B (Consistency), Layer 4 (RAG), Layer 5 (Interfaces)
Rulebooks Modeled — Table with document_id, framework, jurisdiction, status, examples
How to Extend — Add rulebook, add rules, modify checks, documentation
Status & Disclaimers — Research/demo, not legal advice, GENIUS fictionalized
Documentation — Links to all docs
License & Credits — MIT, Claude Code, regulatory framework references


Consistency Engine Overview
The consistency engine verifies that YAML rules accurately represent their source legal text. It's located in backend/verify/consistency_engine.py.
Purpose
Rules encode human interpretations of legal text. These can be:
Correct — Rule faithfully represents the provision
Incomplete — Rule omits conditions or exceptions
Inconsistent — Rule contradicts the source text
Ambiguous — Interpretation is defensible but not unique
The engine provides automated QA to detect issues and prioritize human review.
Verification Tiers
Tier	Status	Focus	Checks
0	Implemented	Schema & Structure	schema_valid, required_fields, source_exists, date_consistency, id_format
1	Implemented	Lexical & Heuristic	deontic_alignment, keyword_overlap, negation_consistency, actor_mentioned, instrument_mentioned
2	Stub	Semantic Similarity	Embedding-based alignment (requires sentence-transformers)
3	Stub	NLI Entailment	Source entails rule conclusion (requires NLI model)
4	Stub	Cross-Rule	No contradictions, hierarchy consistent, temporal consistent
Tier 0: Schema Validation (Deterministic)
Fast, rule-based checks run on every rule load:
Check	Description
schema_valid	Rule parses against DSL schema
required_fields	rule_id, source present
source_exists	Source document/article can be resolved
date_consistency	effective_from <= effective_to
id_format	rule_id follows naming convention
Tier 1: Lexical Analysis (Heuristics)
Surface-level text analysis without ML:
Check	Description
deontic_alignment	Deontic verbs (shall/must/may) match rule modality
keyword_overlap	Key terms from rule appear in source
negation_consistency	Negations in source reflected in rule logic
actor_mentioned	Actor types in rule appear in source text
instrument_mentioned	Instrument types in rule appear in source
Tier 2-4: ML-Based (Stubs)
Planned but not yet implemented:
Tier 2: Semantic similarity via embeddings
Tier 3: NLI entailment (source → rule conclusion)
Tier 4: Cross-rule contradiction detection
Evidence Structure
Each check produces an evidence record:
ConsistencyEvidence(
    tier=1,
    category="deontic_alignment",
    label="pass",        # pass | warning | fail
    score=0.85,          # 0.0-1.0 confidence
    details="Obligation verb 'must' found in source",
    source_span="shall make a public offer",
    rule_element="applies_if.all[0]",
    timestamp="2024-12-10T14:30:01Z"
)
Summary Computation
The overall status is computed from evidence:
if any(e.label == "fail"):
    status = "inconsistent"
elif any(e.label == "warning"):
    status = "needs_review"
elif not evidence:
    status = "unverified"
else:
    status = "verified"
Confidence is a weighted average (Tier 0-1 have higher weight since they're deterministic).
Key Design Decisions
No external LLM calls — All verification is local
Deterministic base — Tier 0-1 are rule-based, not ML
Writeback — Results stored in rule YAML files
Human override — Humans can mark rules verified regardless of automated checks
