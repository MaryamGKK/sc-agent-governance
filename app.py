import streamlit as st
import os
import requests
import pandas as pd
from io import StringIO
from dotenv import load_dotenv

# --- Load environment variables ---
load_dotenv()
DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN")
DATABRICKS_ENDPOINT_URL = os.getenv("DATABRICKS_ENDPOINT_URL")

# --- Streamlit Page Setup ---
st.set_page_config(page_title="HR Data Analyst Assistant", page_icon="💼", layout="wide")

st.markdown("""
    <style>
    /* Hide Streamlit header/footer */
    #MainMenu, footer, header {visibility: hidden;}

    /* Chat-like layout */
    .stChatMessage {font-size: 1rem; line-height: 1.5;}
    .stTextInput > div > div > input {
        border-radius: 20px;
        padding: 0.6rem 1rem;
        font-size: 1rem;
    }
    </style>
""", unsafe_allow_html=True)

st.title("💼 HR Data Analyst Assistant")
st.caption("Ask questions about our company's HR data.")

# --- Chat History ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# --- Display previous messages ---
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- User input ---
user_input = st.chat_input("Ask me anything about HR data...")

if user_input:
    # Display user message
    st.chat_message("user").markdown(user_input)
    st.session_state.chat_history.append({"role": "user", "content": user_input})

    # Show assistant typing indicator
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown("_Analyzing..._")

    # Prepare payload
    payload = {
        "input": [
            {"role": "system", "content": "You are an expert HR data analyst."},
            {"role": "user", "content": user_input}
        ],
        "temperature": 0.3
    }

    headers = {
        "Authorization": f"Bearer {DATABRICKS_TOKEN}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(
            DATABRICKS_ENDPOINT_URL,
            headers=headers,
            json=payload,
            timeout=90
        )
        response.raise_for_status()
        data = response.json()
    except Exception:
        message_placeholder.error("⚠️ Sorry, something went wrong while analyzing the data.")
        st.stop()

    # Parse response
    text_output = None
    csv_output = None

    for item in data.get("output", []):
        if item["type"] == "function_call_output":
            csv_output = item.get("output")
        elif item["type"] == "message":
            for content in item["content"]:
                if content["type"] == "output_text":
                    text_output = content["text"]

    # Display final message
    final_text = ""
    if csv_output:
        try:
            df = pd.read_csv(StringIO(csv_output))
            st.dataframe(df, use_container_width=True)
        except Exception:
            final_text += f"**Data Summary:**\n```\n{csv_output}\n```\n"

    if text_output:
        final_text += text_output

    message_placeholder.markdown(final_text)
    st.session_state.chat_history.append({"role": "assistant", "content": final_text})
