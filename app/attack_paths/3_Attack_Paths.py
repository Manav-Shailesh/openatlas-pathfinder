"""
Attack Paths page — Phase 5.
Shows AI-generated attack paths, interactive graph, risk scores,
and specific mitigations for the last analysed architecture.
"""

import streamlit as st
import pandas as pd

from app.ingestion.service import get_analysis_by_id
from app.attack_paths.service import run_attack_path_pipeline, get_attack_path_record
from app.attack_paths.graph_builder import build_attack_graph, build_pyvis_html, get_graph_stats

st.title("⚔️ Attack Path Analysis")
st.caption("AI-generated multi-step attack chains mapped to MITRE ATLAS techniques.")

# ── Resolve analysis ─────────────────────────────────────────────────────────
analysis_id = st.session_state.get("last_analysis_id", "")

with st.expander("Load a different analysis by ID"):
    manual_id = st.text_input("Analysis ID", value=analysis_id)
    if st.button("Load"):
        analysis_id = manual_id.strip()

if not analysis_id:
    st.info("Upload an architecture document on the Upload page first.")
    st.stop()

# ── Check for existing results or run pipeline ───────────────────────────────
existing = get_attack_path_record(analysis_id)

col1, col2 = st.columns([3, 1])
with col1:
    run_btn = st.button(
        "🔄 Re-run AI Attack Path Generation" if existing else "🚀 Generate Attack Paths",
        type="primary",
    )
with col2:
    if existing:
        st.metric("Paths found", existing.total_paths)

if run_btn or existing is None:
    record = get_analysis_by_id(analysis_id)
    if record is None:
        st.error(f"Analysis `{analysis_id}` not found.")
        st.stop()
    if not record.components:
        st.warning("No components detected — nothing to generate paths for.")
        st.stop()

    with st.spinner("🤖 Gemini is reasoning about attack paths... this may take 20-40 seconds"):
        result = run_attack_path_pipeline(record)
else:
    result = existing

if not result or not result.attack_paths:
    st.warning("No attack paths could be generated for this architecture.")
    st.stop()

# ── Summary metrics ──────────────────────────────────────────────────────────
st.subheader("Summary")

risk_colors = {"High": "🔴", "Medium": "🟡", "Low": "🟢", "Unknown": "⚪"}
icon = risk_colors.get(result.overall_risk_level, "⚪")

m1, m2, m3 = st.columns(3)
m1.metric("Total Attack Paths", result.total_paths)
m2.metric("Highest Risk Score", f"{result.highest_risk_score:.1f} / 100")
m3.metric("Overall Risk Level", f"{icon} {result.overall_risk_level}")

# ── Interactive graph ─────────────────────────────────────────────────────────
st.subheader("Attack Graph")
st.caption("Nodes = ATLAS techniques. Edges = attack step transitions. Hover for details.")

graph_html = build_pyvis_html(result.attack_paths, height="550px")
st.components.v1.html(graph_html, height=570, scrolling=False)

# Graph stats
G = build_attack_graph(result.attack_paths)
stats = get_graph_stats(G)
with st.expander("Graph statistics"):
    s1, s2, s3 = st.columns(3)
    s1.metric("Unique Techniques", stats["total_nodes"])
    s2.metric("Attack Transitions", stats["total_edges"])
    s3.metric("Most Connected", stats["most_connected_technique"] or "—")

# ── Individual attack paths ──────────────────────────────────────────────────
st.subheader("Attack Paths Detail")

for path in result.attack_paths:
    risk_icon = risk_colors.get(path.risk_level, "⚪")
    with st.expander(
        f"{risk_icon} {path.path_id} — {path.name} "
        f"[Risk: {path.risk_score:.1f}/100]",
        expanded=path.risk_level == "High",
    ):
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Likelihood", f"{path.likelihood:.1f}/10")
        c2.metric("Impact", f"{path.impact:.1f}/10")
        c3.metric("Exposure", f"{path.exposure:.1f}/10")
        c4.metric("Risk Score", f"{path.risk_score:.1f}/100")

        st.markdown(f"**Entry Point:** {path.entry_point}")
        st.markdown(f"**Final Impact:** {path.final_impact}")

        if path.ai_explanation:
            st.info(f"🤖 **AI Risk Analysis:** {path.ai_explanation}")

        # Steps table
        st.markdown("**Attack Steps:**")
        steps_df = pd.DataFrame([
            {
                "Step": s.step,
                "Technique ID": s.technique_id,
                "Technique": s.technique_name,
                "Attacker Action": s.action,
                "Enables": s.leads_to,
            }
            for s in path.steps
        ])
        st.dataframe(steps_df, use_container_width=True, hide_index=True)

        # Mitigations
        if path.mitigations:
            st.markdown("**Mitigations:**")
            for m in path.mitigations:
                control_icons = {
                    "Preventive": "🛡️",
                    "Detective": "🔍",
                    "Corrective": "🔧"
                }
                icon_m = control_icons.get(m.get("control_type", ""), "📋")
                st.markdown(
                    f"{icon_m} **{m.get('title', 'Mitigation')}** "
                    f"({m.get('control_type', '')} | Effort: {m.get('effort', '')})"
                )
                st.caption(m.get("description", ""))
                if m.get("atlas_mitigation_id"):
                    st.caption(f"ATLAS: {m.get('atlas_mitigation_id')}")

# ── Store for Phase 6 ────────────────────────────────────────────────────────
st.session_state["last_analysis_id"] = analysis_id
st.session_state["last_attack_path_record"] = result.model_dump()
st.info("Attack paths saved. Risk dashboard and reporting come in Phase 6 & 7.")