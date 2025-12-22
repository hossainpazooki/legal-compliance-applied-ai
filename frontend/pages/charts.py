"""
Charts - Interactive Tree Visualizations.

NOTE: Decision Tree and Decision Trace features are now available in the
KE Cockpit main dashboard. This page remains useful for corpus-wide
visualizations that don't fit the single-rule cockpit view.

This page provides tree visualizations for:
- Rulebook outline (rules grouped by document)
- Ontology browser (actor/instrument/activity types)
- Corpus-to-rule links (traceability)
- Decision tree explorer (individual rule trees)
- Decision trace viewer (evaluation path)

When Supertree is installed, shows interactive visualizations.
Otherwise, shows the raw tree data as expandable JSON.
"""

import sys
from pathlib import Path

# Add backend to path for direct imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st

from backend.rules import RuleLoader, DecisionEngine
from backend.ontology import Scenario
from backend.visualization import (
    build_rulebook_outline,
    build_decision_trace_tree,
    build_ontology_tree,
    build_corpus_rule_links,
    build_decision_tree_structure,
    build_legal_corpus_coverage,
    is_supertree_available,
    render_rulebook_outline_html,
    render_decision_trace_html,
    render_ontology_tree_html,
    render_corpus_links_html,
    render_legal_corpus_html,
)

# -----------------------------------------------------------------------------
# Page Configuration
# -----------------------------------------------------------------------------

st.set_page_config(
    page_title="Charts - KE Workbench",
    page_icon="📊",
    layout="wide",
)

# -----------------------------------------------------------------------------
# Info Banner
# -----------------------------------------------------------------------------

st.info(
    "ℹ️ **Note:** Decision Tree and Decision Trace features are now in the "
    "[KE Cockpit](/) main dashboard. This page remains useful for corpus-wide "
    "visualizations like Rulebook Outline, Ontology Browser, and Corpus Coverage.",
)

# -----------------------------------------------------------------------------
# Session State Initialization
# -----------------------------------------------------------------------------

if "rule_loader" not in st.session_state:
    st.session_state.rule_loader = RuleLoader()
    rules_dir = Path(__file__).parent.parent.parent / "backend" / "rules"
    try:
        st.session_state.rule_loader.load_directory(rules_dir)
    except FileNotFoundError:
        pass

if "selected_chart_rule" not in st.session_state:
    st.session_state.selected_chart_rule = None

if "trace_scenario" not in st.session_state:
    st.session_state.trace_scenario = {}


# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------

def render_tree_view(tree_data: dict, depth: int = 0) -> None:
    """Render a tree structure as nested expandables."""
    title = tree_data.get("title", "Node")
    children = tree_data.get("children", [])

    # Create display label with metadata
    label_parts = [title]
    if "count" in tree_data:
        label_parts.append(f"({tree_data['count']})")
    if "type" in tree_data:
        label_parts.append(f"[{tree_data['type']}]")

    label = " ".join(label_parts)

    if children:
        with st.expander(label, expanded=(depth < 1)):
            # Show additional metadata
            for key, value in tree_data.items():
                if key not in ("title", "children", "count", "type"):
                    if isinstance(value, (str, int, float, bool)):
                        st.caption(f"{key}: {value}")

            for child in children:
                render_tree_view(child, depth + 1)
    else:
        # Leaf node
        st.markdown(f"{'  ' * depth}• **{label}**")
        for key, value in tree_data.items():
            if key not in ("title", "children", "count", "type"):
                if isinstance(value, (str, int, float, bool)):
                    st.caption(f"{'  ' * depth}  {key}: {value}")


def render_chart(chart_type: str, tree_data: dict, html_renderer) -> None:
    """Render a chart with fallback to JSON view."""
    tab1, tab2 = st.tabs(["Visual", "Data"])

    with tab1:
        if is_supertree_available():
            html = html_renderer(tree_data)
            st.components.v1.html(html, height=500, scrolling=True)
        else:
            st.warning(
                "Supertree not installed. Showing tree structure below. "
                "Install with: `pip install -r requirements-visualization.txt`"
            )
            render_tree_view(tree_data)

    with tab2:
        st.json(tree_data)


