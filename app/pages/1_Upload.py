"""
Upload page — first step in the user flow.
Lets the user upload a PDF/TXT/MD architecture description or
diagram image and shows the detected AI components immediately.
"""

import streamlit as st
import pandas as pd

from app.ingestion.service import process_uploaded_file
from app.config import settings

st.title("📤 Upload Architecture Document")
st.caption(
    "Upload a PDF, TXT, or Markdown file — or an architecture "
    "diagram image (PNG / JPG) describing your AI system."
)

uploaded_file = st.file_uploader(
    "Choose a file",
    type=["pdf", "txt", "md", "png", "jpg", "jpeg"],
    accept_multiple_files=False,
)

if uploaded_file is not None:
    size_mb = uploaded_file.size / (1024 * 1024)
    if size_mb > settings.MAX_UPLOAD_SIZE_MB:
        st.error(
            f"File too large ({size_mb:.1f} MB). "
            f"Max allowed: {settings.MAX_UPLOAD_SIZE_MB} MB."
        )
    else:
        with st.spinner("Extracting text and detecting components..."):
            try:
                import sys
                print(f"[Upload.py] uploaded_file.name = {uploaded_file.name!r}", file=sys.stdout)
                print(f"[Upload.py] uploaded_file.type = {uploaded_file.type!r}", file=sys.stdout)
                record = process_uploaded_file(uploaded_file.name, uploaded_file)
            except ValueError as e:
                st.error(str(e))
                record = None
            except Exception as e:
                st.error(f"Something went wrong while processing the file: {e}")
                record = None

        if record is not None:
            st.success(f"Analysis complete. ID: `{record.analysis_id}`")

            st.subheader("Detected Components")
            if record.components:
                df = pd.DataFrame([c.model_dump() for c in record.components])
                df = df.rename(columns={
                    "name": "Component",
                    "component_type": "Type",
                    "confidence": "Confidence",
                    "source_text": "Matched Text",
                })
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.warning(
                    "No known AI components were detected in this document."
                )

            if record.raw_text:
                with st.expander("View extracted raw text"):
                    st.text(record.raw_text)
            else:
                st.caption(
                    "📷 Components were extracted from the uploaded diagram image."
                )

            st.session_state["last_analysis_id"] = record.analysis_id
            st.info(
                "This analysis is saved. "
                "Architecture graph building comes in Phase 3."
            )