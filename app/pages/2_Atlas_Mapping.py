"""
ATLAS Mapping page — Phase 4 UI.
Takes the last uploaded analysis (from the Upload page) and maps its
detected components to MITRE ATLAS techniques.
"""

import streamlit as st
import pandas as pd

from app.atlas_mapping.service import run_atlas_mapping, get_latest_mapping
from app.ingestion.service import get_analysis_by_id

st.set_page_config(page_title="ATLAS Mapping - OpenATLAS Pathfinder", page_icon="🎯")

st.title("MITRE ATLAS Mapping")
st.caption("Maps your detected architecture components to real MITRE ATLAS techniques.")

analysis_id = st.session_state.get("last_analysis_id")

if not analysis_id:
    st.warning("No analysis found. Upload an architecture document or diagram first.")
    st.stop()

analysis = get_analysis_by_id(analysis_id)
if analysis is None:
    st.error("Could not load the analysis. Try uploading again.")
    st.stop()

st.write(f"**Analysis:** `{analysis.filename}` - {len(analysis.components)} component(s) detected")

if st.button("Run ATLAS Mapping", type="primary"):
    with st.spinner("Mapping components to ATLAS techniques..."):
        try:
            mapping = run_atlas_mapping(analysis_id)
            st.session_state["last_mapping_id"] = mapping.mapping_id
        except ValueError as e:
            st.error(str(e))
            mapping = None
else:
    mapping = get_latest_mapping(analysis_id)

if mapping and mapping.techniques:
    st.success(f"Mapped to {len(mapping.techniques)} ATLAS technique(s) across {len(mapping.tactic_summary)} tactic(s).")

    st.subheader("Techniques by Tactic")
    st.bar_chart(mapping.tactic_summary)

    st.subheader("Matched Techniques")
    df = pd.DataFrame([t.model_dump() for t in mapping.techniques])
    df = df.rename(columns={
        "technique_id": "ID",
        "technique_name": "Technique",
        "tactic_name": "Tactic",
        "maturity": "Maturity",
        "matched_components": "Triggered By",
    })
    df["Triggered By"] = df["Triggered By"].apply(lambda x: ", ".join(x))
    st.dataframe(
        df[["ID", "Technique", "Tactic", "Maturity", "Triggered By"]],
        use_container_width=True,
        hide_index=True,
    )

    with st.expander("View technique links (atlas.mitre.org)"):
        for t in mapping.techniques:
            st.markdown(f"- [{t.technique_id} — {t.technique_name}]({t.url})")

    st.info("Attack path generation (chaining these techniques into a graph) comes in Phase 5.")
elif mapping is not None:
    st.warning("No techniques matched - this component set isn't covered by the curated mapping yet.")