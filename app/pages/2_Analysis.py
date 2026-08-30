"""
Analysis page — Phase 4.
Reads the last uploaded analysis from session state (or lets the user
enter an analysis ID manually) and shows the full MITRE ATLAS mapping.
"""

import streamlit as st
import pandas as pd

from app.ingestion.service import get_analysis_by_id
from app.atlas_mapping.mapper import map_components_to_techniques, summarise_by_tactic
from app.atlas_mapping.atlas_loader import get_kb

st.title("🗺️ MITRE ATLAS Analysis")
st.caption("Maps your detected AI components to ATLAS tactics and techniques.")

# ── Resolve which analysis to show ──────────────────────────────────────────
analysis_id = st.session_state.get("last_analysis_id", "")

with st.expander("Load a different analysis by ID"):
    manual_id = st.text_input("Analysis ID", value=analysis_id)
    if st.button("Load"):
        analysis_id = manual_id.strip()

if not analysis_id:
    st.info("Upload an architecture document on the Upload page first.")
    st.stop()

# ── Fetch from MongoDB ───────────────────────────────────────────────────────
record = get_analysis_by_id(analysis_id)

if record is None:
    st.error(f"Analysis `{analysis_id}` not found in the database.")
    st.stop()

if not record.components:
    st.warning("No components were detected in this analysis. Nothing to map.")
    st.stop()

st.success(f"Loaded analysis: `{record.filename}` — `{record.analysis_id}`")

# ── Detected components summary ──────────────────────────────────────────────
st.subheader("Detected Components")
comp_df = pd.DataFrame([c.model_dump() for c in record.components])
comp_df = comp_df.rename(columns={
    "name": "Component",
    "component_type": "Type",
    "confidence": "Confidence",
    "source_text": "Matched Text",
})
st.dataframe(comp_df, use_container_width=True, hide_index=True)

# ── ATLAS mapping ────────────────────────────────────────────────────────────
st.subheader("MITRE ATLAS Technique Mapping")

with st.spinner("Mapping components to ATLAS techniques..."):
    try:
        mapped = map_components_to_techniques(record.components)
    except FileNotFoundError as e:
        st.error(str(e))
        st.stop()
    except Exception as e:
        st.error(f"Mapping failed: {e}")
        st.stop()

if not mapped:
    st.warning("No ATLAS techniques could be mapped from the detected components.")
    st.stop()

kb = get_kb()
st.caption(f"ATLAS knowledge base version: **{kb.version}**")

# ── Full technique table ─────────────────────────────────────────────────────
with st.expander("View all mapped techniques", expanded=True):
    rows = []
    for m in mapped:
        rows.append({
            "Technique ID": m.technique_id,
            "Technique": m.technique_name,
            "Tactic": m.tactic_name or "—",
            "Source Component": m.source_component,
            "Maturity": m.maturity,
            "Confidence": m.confidence,
        })
    df = pd.DataFrame(rows)
    st.dataframe(df, hide_index=True)

# ── Grouped by tactic ───────────────────────────────────────────────────────
st.subheader("Techniques by ATLAS Tactic")
grouped = summarise_by_tactic(mapped)

for tactic_name, techniques in sorted(grouped.items()):
    with st.expander(f"🎯 {tactic_name} ({len(techniques)} techniques)"):
        for t in techniques:
            st.markdown(f"**{t.technique_id} — {t.technique_name}**")
            st.caption(f"Source component: `{t.source_component}` | Maturity: {t.maturity}")
            if t.description:
                st.write(t.description[:250] + ("..." if len(t.description) >= 250 else ""))
            st.divider()

# ── Store for downstream phases ──────────────────────────────────────────────
st.session_state["last_analysis_id"] = analysis_id
st.session_state["last_mapped_techniques"] = [m.model_dump() for m in mapped]
st.info("ATLAS mapping complete. Attack path generation comes in Phase 5.")