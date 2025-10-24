import os
import requests
import streamlit as st
import pandas as pd
from io import StringIO
from dotenv import load_dotenv

# -----------------------------
# Load env
# -----------------------------
load_dotenv()
DATABRICKS_ENDPOINT_URL = os.getenv("DATABRICKS_ENDPOINT_URL")
DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN")

# -----------------------------
# Page config & style
# -----------------------------
st.set_page_config(page_title="HR Analytics Assistant", layout="centered")
st.markdown(
    """
    <style>
    body { background-color: #0E1117; color: #FAFAFA; }
    #MainMenu, footer, header { visibility: hidden; }
    [data-testid="stChatMessage-user"] {
        background: linear-gradient(145deg, #202124, #2b2b2b) !important;
        color: #fff !important;
        border-radius: 12px !important;
        padding: 0.9rem !important;
    }
    [data-testid="stChatMessage-assistant"] {
        background: linear-gradient(145deg, #1a1a1a, #252525) !important;
        color: #f5f5f5 !important;
        border-radius: 12px !important;
        padding: 0.9rem !important;
    }
    .loading-container {
        display:flex;justify-content:center;align-items:center;flex-direction:column;margin-top:1rem;
    }
    .loader {
        border: 4px solid #2a2a2a;
        border-top: 4px solid #FFB86B;
        border-radius:50%;
        width:28px;height:28px;animation:spin 1s linear infinite;margin-bottom:8px;
    }
    @keyframes spin {0%{transform:rotate(0deg);}100%{transform:rotate(360deg);}}
    .scroll-box { max-height: 380px; overflow-y: auto; background-color: #1f1f1f; padding: 0.9rem; border-radius: 8px; border:1px solid #333; color:#f5f5f5; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("💼 HR Analytics Assistant")
st.caption("Ask about HR data — e.g. average tenure, top departments by salary, retention insights.")

# -----------------------------
# Chat memory
# -----------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

# render previous messages
for m in st.session_state.messages:
    role = m.get("role", "assistant")
    with st.chat_message(role):
        st.markdown(m.get("content", ""))

# input
prompt = st.chat_input("Ask me anything about the HR data...")

if prompt:
    # append & show user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # centered (non-bubble) loading indicator
    loading_placeholder = st.empty()
    with loading_placeholder.container():
        st.markdown(
            """
            <div class="loading-container">
                <div class="loader"></div>
                <div><i>Analyzing HR data...</i></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # build payload exactly like your guide
    payload = {
        "input": [
            {"role": "system", "content": "You are an expert HR data analyst."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
    }

    headers = {
        "Authorization": f"Bearer {DATABRICKS_TOKEN}",
        "Content-Type": "application/json",
    }

    # call endpoint
    try:
        resp = requests.post(
            DATABRICKS_ENDPOINT_URL, headers=headers, json=payload, timeout=120
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        loading_placeholder.empty()
        with st.chat_message("assistant"):
            st.error("Sorry, something went wrong while analyzing the data. Please try again.")
        st.session_state.messages.append({"role": "assistant", "content": "Error analyzing request."})
        st.stop()

    # remove spinner
    loading_placeholder.empty()

    # --- robust parsing of databricks agent response ---
    text_output = None
    csv_output = None

    # typical agent responses include 'output' (list) or 'outputs' or 'predictions'
    # handle many shapes defensively
    if isinstance(data, dict):
        # 1) legacy agent style: "output": [ ... ]
        output_items = data.get("output") or data.get("outputs") or data.get("outputs") or data.get("predictions")
        if isinstance(output_items, dict):
            # sometimes outputs is a dict with content
            output_items = [output_items]
        if not output_items and "predictions" in data and isinstance(data["predictions"], list):
            output_items = data["predictions"]

        if isinstance(output_items, list):
            for item in output_items:
                if not isinstance(item, dict):
                    continue
                itype = item.get("type", "").lower()
                if itype == "function_call_output" or itype == "function_call_output":
                    # structured CSV output commonly in 'output'
                    csv_output = item.get("output") or item.get("result") or item.get("content")
                elif itype == "message" or itype == "assistant_message":
                    for c in item.get("content", []):
                        if isinstance(c, dict) and c.get("type") in ("output_text", "text"):
                            text_output = c.get("text") or c.get("content")
                        elif isinstance(c, str):
                            text_output = c
                else:
                    # fallback: some agents put text in 'content' or 'text'
                    if "content" in item and isinstance(item["content"], str):
                        text_output = item["content"]

        # fallback shapes
        if not text_output:
            # databricks sometimes returns outputs[0].content as string
            if "outputs" in data and isinstance(data["outputs"], list) and data["outputs"]:
                first = data["outputs"][0]
                if isinstance(first, dict):
                    text_output = first.get("content") or text_output
            elif "content" in data:
                text_output = data.get("content")

    # If still nothing, try raw text
    if not text_output:
        try:
            raw = resp.text
            if raw:
                text_output = raw
        except:
            text_output = "No content returned."

    # --- display assistant message (only now) ---
    with st.chat_message("assistant"):
        # if csv-like output, try to render table
        if csv_output:
            try:
                df = pd.read_csv(StringIO(csv_output))
                st.dataframe(df, use_container_width=True, height=360)
                # also include a natural language summary if present
                if text_output:
                    st.markdown(f'<div class="scroll-box">{text_output}</div>', unsafe_allow_html=True)
            except Exception:
                # if csv parse fails, show as text in scroll box
                st.markdown(f'<div class="scroll-box">{csv_output}</div>', unsafe_allow_html=True)
                if text_output:
                    st.markdown(f'<div class="scroll-box">{text_output}</div>', unsafe_allow_html=True)
        else:
            # plain text response
            st.markdown(f'<div class="scroll-box">{text_output}</div>', unsafe_allow_html=True)

    # append assistant to history
    st.session_state.messages.append({"role": "assistant", "content": text_output})
