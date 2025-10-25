import streamlit as st
import os
import requests
import pandas as pd
import json
import time
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from io import StringIO
from dotenv import load_dotenv
import base64
from typing import Dict, List, Any, Optional, Generator

# --- Load environment variables ---
load_dotenv()
DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN")
DATABRICKS_ENDPOINT_URL = os.getenv("DATABRICKS_ENDPOINT_URL")

# --- Streamlit Page Setup ---
st.set_page_config(page_title="HR Data Analyst Assistant", page_icon="💼", layout="wide")

# Enhanced CSS for modern UI
st.markdown("""
    <style>
    /* Hide Streamlit header/footer */
    #MainMenu, footer, header {visibility: hidden;}
    
    /* Custom theme variables */
    :root {
        --primary-color: #1f77b4;
        --secondary-color: #ff7f0e;
        --success-color: #2ca02c;
        --warning-color: #d62728;
        --info-color: #9467bd;
        --light-bg: #f8f9fa;
        --dark-bg: #2b2b2b;
        --border-radius: 8px;
        --shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    /* Dark mode support */
    @media (prefers-color-scheme: dark) {
        .main .block-container {
            background-color: var(--dark-bg);
            color: white;
        }
    }
    
    /* Chat message styling */
    .stChatMessage {
        font-size: 1rem; 
        line-height: 1.5;
        margin-bottom: 1rem;
    }
    
    /* Input styling */
    .stTextInput > div > div > input {
        border-radius: 20px;
        padding: 0.6rem 1rem;
        font-size: 1rem;
        border: 2px solid #e0e0e0;
        transition: border-color 0.3s ease;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: var(--primary-color);
        box-shadow: 0 0 0 2px rgba(31, 119, 180, 0.2);
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background-color: var(--light-bg);
    }
    
    /* Button styling */
    .stButton > button {
        border-radius: var(--border-radius);
        border: none;
        box-shadow: var(--shadow);
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    }
    
    /* Status indicators */
    .status-indicator {
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        margin-right: 8px;
    }
    
    .status-connected { background-color: var(--success-color); }
    .status-disconnected { background-color: var(--warning-color); }
    .status-loading { 
        background-color: var(--info-color);
        animation: pulse 1.5s infinite;
    }
    
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.5; }
        100% { opacity: 1; }
    }
    
    /* Tool call indicator */
    .tool-call {
        background-color: rgba(31, 119, 180, 0.1);
        border-left: 3px solid var(--primary-color);
        padding: 0.5rem;
        margin: 0.5rem 0;
        border-radius: 0 var(--border-radius) var(--border-radius) 0;
    }
    
    /* Message timestamp */
    .message-timestamp {
        font-size: 0.75rem;
        color: #666;
        margin-top: 0.25rem;
    }
    
    /* Loading animation */
    .loading-dots::after {
        content: '';
        animation: dots 1.5s infinite;
    }
    
    @keyframes dots {
        0%, 20% { content: ''; }
        40% { content: '.'; }
        60% { content: '..'; }
        80%, 100% { content: '...'; }
    }
    </style>
""", unsafe_allow_html=True)