# -----------------------------------------------------------------------------
# Main Content
# -----------------------------------------------------------------------------

st.title("📊 Regulatory Charts")

# Status indicator
supertree_status = is_supertree_available()
if supertree_status:
    st.success("Supertree is installed - interactive charts available")
else:
    st.info(
        "Supertree not installed - showing tree structures. "
        "Install for interactive charts: `pip install -r requirements-visualization.txt`"
    )

st.divider()

# Chart selection
chart_type = st.selectbox(
    "Select Chart Type",
    options=[
        "Rulebook Outline",
        "Ontology Browser",
        "Corpus-Rule Links",
        "Legal Corpus Coverage",
        "Decision Tree",
        "Decision Trace",
    ],
)

st.divider()

# -----------------------------------------------------------------------------
# Rulebook Outline
# -----------------------------------------------------------------------------

if chart_type == "Rulebook Outline":
    st.subheader("Rulebook Outline")
    st.caption("Hierarchical view of all rules grouped by source document")

    rules = st.session_state.rule_loader.get_all_rules()
    if not rules:
        st.warning("No rules loaded. Add YAML rules to backend/rules/")
    else:
        tree_data = build_rulebook_outline(rules)
        render_chart("rulebook_outline", tree_data, render_rulebook_outline_html)

        # Summary stats
        st.divider()
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Rules", tree_data.get("total_rules", 0))
        with col2:
            st.metric("Documents", len(tree_data.get("children", [])))
        with col3:
            tags = set()
            for rule in rules:
                tags.update(rule.tags)
            st.metric("Unique Tags", len(tags))


# -----------------------------------------------------------------------------
# Ontology Browser
# -----------------------------------------------------------------------------

elif chart_type == "Ontology Browser":
    st.subheader("Ontology Browser")
    st.caption("Explore regulatory ontology types: actors, instruments, activities")

    tree_data = build_ontology_tree()
    render_chart("ontology", tree_data, render_ontology_tree_html)


# -----------------------------------------------------------------------------
# Corpus-Rule Links
# -----------------------------------------------------------------------------

elif chart_type == "Corpus-Rule Links":
    st.subheader("Corpus-Rule Links")
    st.caption("Traceability view: source documents → articles → rules")

    rules = st.session_state.rule_loader.get_all_rules()
    if not rules:
        st.warning("No rules loaded.")
    else:
        tree_data = build_corpus_rule_links(rules)
        render_chart("corpus_links", tree_data, render_corpus_links_html)

        # Document breakdown with legal corpus metadata
        st.divider()
        st.markdown("### Document Breakdown")

        for doc in tree_data.get("children", []):
            doc_title = doc.get("document_title") or doc["title"]
            jurisdiction = doc.get("jurisdiction", "")
            jurisdiction_badge = f" [{jurisdiction}]" if jurisdiction else ""

            with st.expander(f"**{doc_title}**{jurisdiction_badge} ({doc.get('rules', 0)} rules)"):
                # Show legal corpus metadata if available
                if doc.get("citation"):
                    st.caption(f"Citation: {doc['citation']}")
                if doc.get("source_url"):
                    st.markdown(f"[Source Document]({doc['source_url']})")

                st.markdown("**Articles:**")
                for article in doc.get("children", []):
                    st.markdown(f"- {article['title']}: {article.get('count', 0)} rules")


# -----------------------------------------------------------------------------
# Legal Corpus Coverage
# -----------------------------------------------------------------------------

