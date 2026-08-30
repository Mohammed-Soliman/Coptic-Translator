"""Minimal Streamlit prototype UI for the Coptic translator."""

import os

import requests
import streamlit as st

API_URL = os.environ.get("COPTIC_API_URL", "http://localhost:8000")

st.set_page_config(page_title="Coptic AI Translator", page_icon="𓂀")

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Coptic&display=swap');
    .coptic-text {
        font-family: 'Noto Sans Coptic', serif;
        font-size: 1.8rem;
        line-height: 1.6;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Coptic AI Translator")
st.caption(
    "Minimal dev prototype. For the full Ancient-Egyptian/Coptic-styled "
    "interface (Translator, Lexicon, Manuscripts, Lab Notes), run the API "
    "and open http://localhost:8000/app/coptic_translator.html instead."
)

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
            if direction == "en2cop":
                st.markdown(
                    f'<div class="coptic-text">{data["output_text"]}</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.write(data["output_text"])
            st.caption(f"Model: {data['model']}")

            col1, col2 = st.columns(2)
            with col1:
                if data.get("confidence") is not None:
                    st.metric("Model confidence", f"{data['confidence']:.0%}")
                else:
                    st.metric("Model confidence", "n/a")
            with col2:
                if data.get("dictionary_coverage") is not None:
                    st.metric(
                        "Dictionary coverage", f"{data['dictionary_coverage']:.0%}"
                    )
                else:
                    st.metric("Dictionary coverage", "n/a")

            st.caption(
                "These are two independent, uncalibrated signals - not a combined "
                "accuracy score. Low coverage just means our small starter lexicon "
                "doesn't recognize those words yet, not that the translation is wrong."
            )
