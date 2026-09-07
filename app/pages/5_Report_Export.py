"""
Report Export page — Phase 8.
Generates and serves the downloadable PDF security report.
"""

import streamlit as st
from app.reports.service import build_report
from app.attack_paths.service import get_attack_path_record
from app.risk_scoring.scoring_summary import compute_overall_score

st.title("📋 Security Report Export")
st.caption("Generate and download a full PDF security report for this analysis.")

# ── Resolve analysis ID ──────────────────────────────────────────────────────
analysis_id = st.session_state.get("last_analysis_id", "")

with st.expander("Load a different analysis by ID"):
    manual_id = st.text_input("Analysis ID", value=analysis_id)
    if st.button("Load"):
        analysis_id = manual_id.strip()

if not analysis_id:
    st.info("Complete the Upload and Attack Paths steps first.")
    st.stop()

# ── Preview what will be in the report ───────────────────────────────────────
ap_record = get_attack_path_record(analysis_id)

if ap_record and ap_record.attack_paths:
    overall = compute_overall_score(ap_record)

    risk_icons = {"High": "🔴", "Medium": "🟡", "Low": "🟢", "Unknown": "⚪"}
    icon = risk_icons.get(overall["overall_risk_level"], "⚪")

    st.subheader("Report Preview")

    c1, c2, c3 = st.columns(3)
    c1.metric("Overall Risk",   f"{icon} {overall['overall_risk_level']}")
    c2.metric("Security Score", f"{overall['overall_score']:.1f}/100")
    c3.metric("Attack Paths",   overall["total_paths"])

    st.markdown("**Report will include:**")
    st.markdown("""
    ✅ Cover Page with analysis metadata  
    ✅ Executive Summary  
    ✅ Detected Components table  
    ✅ MITRE ATLAS Technique Mapping  
    ✅ Attack Paths with step-by-step breakdown  
    ✅ Risk Assessment with AI explanations  
    ✅ Prioritised Mitigation Recommendations  
    ✅ Final Security Score with remediation guidance  
    """)
    st.divider()
else:
    st.warning(
        "No attack paths found for this analysis. "
        "Go to the **Attack Paths** page and generate paths first."
    )
    st.stop()

# ── Generate and download ─────────────────────────────────────────────────────
if st.button("📥 Generate & Download PDF Report", type="primary"):
    with st.spinner("Building your security report..."):
        pdf_bytes, result = build_report(analysis_id)

    if pdf_bytes is None:
        st.error(result)
    else:
        st.success("✅ Report generated successfully!")
        st.download_button(
            label="⬇️ Download PDF Report",
            data=pdf_bytes,
            file_name=result,
            mime="application/pdf",
            type="primary",
        )
        st.caption(f"File: `{result}`")

st.session_state["last_analysis_id"] = analysis_id