elif chart_type == "Legal Corpus Coverage":
    st.subheader("Legal Corpus Coverage")
    st.caption("Coverage analysis: which legal provisions have corresponding rules")

    rules = st.session_state.rule_loader.get_all_rules()
    tree_data = build_legal_corpus_coverage(rules)

    if tree_data.get("message"):
        st.warning(tree_data["message"])
    else:
        render_chart("legal_corpus", tree_data, render_legal_corpus_html)

        # Coverage summary
        st.divider()
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Legal Documents", tree_data.get("documents", 0))
        with col2:
            st.metric("Covered Articles", tree_data.get("total_covered", 0))
        with col3:
            total_gaps = tree_data.get("total_gaps", 0)
            st.metric(
                "Coverage Gaps",
                total_gaps,
                delta=f"-{total_gaps}" if total_gaps > 0 else None,
                delta_color="inverse",
            )

        # Document-level breakdown
        st.divider()
        st.markdown("### Coverage by Document")

        for doc in tree_data.get("children", []):
            coverage_pct = doc.get("coverage", 0)
            covered = doc.get("covered_articles", 0)
            total = doc.get("total_articles", 0)
            gaps = doc.get("gap_articles", 0)

            # Color based on coverage level
            if coverage_pct >= 75:
                progress_color = "green"
            elif coverage_pct >= 50:
                progress_color = "orange"
            else:
                progress_color = "red"

            jurisdiction = doc.get("jurisdiction", "")
            jurisdiction_badge = f" [{jurisdiction}]" if jurisdiction else ""

            with st.expander(
                f"**{doc['title']}**{jurisdiction_badge} - {coverage_pct:.1f}% coverage ({covered}/{total} articles)"
            ):
                # Progress bar
                st.progress(coverage_pct / 100)

                # Citation and source link
                if doc.get("citation"):
                    st.caption(f"Citation: {doc['citation']}")
                if doc.get("source_url"):
                    st.markdown(f"[View Source Document]({doc['source_url']})")

                # Article status table
                if gaps > 0:
                    st.markdown(f"**Coverage Gaps ({gaps} articles):**")
                    gap_articles = [
                        a for a in doc.get("children", [])
                        if a.get("status") == "gap"
                    ]
                    for art in gap_articles[:10]:  # Limit to first 10
                        st.markdown(f"- {art['title']}")
                    if len(gap_articles) > 10:
                        st.caption(f"...and {len(gap_articles) - 10} more")

                if covered > 0:
                    st.markdown(f"**Covered Articles ({covered}):**")
                    covered_articles = [
                        a for a in doc.get("children", [])
                        if a.get("status") == "covered"
                    ]
                    for art in covered_articles[:10]:  # Limit to first 10
                        rules_list = ", ".join(art.get("rules", [])[:3])
                        if len(art.get("rules", [])) > 3:
                            rules_list += f" (+{len(art['rules']) - 3} more)"
                        st.markdown(f"- {art['title']}: {rules_list}")
                    if len(covered_articles) > 10:
                        st.caption(f"...and {len(covered_articles) - 10} more")


# -----------------------------------------------------------------------------
# Decision Tree
# -----------------------------------------------------------------------------

elif chart_type == "Decision Tree":
    st.subheader("Decision Tree Explorer")
    st.caption("Explore the decision logic of individual rules")

    rules = st.session_state.rule_loader.get_all_rules()
    rule_ids = [r.rule_id for r in rules if r.decision_tree]

    if not rule_ids:
        st.warning("No rules with decision trees found.")
    else:
        selected_rule = st.selectbox(
            "Select Rule",
            options=rule_ids,
            key="decision_tree_rule_select",
        )

        if selected_rule:
            rule = st.session_state.rule_loader.get_rule(selected_rule)

            if rule and rule.decision_tree:
                # Rule metadata
                st.markdown(f"**{rule.rule_id}** v{rule.version}")
                if rule.description:
                    st.caption(rule.description)
                if rule.source:
                    st.caption(f"Source: {rule.source.document_id} Art. {rule.source.article or ''}")

                st.divider()

                # Build and display tree
                tree_data = build_decision_tree_structure(rule.decision_tree)

                if tree_data:
                    tab1, tab2 = st.tabs(["Tree View", "JSON"])

                    with tab1:
                        render_tree_view(tree_data)

                    with tab2:
                        st.json(tree_data)
                else:
                    st.warning("Could not parse decision tree structure.")


# -----------------------------------------------------------------------------
# Decision Trace
# -----------------------------------------------------------------------------

