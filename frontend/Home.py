"""
Home - Regulatory Knowledge Engineering Workbench.

Landing page with overview, instructions, and quick navigation.

Run from repo root:
    streamlit run frontend/Home.py
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd

# Backend imports for dynamic rule counts
from backend.rule_service.app.services import RuleLoader
from backend.synthetic_data.config import (
    RULE_DISTRIBUTIONS,
    JURISDICTIONS,
    TARGET_VOLUMES,
)

# -----------------------------------------------------------------------------
# Page Configuration
# -----------------------------------------------------------------------------

st.set_page_config(
    page_title="Home",
    page_icon="🏠",
    layout="wide",
)

# -----------------------------------------------------------------------------
# Header
# -----------------------------------------------------------------------------

st.title("Regulatory Knowledge Engineering Workbench")

st.markdown("""
**A Computational Law Platform for MiCA, RWA Tokenization, and Stablecoin Frameworks**

Transform regulatory documents into executable knowledge through ontology extraction,
declarative rules, and traceable decision logic.
""")

st.divider()

# -----------------------------------------------------------------------------
# Quick Navigation
# -----------------------------------------------------------------------------

st.header("Quick Navigation")

nav_col1, nav_col2, nav_col3 = st.columns(3)

with nav_col1:
    st.markdown("### KE Workbench")
    st.caption("Browse rules, visualize decision trees, run trace tests, verify consistency")
    st.page_link("pages/1_KE_Workbench.py", label="Open KE Workbench", icon="⚖️")

with nav_col2:
    st.markdown("### Production Demo")
    st.caption("Compile rules to IR, benchmark O(1) lookup, monitor cache performance")
    st.page_link("pages/2_Production_Demo.py", label="Open Production Demo", icon="🏭")

with nav_col3:
    st.markdown("### Cross-Border Navigator")
    st.caption("Multi-jurisdiction compliance, conflict detection, pathway synthesis")
    st.page_link("pages/3_Cross_Border_Navigator.py", label="Open Navigator", icon="🧭")

st.divider()

# -----------------------------------------------------------------------------
# AI Engineering Workbench
# -----------------------------------------------------------------------------

st.header("AI Engineering Workbench")

ai_col1, ai_col2, ai_col3, ai_col4 = st.columns(4)

with ai_col1:
    st.markdown("### Embedding Explorer")
    st.caption("UMAP 2D/3D visualization of rule embeddings")
    st.page_link("pages/4_Embedding_Explorer.py", label="Open", icon="🔮")

with ai_col2:
    st.markdown("### Similarity Search")
    st.caption("Find related rules using multi-type embeddings")
    st.page_link("pages/5_Similarity_Search.py", label="Open", icon="🔍")

with ai_col3:
    st.markdown("### Graph Visualizer")
    st.caption("Interactive rule structure and network graphs")
    st.page_link("pages/6_Graph_Visualizer.py", label="Open", icon="🔗")

with ai_col4:
    st.markdown("### Analytics Dashboard")
    st.caption("Clustering, coverage analysis, conflict detection")
    st.page_link("pages/7_Analytics_Dashboard.py", label="Open", icon="📊")

st.divider()

# -----------------------------------------------------------------------------
# System Overview
# -----------------------------------------------------------------------------

st.header("System Overview")

st.markdown("""
This system encodes financial regulations as **executable rules** with full traceability to source legal text.

