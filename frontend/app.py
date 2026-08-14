"""Minimal Streamlit prototype UI for the Coptic translator (Phase 1)."""

import os

import requests
import streamlit as st

API_URL = os.environ.get("COPTIC_API_URL", "http://localhost:8000")

st.set_page_config(page_title="Coptic AI Translator", page_icon="✝")

st.title("Coptic AI Translator")
st.caption("Phase 1 MVP — baseline neural model only, no retrieval/validation yet.")

direction_label = st.radio(
    "Direction", ["English → Coptic", "Coptic → English"], horizontal=True
)
direction = "en2cop" if direction_label == "English → Coptic" else "cop2en"

dialect = st.selectbox("Dialect", ["bohairic", "sahidic"])

text = st.text_area("Enter your text", height=120)

if st.button("Translate", type="primary") and text.strip():
    with st.spinner("Translating..."):
        try:
            resp = requests.post(
                f"{API_URL}/translate",
                json={"text": text, "direction": direction, "dialect": dialect},
                timeout=60,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as exc:
            st.error(f"Request failed: {exc}")
        else:
            st.subheader("Translation")
            st.write(data["output_text"])
            st.caption(f"Model: {data['model']}")
            if data.get("confidence") is not None:
                st.caption(f"Confidence: {data['confidence']:.0%}")