elif chart_type == "Decision Trace":
    st.subheader("Decision Trace Viewer")
    st.caption("Evaluate a rule against a scenario and see the decision path")

    rules = st.session_state.rule_loader.get_all_rules()
    rule_ids = [r.rule_id for r in rules if r.decision_tree]

    if not rule_ids:
        st.warning("No rules with decision trees found.")
    else:
        selected_rule = st.selectbox(
            "Select Rule",
            options=rule_ids,
            key="trace_rule_select",
        )

        if selected_rule:
            rule = st.session_state.rule_loader.get_rule(selected_rule)

            # Scenario builder
            st.markdown("### Build Scenario")
            st.caption("Enter scenario attributes for evaluation")

            # Common scenario fields
            col1, col2 = st.columns(2)

            with col1:
                instrument_type = st.selectbox(
                    "Instrument Type",
                    options=["art", "emt", "stablecoin", "utility_token",
                             "rwa_token", "rwa_debt", "rwa_equity", "rwa_property"],
                    key="trace_instrument_type",
                )

                jurisdiction = st.selectbox(
                    "Jurisdiction",
                    options=["EU", "US", "UK", "Other"],
                    key="trace_jurisdiction",
                )

            with col2:
                activity = st.selectbox(
                    "Activity",
                    options=["public_offer", "admission_to_trading", "custody",
                             "exchange", "tokenization", "disclosure"],
                    key="trace_activity",
                )

            # Additional attributes
            with st.expander("Additional Attributes", expanded=False):
                is_credit_institution = st.checkbox("Is Credit Institution", key="trace_credit")
                authorized = st.checkbox("Authorized", key="trace_authorized")
                rwa_authorized = st.checkbox("RWA Authorized", key="trace_rwa_auth")
                is_regulated_market_issuer = st.checkbox("Regulated Market Issuer", key="trace_regulated")
                custodian_authorized = st.checkbox("Custodian Authorized", key="trace_custodian_auth")
                assets_segregated = st.checkbox("Assets Segregated", key="trace_segregated")
                disclosure_current = st.checkbox("Disclosure Current", key="trace_disclosure")
                total_token_value_eur = st.number_input(
                    "Total Token Value (EUR)",
                    min_value=0,
                    value=0,
                    key="trace_value",
                )

            if st.button("Evaluate Rule", type="primary"):
                # Build scenario
                scenario_dict = {
                    "instrument_type": instrument_type,
                    "jurisdiction": jurisdiction,
                    "activity": activity,
                    "is_credit_institution": is_credit_institution,
                    "authorized": authorized,
                    "rwa_authorized": rwa_authorized,
                    "is_regulated_market_issuer": is_regulated_market_issuer,
                    "custodian_authorized": custodian_authorized,
                    "assets_segregated": assets_segregated,
                    "disclosure_current": disclosure_current,
                }

                if total_token_value_eur > 0:
                    scenario_dict["total_token_value_eur"] = total_token_value_eur

                try:
                    scenario = Scenario(**scenario_dict)

                    # Evaluate
                    engine = DecisionEngine(st.session_state.rule_loader)
                    result = engine.evaluate(scenario, selected_rule)

                    st.divider()
                    st.markdown("### Evaluation Result")

                    # Result summary
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        decision = result.decision or "N/A"
                        color = "#28a745" if decision in ("authorized", "compliant", "exempt") else (
                            "#dc3545" if decision in ("not_authorized", "non_compliant") else "#ffc107"
                        )
                        st.markdown(
                            f'<div style="background-color:{color};color:white;'
                            f'padding:8px 16px;border-radius:4px;text-align:center;">'
                            f'{decision.upper()}</div>',
                            unsafe_allow_html=True,
                        )

                    with col2:
                        st.metric("Applicable", "Yes" if result.applicable else "No")

                    with col3:
                        st.metric("Trace Steps", len(result.trace))

                    # Obligations
                    if result.obligations:
                        st.markdown("**Obligations:**")
                        for obl in result.obligations:
                            st.markdown(f"- **{obl.id}**: {obl.description or ''}")

                    # Decision trace
                    st.markdown("### Decision Trace")

                    tree_data = build_decision_trace_tree(
                        trace=result.trace,
                        decision=result.decision,
                        rule_id=selected_rule,
                    )

                    render_chart("decision_trace", tree_data, render_decision_trace_html)

                except Exception as e:
                    st.error(f"Error evaluating rule: {e}")


# -----------------------------------------------------------------------------
# Footer
# -----------------------------------------------------------------------------

st.divider()
st.caption("Charts v0.1 | Internal Use Only")