| Capability | Description |
|------------|-------------|
| **Automated Compliance** | Check scenarios against MiCA, GENIUS Act, and other frameworks |
| **Decision Tracing** | Every decision shows which provisions applied and why |
| **Semantic Verification** | Ensure rules faithfully represent source provisions |
| **Gap Analysis** | Identify legal provisions without rule coverage |
""")

st.divider()

# -----------------------------------------------------------------------------
# Regulatory Frameworks
# -----------------------------------------------------------------------------

st.header("Regulatory Frameworks Modeled")

# Load actual rules to get dynamic counts
@st.cache_resource
def load_rule_counts() -> dict[str, int]:
    """Load rules and count by framework."""
    loader = RuleLoader()
    rules_dir = Path(__file__).parent.parent / "backend" / "rule_service" / "data"
    try:
        loader.load_directory(rules_dir)
    except FileNotFoundError:
        pass

    counts = {"mica": 0, "fca": 0, "genius": 0, "finma": 0, "mas": 0, "rwa": 0}
    for rule in loader.get_all_rules():
        rule_id = rule.rule_id.lower()
        if rule_id.startswith("mica_"):
            counts["mica"] += 1
        elif rule_id.startswith("fca_"):
            counts["fca"] += 1
        elif rule_id.startswith("genius_"):
            counts["genius"] += 1
        elif rule_id.startswith("finma_"):
            counts["finma"] += 1
        elif rule_id.startswith("mas_"):
            counts["mas"] += 1
        elif rule_id.startswith("rwa_"):
            counts["rwa"] += 1
    return counts

rule_counts = load_rule_counts()
total_rules = sum(rule_counts.values())

# Framework summary metrics
fw_col1, fw_col2, fw_col3, fw_col4 = st.columns(4)
with fw_col1:
    st.metric("Total Rules", total_rules)
with fw_col2:
    st.metric("Jurisdictions", len(JURISDICTIONS))
with fw_col3:
    st.metric("Test Scenarios", TARGET_VOLUMES["scenarios"])
with fw_col4:
    st.metric("Frameworks", len(RULE_DISTRIBUTIONS))

st.divider()

# Framework details table
framework_data = [
    {
        "Framework": "MiCA (EU)",
        "Document ID": "mica_2023",
        "Rules": f"{rule_counts['mica']} rules",
        "Coverage": "Public offers, ARTs, EMTs, CASPs, Market abuse",
        "Accuracy": "High (enacted law)",
        "Status": "Active",
    },
    {
        "Framework": "FCA Crypto (UK)",
        "Document ID": "fca_crypto_2024",
        "Rules": f"{rule_counts['fca']} rules",
        "Coverage": "Financial promotions, risk warnings, cooling-off",
        "Accuracy": "High (enacted rules)",
        "Status": "Active",
    },
    {
        "Framework": "GENIUS Act (US)",
        "Document ID": "genius_act_2025",
        "Rules": f"{rule_counts['genius']} rules",
        "Coverage": "Stablecoin issuers, reserves, redemption, AML",
        "Accuracy": "High (enacted law)",
        "Status": "Active",
    },
    {
        "Framework": "FINMA DLT (CH)",
        "Document ID": "finma_dlt_2021",
        "Rules": f"{rule_counts['finma']} rules",
        "Coverage": "Token classification, DLT facilities, custody, AML",
        "Accuracy": "High (enacted law)",
        "Status": "Active",
    },
    {
        "Framework": "MAS PSA (SG)",
        "Document ID": "mas_psa_2019",
        "Rules": f"{rule_counts['mas']} rules",
        "Coverage": "DPT licensing, custody, stablecoin framework",
        "Accuracy": "High (enacted law)",
        "Status": "Active",
    },
    {
        "Framework": "RWA Tokenization",
        "Document ID": "rwa_eu_2025",
        "Rules": f"{rule_counts['rwa']} rules",
        "Coverage": "Authorization, custody, disclosure",
        "Accuracy": "Low (hypothetical)",
        "Status": "Illustrative",
    },
]

st.dataframe(pd.DataFrame(framework_data), use_container_width=True, hide_index=True)

st.divider()

# -----------------------------------------------------------------------------
# Getting Started
# -----------------------------------------------------------------------------

st.header("Getting Started")

st.markdown("""
1. **Start the API server:** `uvicorn backend.main:app --reload`
2. **Open KE Workbench** to browse rules and run compliance checks
3. **Use AI Workbench** for embedding analysis and similarity search
""")

st.divider()

# -----------------------------------------------------------------------------
# Footer
# -----------------------------------------------------------------------------

st.caption("""
**Resources:** [docs/rule_dsl.md](docs/rule_dsl.md) | [docs/knowledge_model.md](docs/knowledge_model.md) | API at `/docs`

*Research/demo project - not legal advice. Consult qualified legal counsel for compliance decisions.*
""")
