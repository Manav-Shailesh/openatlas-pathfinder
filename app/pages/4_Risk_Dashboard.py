"""
Risk Dashboard — Phase 6.
Displays the overall security score, risk heatmap, per-path
bar chart, L/I/E breakdown, and mitigation summary.
All data comes from MongoDB — no new AI calls on this page.
"""

import streamlit as st
import pandas as pd

from app.risk_scoring.service import get_dashboard_data
from app.risk_scoring.heatmap import (
    build_risk_gauge,
    build_risk_heatmap,
    build_path_score_chart,
    build_lia_chart,
)

st.title("📊 Risk Dashboard")
st.caption("Overall security posture, risk heatmap, and mitigation priorities.")

# ── Resolve analysis ID ──────────────────────────────────────────────────────
analysis_id = st.session_state.get("last_analysis_id", "")

with st.expander("Load a different analysis by ID"):
    manual_id = st.text_input("Analysis ID", value=analysis_id)
    if st.button("Load"):
        analysis_id = manual_id.strip()

if not analysis_id:
    st.info("Complete the Upload and Attack Paths steps first.")
    st.stop()

# ── Load dashboard data ──────────────────────────────────────────────────────
with st.spinner("Loading risk data..."):
    data = get_dashboard_data(analysis_id)

if data is None:
    st.warning(
        "No attack path data found for this analysis. "
        "Go to the Attack Paths page and generate paths first."
    )
    st.stop()

overall      = data["overall"]
ap_record    = data["attack_path_record"]
components   = data["components"]
mitigations  = data["mitigations"]

# ── Overall score gauge ───────────────────────────────────────────────────────
st.subheader("Overall Security Score")

risk_icons = {"High": "🔴", "Medium": "🟡", "Low": "🟢", "Unknown": "⚪"}
icon = risk_icons.get(overall["overall_risk_level"], "⚪")

gauge_fig = build_risk_gauge(overall["overall_score"], overall["overall_risk_level"])
st.plotly_chart(gauge_fig, use_container_width=True)

# ── Summary metrics ──────────────────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total Paths",    overall["total_paths"])
c2.metric("🔴 High Risk",   overall["high_count"])
c3.metric("🟡 Medium Risk", overall["medium_count"])
c4.metric("🟢 Low Risk",    overall["low_count"])
c5.metric("Avg Score",      f"{overall['average_score']}/100")

st.divider()

# ── L / I / E averages ───────────────────────────────────────────────────────
st.subheader("Risk Factor Averages")
f1, f2, f3 = st.columns(3)
f1.metric("Avg Likelihood", f"{overall['average_likelihood']}/10",
          help="How easy the attacks are to execute")
f2.metric("Avg Impact",     f"{overall['average_impact']}/10",
          help="Business damage if attacks succeed")
f3.metric("Avg Exposure",   f"{overall['average_exposure']}/10",
          help="How exposed this architecture is")

st.divider()

# ── Charts row ───────────────────────────────────────────────────────────────
st.subheader("Risk Heatmap")
heatmap_fig = build_risk_heatmap(ap_record, components)
st.plotly_chart(heatmap_fig, use_container_width=True)

st.subheader("Attack Path Risk Scores")
bar_fig = build_path_score_chart(ap_record)
st.plotly_chart(bar_fig, use_container_width=True)

st.subheader("Likelihood · Impact · Exposure Breakdown")
lia_fig = build_lia_chart(ap_record)
st.plotly_chart(lia_fig, use_container_width=True)

st.divider()

# ── Component risk table ─────────────────────────────────────────────────────
st.subheader("Risk by Component")
comp_risk = data["component_risk"]
if comp_risk:
    comp_df = pd.DataFrame(comp_risk)
    comp_df = comp_df.rename(columns={
        "component":    "Component",
        "average_risk": "Avg Risk Score",
        "risk_level":   "Risk Level",
        "path_count":   "Paths Affected",
    })
    st.dataframe(comp_df, use_container_width=True, hide_index=True)

st.divider()

# ── Highest risk path callout ─────────────────────────────────────────────────
st.subheader("Highest Risk Attack Path")
highest = max(ap_record.attack_paths, key=lambda p: p.risk_score)
st.error(
    f"**{highest.name}**  \n"
    f"Risk Score: **{highest.risk_score:.1f}/100** · "
    f"Likelihood: {highest.likelihood}/10 · "
    f"Impact: {highest.impact}/10 · "
    f"Exposure: {highest.exposure}/10  \n"
    f"Entry Point: {highest.entry_point}  \n"
    f"Final Impact: {highest.final_impact}"
)
if highest.ai_explanation:
    st.info(f"🤖 **AI Analysis:** {highest.ai_explanation}")

st.divider()

# ── Mitigation priorities ────────────────────────────────────────────────────
st.subheader("Prioritised Mitigations")
st.caption("Sorted by how many attack paths each mitigation addresses.")

control_icons = {"Preventive": "🛡️", "Detective": "🔍", "Corrective": "🔧"}

for m in mitigations[:10]:
    icon_m = control_icons.get(m["control_type"], "📋")
    effort_color = {"Low": "🟢", "Medium": "🟡", "High": "🔴"}.get(m["effort"], "⚪")

    with st.expander(
        f"{icon_m} {m['title']} "
        f"— addresses {m['addresses_paths']} path(s) "
        f"| Effort: {effort_color} {m['effort']}"
    ):
        st.write(m["description"])
        col1, col2 = st.columns(2)
        col1.caption(f"Control Type: **{m['control_type']}**")
        if m.get("atlas_mitigation_id"):
            col2.caption(f"ATLAS: **{m['atlas_mitigation_id']}**")

st.divider()

# ── Store for Phase 8 ────────────────────────────────────────────────────────
st.session_state["last_analysis_id"]  = analysis_id
st.session_state["dashboard_overall"] = overall
st.info("Risk dashboard complete. PDF report generation comes in Phase 8.")