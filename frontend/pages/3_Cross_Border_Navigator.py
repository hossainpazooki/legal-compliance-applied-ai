"""
Cross-Border Compliance Navigator.

Multi-jurisdiction compliance analysis with conflict detection and pathway synthesis.

Run from repo root:
    streamlit run frontend/Home.py
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
import asyncio
import json
from datetime import datetime

from backend.rule_service.app.services.jurisdiction.resolver import resolve_jurisdictions, get_equivalences
from backend.rule_service.app.services.jurisdiction.evaluator import evaluate_jurisdiction
from backend.rule_service.app.services.jurisdiction.conflicts import detect_conflicts
from backend.rule_service.app.services.jurisdiction.pathway import (
    synthesize_pathway,
    aggregate_obligations,
    estimate_timeline,
)
from backend.synthetic_data.config import (
    INSTRUMENT_TYPES,
    ACTIVITY_TYPES,
    JURISDICTIONS,
    RULE_DISTRIBUTIONS,
)
from frontend.helpers import get_analytics_client, get_rules_by_jurisdiction

# -----------------------------------------------------------------------------
# Page Configuration
# -----------------------------------------------------------------------------

st.set_page_config(
    page_title="Cross-Border Navigator",
    page_icon="",
    layout="wide",
)

# -----------------------------------------------------------------------------
# Jurisdiction Info (Sidebar)
# -----------------------------------------------------------------------------

with st.sidebar:
    st.header("Jurisdiction Coverage")

    # Get rules by jurisdiction
    rules_by_jur = get_rules_by_jurisdiction()

    if rules_by_jur:
        for jur, rules in sorted(rules_by_jur.items()):
            with st.expander(f"{jur} ({len(rules)} rules)"):
                for rule_id in rules[:10]:
                    st.caption(f"• {rule_id}")
                if len(rules) > 10:
                    st.caption(f"... and {len(rules) - 10} more")
    else:
        st.info("Connect to API to see rules")

    st.divider()

    # Quick reference
    st.subheader("Quick Reference")
    st.markdown("""
    **Jurisdiction Codes:**
    - **EU** - European Union (MiCA, MiFID II)
    - **UK** - United Kingdom (FCA Crypto)
    - **US** - United States (SEC, GENIUS Act)
    - **CH** - Switzerland (FINMA, FinSA)
    - **SG** - Singapore (MAS, PSA)
    """)

# -----------------------------------------------------------------------------
# Header
# -----------------------------------------------------------------------------

st.title("Cross-Border Compliance Navigator")

st.markdown("""
Navigate multi-jurisdiction compliance requirements for digital assets.
Select your scenario to get a comprehensive analysis of applicable regulations,
potential conflicts, and recommended compliance pathway.
""")

# Show coverage summary
col_sum1, col_sum2, col_sum3 = st.columns(3)
with col_sum1:
    total_rules = sum(len(r) for r in rules_by_jur.values()) if rules_by_jur else 0
    st.metric("Total Rules", total_rules)
with col_sum2:
    st.metric("Jurisdictions", len(rules_by_jur) if rules_by_jur else len(JURISDICTIONS))
with col_sum3:
    st.metric("Regulatory Regimes", len(RULE_DISTRIBUTIONS))

st.divider()

# -----------------------------------------------------------------------------
# Scenario Input
# -----------------------------------------------------------------------------

st.header("1. Define Your Scenario")

col1, col2 = st.columns(2)

with col1:
    issuer_jurisdiction = st.selectbox(
        "Issuer Jurisdiction",
        options=JURISDICTIONS,
        index=3,  # Default to CH
        help="Where is the issuer/operator based?",
    )

    instrument_type = st.selectbox(
        "Instrument Type",
        options=INSTRUMENT_TYPES,
        help="Type of digital asset or token (from synthetic_data/config.py)",
    )

    activity = st.selectbox(
        "Activity",
        options=ACTIVITY_TYPES,
        help="Regulatory activity (from synthetic_data/config.py)",
    )

with col2:
    target_jurisdictions = st.multiselect(
        "Target Markets",
        options=JURISDICTIONS,
        default=["EU", "UK"],
        help="Markets where you intend to offer or promote",
    )

    investor_types = st.multiselect(
        "Investor Types",
        options=["retail", "professional", "institutional"],
        default=["professional"],
        help="Types of investors you're targeting",
    )

# Additional facts
with st.expander("Additional Scenario Details (Optional)"):
    col_facts1, col_facts2 = st.columns(2)

    with col_facts1:
        is_authorized = st.checkbox("Has existing authorization", value=False)
        is_credit_institution = st.checkbox("Is a credit institution", value=False)
        has_whitepaper = st.checkbox("Has prepared whitepaper", value=False)

    with col_facts2:
        is_fca_authorized = st.checkbox("FCA authorized (UK)", value=False)
        has_risk_warning = st.checkbox("Has risk warning", value=False)
        is_first_time_investor = st.checkbox("First-time investor scenario", value=False)

# Build facts dict
additional_facts = {}
if is_authorized:
    additional_facts["has_authorization"] = True
    additional_facts["issuer_type"] = "credit_institution" if is_credit_institution else "other"
if has_whitepaper:
    additional_facts["whitepaper_submitted"] = True
if is_fca_authorized:
    additional_facts["is_fca_authorized"] = True
if has_risk_warning:
    additional_facts["has_prescribed_risk_warning"] = True
    additional_facts["risk_warning_prominent"] = True
if is_first_time_investor:
    additional_facts["is_first_time_investor"] = True

# -----------------------------------------------------------------------------
# Run Analysis
# -----------------------------------------------------------------------------

st.divider()

if st.button("Analyze Compliance Requirements", type="primary", use_container_width=True):
    with st.spinner("Analyzing cross-border compliance requirements..."):
        # Step 1: Resolve jurisdictions
        applicable = resolve_jurisdictions(
            issuer=issuer_jurisdiction,
            targets=target_jurisdictions,
            instrument_type=instrument_type,
        )

        # Step 2: Get equivalences
        equivalences = get_equivalences(
            from_jurisdiction=issuer_jurisdiction,
            to_jurisdictions=target_jurisdictions,
        )

        # Step 3: Evaluate each jurisdiction
        async def run_evaluations():
            tasks = [
                evaluate_jurisdiction(
                    jurisdiction=j.jurisdiction.value,
                    regime_id=j.regime_id,
                    facts={
                        **additional_facts,
                        "instrument_type": instrument_type,
                        "activity": activity,
                        "investor_types": investor_types,
                        "target_jurisdiction": j.jurisdiction.value,
                        "jurisdiction": j.jurisdiction.value,
                    },
                )
                for j in applicable
            ]
            return await asyncio.gather(*tasks)

        jurisdiction_results = asyncio.run(run_evaluations())

        # Add roles
        for i, result in enumerate(jurisdiction_results):
            result["role"] = applicable[i].role.value

        # Step 4: Detect conflicts
        conflicts = detect_conflicts(jurisdiction_results)

        # Step 5: Synthesize pathway
        pathway = synthesize_pathway(jurisdiction_results, conflicts, equivalences)

        # Step 6: Aggregate obligations
        cumulative_obligations = aggregate_obligations(jurisdiction_results)

        # Store in session state for display
        st.session_state["navigate_results"] = {
            "applicable": applicable,
            "equivalences": equivalences,
            "jurisdiction_results": jurisdiction_results,
            "conflicts": conflicts,
            "pathway": pathway,
            "obligations": cumulative_obligations,
            "timeline": estimate_timeline(pathway),
        }

# -----------------------------------------------------------------------------
# Display Results
# -----------------------------------------------------------------------------

if "navigate_results" in st.session_state:
    results = st.session_state["navigate_results"]

    st.header("2. Analysis Results")

    # Summary cards
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Jurisdictions",
            len(results["applicable"]),
            help="Number of applicable jurisdictions",
        )

    with col2:
        total_obligations = len(results["obligations"])
        st.metric(
            "Total Obligations",
            total_obligations,
            help="Cumulative obligations across all jurisdictions",
        )

    with col3:
        conflict_count = len(results["conflicts"])
        st.metric(
            "Conflicts Detected",
            conflict_count,
            delta=f"{conflict_count} issues" if conflict_count > 0 else None,
            delta_color="inverse" if conflict_count > 0 else "off",
        )

    with col4:
        st.metric(
            "Estimated Timeline",
            results["timeline"],
            help="Estimated time to full compliance",
        )

    st.divider()

    # Tabs for detailed results
    tab1, tab2, tab3, tab4 = st.tabs([
        "Jurisdictions",
        "Conflicts",
        "Pathway",
        "Audit Trail",
    ])

    with tab1:
        st.subheader("Jurisdiction Analysis")

        for jr in results["jurisdiction_results"]:
            with st.expander(
                f"**{jr['jurisdiction']}** - {jr['regime_id']} ({jr.get('role', 'unknown')})"
            ):
                # Status badge
                status = jr.get("status", "unknown")
                if status == "compliant":
                    st.success(f"Status: {status.upper()}")
                elif status == "blocked":
                    st.error(f"Status: {status.upper()}")
                elif status == "requires_action":
                    st.warning(f"Status: {status.upper()}")
                else:
                    st.info(f"Status: {status}")

                st.write(f"**Rules Evaluated:** {jr.get('rules_evaluated', 0)}")
                st.write(f"**Applicable Rules:** {jr.get('applicable_rules', 0)}")

                if jr.get("decisions"):
                    st.write("**Decisions:**")
                    for dec in jr["decisions"]:
                        st.write(f"- `{dec['rule_id']}`: {dec['decision']}")

                if jr.get("obligations"):
                    st.write("**Obligations:**")
                    for obl in jr["obligations"]:
                        st.write(f"- **{obl['id']}**: {obl.get('description', 'N/A')}")

    with tab2:
        st.subheader("Cross-Jurisdiction Conflicts")

        if not results["conflicts"]:
            st.success("No conflicts detected between jurisdictions")
        else:
            for conflict in results["conflicts"]:
                severity = conflict.get("severity", "info")
                if severity == "blocking":
                    st.error(f"**BLOCKING**: {conflict.get('description', 'Unknown conflict')}")
                elif severity == "warning":
                    st.warning(f"**WARNING**: {conflict.get('description', 'Unknown conflict')}")
                else:
                    st.info(f"**INFO**: {conflict.get('description', 'Unknown conflict')}")

                st.write(f"- Type: `{conflict.get('type')}`")
                st.write(f"- Jurisdictions: {', '.join(conflict.get('jurisdictions', []))}")
                if conflict.get("resolution_strategy"):
                    st.write(f"- Resolution: {conflict.get('resolution_note', conflict.get('resolution_strategy'))}")

    with tab3:
        st.subheader("Compliance Pathway")

        if not results["pathway"]:
            st.info("No compliance steps required")
        else:
            # Visual flow diagram
            st.markdown("##### Compliance Flow")

            # Create a simple flow visualization using columns
            flow_cols = st.columns(min(len(results["pathway"]), 5))
            for i, step in enumerate(results["pathway"][:5]):
                with flow_cols[i]:
                    status = step.get("status", "pending")
                    jur = step.get("jurisdiction", "?")[:2]
                    step_num = step.get("step_id", i + 1)

                    if status == "waived":
                        st.success(f"**{jur}**\nStep {step_num}\n(Waived)")
                    elif status == "completed":
                        st.success(f"**{jur}**\nStep {step_num}")
                    else:
                        st.warning(f"**{jur}**\nStep {step_num}")

            if len(results["pathway"]) > 5:
                st.caption(f"... and {len(results['pathway']) - 5} more steps")

            st.divider()

            # Detailed steps
            st.markdown("##### Step Details")
            for step in results["pathway"]:
                status_icon = "✅" if step.get("status") == "waived" else "⏳"
                status_text = "WAIVED" if step.get("status") == "waived" else "PENDING"

                st.markdown(f"""
                **Step {step['step_id']}** {status_icon} `{status_text}`

                - **Jurisdiction:** {step.get('jurisdiction', 'N/A')}
                - **Regime:** {step.get('regime', 'N/A')}
                - **Action:** {step.get('action', step.get('obligation_id', 'N/A'))}
                - **Timeline:** {step.get('timeline', {}).get('min_days', '?')}-{step.get('timeline', {}).get('max_days', '?')} days
                """)

                if step.get("waiver_reason"):
                    st.caption(f"Waiver: {step['waiver_reason']}")

                if step.get("prerequisites"):
                    st.caption(f"Prerequisites: Steps {step['prerequisites']}")

                st.divider()

    with tab4:
        st.subheader("Cumulative Obligations")

        if not results["obligations"]:
            st.info("No obligations identified")
        else:
            # Group by jurisdiction
            obls_by_jurisdiction = {}
            for obl in results["obligations"]:
                j = obl.get("jurisdiction", "Unknown")
                if j not in obls_by_jurisdiction:
                    obls_by_jurisdiction[j] = []
                obls_by_jurisdiction[j].append(obl)

            for jurisdiction, obls in obls_by_jurisdiction.items():
                st.write(f"**{jurisdiction}** ({len(obls)} obligations)")
                for obl in obls:
                    st.write(f"- `{obl['id']}`: {obl.get('description', 'N/A')}")

        st.divider()

        # Equivalences
        st.subheader("Equivalence Determinations")

        if not results["equivalences"]:
            st.info("No equivalence determinations found")
        else:
            for eq in results["equivalences"]:
                st.write(f"**{eq['from']} → {eq['to']}** ({eq['scope']})")
                st.write(f"- Status: `{eq['status']}`")
                if eq.get("notes"):
                    st.write(f"- Notes: {eq['notes']}")

# -----------------------------------------------------------------------------
# Export Section
# -----------------------------------------------------------------------------

if "navigate_results" in st.session_state:
    st.divider()
    st.header("3. Export Report")

    results = st.session_state["navigate_results"]

    # Build export data
    export_data = {
        "generated_at": datetime.now().isoformat(),
        "scenario": {
            "issuer_jurisdiction": issuer_jurisdiction,
            "target_jurisdictions": target_jurisdictions,
            "instrument_type": instrument_type,
            "activity": activity,
            "investor_types": investor_types,
        },
        "summary": {
            "jurisdictions_count": len(results["applicable"]),
            "obligations_count": len(results["obligations"]),
            "conflicts_count": len(results["conflicts"]),
            "estimated_timeline": results["timeline"],
        },
        "jurisdiction_results": [
            {
                "jurisdiction": jr.get("jurisdiction"),
                "regime_id": jr.get("regime_id"),
                "status": jr.get("status"),
                "role": jr.get("role"),
                "rules_evaluated": jr.get("rules_evaluated", 0),
            }
            for jr in results["jurisdiction_results"]
        ],
        "conflicts": results["conflicts"],
        "pathway": results["pathway"],
        "obligations": results["obligations"],
        "equivalences": results["equivalences"],
    }

    col_exp1, col_exp2, col_exp3 = st.columns(3)

    with col_exp1:
        # JSON export
        json_str = json.dumps(export_data, indent=2, default=str)
        st.download_button(
            label="Download JSON Report",
            data=json_str,
            file_name=f"compliance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True,
        )

    with col_exp2:
        # Summary text export
        summary_text = f"""CROSS-BORDER COMPLIANCE REPORT
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