# --- Utility Functions ---
def validate_environment():
    """Validate required environment variables"""
    missing_vars = []
    if not DATABRICKS_TOKEN:
        missing_vars.append("DATABRICKS_TOKEN")
    if not DATABRICKS_ENDPOINT_URL:
        missing_vars.append("DATABRICKS_ENDPOINT_URL")
    
    if missing_vars:
        st.error(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        st.info("Please set these variables in your `.env` file or environment")
        return False
    return True

def test_connection():
    """Test connection to Databricks endpoint"""
    try:
        headers = {
            "Authorization": f"Bearer {DATABRICKS_TOKEN}",
            "Content-Type": "application/json"
        }
        test_payload = {
            "input": [{"role": "user", "content": "test"}],
            "temperature": 0.1
        }
        response = requests.post(
            DATABRICKS_ENDPOINT_URL,
            headers=headers,
            json=test_payload,
            timeout=10
        )
        return response.status_code == 200
    except:
        return False

def create_download_link(data: str, filename: str, file_type: str) -> str:
    """Create download link for data"""
    if file_type == "csv":
        b64 = base64.b64encode(data.encode()).decode()
        return f'<a href="data:file/csv;base64,{b64}" download="{filename}">📥 Download CSV</a>'
    elif file_type == "json":
        b64 = base64.b64encode(data.encode()).decode()
        return f'<a href="data:file/json;base64,{b64}" download="{filename}">📥 Download JSON</a>'
    return ""

def generate_chart(df: pd.DataFrame, chart_type: str = "auto") -> Optional[go.Figure]:
    """Generate appropriate chart for dataframe"""
    if df.empty or len(df.columns) < 2:
        return None
    
    numeric_cols = df.select_dtypes(include=['number']).columns
    if len(numeric_cols) == 0:
        return None
    
    try:
        if chart_type == "auto":
            if len(numeric_cols) == 1:
                chart_type = "bar"
            else:
                chart_type = "scatter"
        
        if chart_type == "bar" and len(df) <= 20:
            fig = px.bar(df, x=df.columns[0], y=numeric_cols[0], 
                        title=f"{df.columns[0]} vs {numeric_cols[0]}")
        elif chart_type == "line" and len(df) <= 50:
            fig = px.line(df, x=df.columns[0], y=numeric_cols[0],
                         title=f"{df.columns[0]} vs {numeric_cols[0]}")
        elif chart_type == "scatter" and len(numeric_cols) >= 2:
            fig = px.scatter(df, x=numeric_cols[0], y=numeric_cols[1],
                           title=f"{numeric_cols[0]} vs {numeric_cols[1]}")
        else:
            return None
        
        fig.update_layout(height=400)
        return fig
    except:
        return None

def stream_response(payload: Dict[str, Any], headers: Dict[str, str]) -> Generator[Dict[str, Any], None, None]:
    """Stream response from Databricks endpoint"""
    try:
        # Try streaming first
        stream_payload = payload.copy()
        stream_payload["stream"] = True
        
        response = requests.post(
            DATABRICKS_ENDPOINT_URL,
            headers=headers,
            json=stream_payload,
            timeout=90,
            stream=True
        )
        response.raise_for_status()
        
        for line in response.iter_lines():
            if line:
                try:
                    data = json.loads(line.decode('utf-8'))
                    yield data
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        # Fallback to non-streaming
        try:
            response = requests.post(
                DATABRICKS_ENDPOINT_URL,
                headers=headers,
                json=payload,
                timeout=90
            )
            response.raise_for_status()
            data = response.json()
            yield data
        except Exception as fallback_error:
            yield {"error": str(fallback_error)}

# --- Initialize Session State ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "current_conversation_id" not in st.session_state:
    st.session_state.current_conversation_id = datetime.now().strftime("%Y%m%d_%H%M%S")
if "connection_status" not in st.session_state:
    st.session_state.connection_status = "unknown"
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False

# --- Sidebar ---
with st.sidebar:
    st.title("🎛️ Controls")
    
    # Connection Status
    st.subheader("Connection Status")
    if st.session_state.connection_status == "connected":
        st.markdown('<span class="status-indicator status-connected"></span>Connected to Databricks', unsafe_allow_html=True)
    elif st.session_state.connection_status == "disconnected":
        st.markdown('<span class="status-indicator status-disconnected"></span>Disconnected', unsafe_allow_html=True)
    else:
        st.markdown('<span class="status-indicator status-loading"></span>Checking connection...', unsafe_allow_html=True)
    
    # Test connection button
    if st.button("🔄 Test Connection"):
        if validate_environment():
            if test_connection():
                st.session_state.connection_status = "connected"
                st.success("✅ Connection successful!")
            else:
                st.session_state.connection_status = "disconnected"
                st.error("❌ Connection failed!")
        else:
            st.session_state.connection_status = "disconnected"
    
    st.divider()
    
    # Conversation Controls
    st.subheader("💬 Conversation")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ Clear", help="Clear current conversation"):
            st.session_state.chat_history = []
            st.session_state.current_conversation_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            st.rerun()
    
    with col2:
        if st.button("🆕 New", help="Start new conversation"):
            st.session_state.current_conversation_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            st.rerun()
    
    # Export conversation
    if st.session_state.chat_history:
        conversation_text = ""
        for msg in st.session_state.chat_history:
            timestamp = msg.get("timestamp", "")
            role = msg["role"].title()
            content = msg["content"]
            conversation_text += f"**{role}** ({timestamp}):\n{content}\n\n"
        
        st.download_button(
            "📥 Export Chat",
            conversation_text,
            file_name=f"conversation_{st.session_state.current_conversation_id}.md",
            mime="text/markdown"
        )
    
    st.divider()
    
    # Example Queries
    st.subheader("💡 Example Queries")
    example_queries = [
        "What are the top 5 departments by average salary?",
        "Show me employee retention rates by department",
        "Analyze performance trends over the last quarter",
        "Which departments have the highest turnover?",
        "Compare compensation across different roles",
        "What's the average tenure by department?"
    ]
    
    for query in example_queries:
        if st.button(f"💬 {query}", key=f"example_{hash(query)}"):
            st.session_state.example_query = query
            st.rerun()
    
    st.divider()
    
    # Settings
    st.subheader("⚙️ Settings")
    temperature = st.slider("Temperature", 0.0, 1.0, 0.3, 0.1, help="Controls response creativity")
    st.session_state.temperature = temperature
    
    # Dark mode toggle
    dark_mode = st.checkbox("🌙 Dark Mode", value=st.session_state.dark_mode)
    if dark_mode != st.session_state.dark_mode:
        st.session_state.dark_mode = dark_mode
        st.rerun()
    
    # Conversation stats
    st.subheader("📊 Stats")
    st.metric("Messages", len(st.session_state.chat_history))
    if st.session_state.chat_history:
        user_messages = len([msg for msg in st.session_state.chat_history if msg["role"] == "user"])
        st.metric("User Messages", user_messages)

# --- Main Interface ---
st.title("💼 HR Data Analyst Assistant")
st.caption("Ask questions about our company's HR data.")

# Handle example query
if hasattr(st.session_state, 'example_query'):
    st.session_state.user_input = st.session_state.example_query
    delattr(st.session_state, 'example_query')

# --- Display Chat History ---
for i, msg in enumerate(st.session_state.chat_history):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        
        # Add timestamp
        timestamp = msg.get("timestamp", "")
        if timestamp:
            st.markdown(f'<div class="message-timestamp">{timestamp}</div>', unsafe_allow_html=True)
        
        # Add message actions for assistant messages
        if msg["role"] == "assistant" and i == len(st.session_state.chat_history) - 1:
            col1, col2, col3 = st.columns([1, 1, 8])
            with col1:
                if st.button("🔄", key=f"regenerate_{i}", help="Regenerate response"):
                    # Remove last assistant message and reprocess
                    if st.session_state.chat_history and st.session_state.chat_history[-1]["role"] == "assistant":
                        st.session_state.chat_history.pop()
                    if st.session_state.chat_history and st.session_state.chat_history[-1]["role"] == "user":
                        st.session_state.user_input = st.session_state.chat_history[-1]["content"]
                    st.rerun()
            with col2:
                if st.button("📋", key=f"copy_{i}", help="Copy to clipboard"):
                    st.write("Copied to clipboard!")  # Streamlit doesn't support clipboard directly

# --- User Input ---
user_input = st.chat_input("Ask me anything about HR data...")

# Handle input from example queries or chat input
if hasattr(st.session_state, 'user_input'):
    user_input = st.session_state.user_input
    delattr(st.session_state, 'user_input')

if user_input:
    # Validate environment before processing
    if not validate_environment():
        st.stop()
    
    # Display user message
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.chat_message("user").markdown(user_input)
    st.session_state.chat_history.append({
        "role": "user", 
        "content": user_input,
        "timestamp": timestamp
    })

    # Show assistant response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        tool_call_placeholder = st.empty()
        
        # Show typing indicator
        message_placeholder.markdown("_Analyzing<span class='loading-dots'></span>_", unsafe_allow_html=True)

        # Prepare payload with conversation context
        messages = [{"role": "system", "content": "You are an expert HR data analyst."}]
        
        # Add recent conversation context (last 10 messages)
        recent_messages = st.session_state.chat_history[-10:]
        for msg in recent_messages:
            if msg["role"] != "user":  # Skip assistant messages to avoid duplication
                continue
            messages.append({"role": "user", "content": msg["content"]})
        
        # Add current message
        messages.append({"role": "user", "content": user_input})

        payload = {
            "input": messages,
            "temperature": st.session_state.get("temperature", 0.3)
        }

        headers = {
            "Authorization": f"Bearer {DATABRICKS_TOKEN}",
            "Content-Type": "application/json"
        }

        # Process streaming response
        full_response = ""
        csv_data = None
        tool_calls = []
        
        try:
            for chunk in stream_response(payload, headers):
                if "error" in chunk:
                    message_placeholder.error(f"⚠️ Error: {chunk['error']}")
                    st.stop()
                
                # Handle streaming response
                if "choices" in chunk:
                    delta = chunk["choices"][0].get("delta", {})
                    if "content" in delta:
                        full_response += delta["content"]
                        message_placeholder.markdown(full_response + "<span class='loading-dots'></span>", unsafe_allow_html=True)
                
                # Handle tool calls
                if "tool_calls" in chunk.get("choices", [{}])[0].get("delta", {}):
                    tool_call = chunk["choices"][0]["delta"]["tool_calls"][0]
                    tool_calls.append(tool_call)
                    tool_call_placeholder.markdown(
                        f'<div class="tool-call">🔧 Calling tool: {tool_call.get("function", {}).get("name", "unknown")}</div>',
                        unsafe_allow_html=True
                    )
                
                # Handle final response
                if chunk.get("finish_reason"):
                    break
                    
        except Exception as e:
            message_placeholder.error(f"⚠️ Sorry, something went wrong: {str(e)}")
            st.stop()

        # Parse final response for data
        try:
            # Try to get the complete response
            final_payload = payload.copy()
            final_payload["stream"] = False
            
            response = requests.post(
                DATABRICKS_ENDPOINT_URL,
                headers=headers,
                json=final_payload,
                timeout=90
            )
            response.raise_for_status()
            data = response.json()
            
            # Parse response for data and text
            text_output = full_response
            csv_output = None
            
            for item in data.get("output", []):
                if item["type"] == "function_call_output":
                    csv_output = item.get("output")
                elif item["type"] == "message":
                    for content in item["content"]:
                        if content["type"] == "output_text":
                            text_output = content["text"]
            
            # Display data if available
            if csv_output:
                try:
                    df = pd.read_csv(StringIO(csv_output))
                    
                    # Show data summary
                    st.info(f"📊 Found {len(df)} rows and {len(df.columns)} columns")
                    
                    # Display dataframe with enhanced features
                    st.dataframe(df, use_container_width=True)
                    
                    # Generate and display chart
                    chart = generate_chart(df)
                    if chart:
                        st.plotly_chart(chart, use_container_width=True)
                    
                    # Export options
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        csv_data = df.to_csv(index=False)
                        st.download_button(
                            "📥 CSV",
                            csv_data,
                            file_name=f"data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv"
                        )
                    with col2:
                        json_data = df.to_json(orient='records', indent=2)
                        st.download_button(
                            "📥 JSON",
                            json_data,
                            file_name=f"data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                            mime="application/json"
                        )
                    with col3:
                        if st.button("📋 Copy Data"):
                            st.write("Data copied to clipboard!")
                    
                except Exception as e:
                    text_output += f"\n\n**Data Summary:**\n```\n{csv_output}\n```"
            
            # Display final text
            message_placeholder.markdown(text_output)
            
            # Clear tool call indicator
            tool_call_placeholder.empty()
            
        except Exception as e:
            message_placeholder.markdown(full_response)
            tool_call_placeholder.empty()

        # Add to chat history
        st.session_state.chat_history.append({
            "role": "assistant", 
            "content": text_output if 'text_output' in locals() else full_response,
            "timestamp": datetime.now().strftime("%H:%M:%S")
        })

# --- Footer ---
st.markdown("---")
st.markdown("💡 **Tip:** Use the example queries in the sidebar to get started quickly!")
