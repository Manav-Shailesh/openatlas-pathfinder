"""
OpenATLAS Pathfinder — Streamlit entrypoint.
Phase 1 version: just confirms the app boots and MongoDB is reachable.
Phase 7 will expand this into the full multipage UI.
"""

import streamlit as st
from app.config import settings
from app.db.mongo_client import check_connection

st.set_page_config(
    page_title=settings.APP_NAME,
    page_icon="🛡️",
    layout="wide",
)

st.title("🛡️ OpenATLAS Pathfinder")
st.caption("AI Threat Modeling & Attack Path Generation Platform")

st.divider()

st.subheader("System Status")

db_ok = check_connection()

col1, col2 = st.columns(2)
with col1:
    st.metric("Environment", settings.APP_ENV)
with col2:
    if db_ok:
        st.success("MongoDB: Connected ✅")
    else:
        st.error("MongoDB: Not reachable ❌ - check your MONGO_URI in .env")

st.info(
    "Phase 1 complete: project structure, config, and database layer are in place.\n\n"
    "Upload/analysis pages will be added in later phases."
)