SCENARIO
--------
Issuer Jurisdiction: {issuer_jurisdiction}
Target Markets: {', '.join(target_jurisdictions)}
Instrument Type: {instrument_type}
Activity: {activity}
Investor Types: {', '.join(investor_types)}

SUMMARY
-------
Applicable Jurisdictions: {len(results['applicable'])}
Total Obligations: {len(results['obligations'])}
Conflicts Detected: {len(results['conflicts'])}
Estimated Timeline: {results['timeline']}

COMPLIANCE PATHWAY
------------------
"""
        for step in results["pathway"]:
            summary_text += f"Step {step['step_id']}: {step.get('jurisdiction', 'N/A')} - {step.get('action', step.get('obligation_id', 'N/A'))}\n"

        summary_text += """
DISCLAIMER
----------
This is a research/demo tool. The compliance analysis is illustrative
and should not be relied upon for actual regulatory decisions.
"""

        st.download_button(
            label="Download Text Summary",
            data=summary_text,
            file_name=f"compliance_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain",
            use_container_width=True,
        )

    with col_exp3:
        # Pathway CSV export
        if results["pathway"]:
            import csv
            import io

            csv_buffer = io.StringIO()
            writer = csv.writer(csv_buffer)
            writer.writerow(["Step", "Jurisdiction", "Regime", "Action", "Status", "Min Days", "Max Days"])
            for step in results["pathway"]:
                writer.writerow([
                    step.get("step_id", ""),
                    step.get("jurisdiction", ""),
                    step.get("regime", ""),
                    step.get("action", step.get("obligation_id", "")),
                    step.get("status", "pending"),
                    step.get("timeline", {}).get("min_days", ""),
                    step.get("timeline", {}).get("max_days", ""),
                ])

            st.download_button(
                label="Download Pathway CSV",
                data=csv_buffer.getvalue(),
                file_name=f"compliance_pathway_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True,
            )
        else:
            st.button("Download Pathway CSV", disabled=True, use_container_width=True)

# -----------------------------------------------------------------------------
# Footer
# -----------------------------------------------------------------------------

st.divider()

st.caption("""
**Disclaimer:** This is a research/demo tool. The compliance analysis is illustrative
and should not be relied upon for actual regulatory decisions. Always consult qualified
legal counsel for compliance matters.
""")
