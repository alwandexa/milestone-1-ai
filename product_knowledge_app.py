import streamlit as st
import requests
import json
from typing import List, Dict, Optional, Any
import uuid
from datetime import datetime
import io
from PIL import Image
import asyncio
import aiohttp
import time
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Custom CSS for modern blueish theme
st.set_page_config(
    page_title="iScaps Product Knowledge",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS styling
st.markdown("""
<style>
    /* Main theme colors */
    :root {
        --primary-blue: #1e3a8a;
        --secondary-blue: #3b82f6;
        --accent-blue: #60a5fa;
        --light-blue: #dbeafe;
        --gradient-start: #1e40af;
        --gradient-end: #3b82f6;
        --text-dark: #1f2937;
        --text-light: #6b7280;
        --bg-white: #ffffff;
        --bg-light: #f8fafc;
    }

    /* Global styling */
    .main {
        background: linear-gradient(135deg, var(--gradient-start) 0%, var(--gradient-end) 100%);
        min-height: 100vh;
    }

    /* Header styling */
    .main .block-container {
        background: var(--bg-white);
        border-radius: 15px;
        padding: 2rem;
        margin: 1rem;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
        border: 1px solid rgba(59, 130, 246, 0.1);
    }

    /* Title styling */
    h1 {
        color: var(--text-dark);
        font-weight: 700;
        font-size: 2.5rem;
        margin-bottom: 1rem;
        text-align: center;
        text-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }

    /* Sidebar styling */
    .css-1d391kg {
        background: linear-gradient(180deg, #1e40af 0%, #3b82f6 50%, #60a5fa 100%);
        border-radius: 0 15px 15px 0;
        box-shadow: 4px 0 20px rgba(0, 0, 0, 0.2);
        border-right: 3px solid #1e3a8a;
    }

    /* Enhanced sidebar containers */
    .sidebar-container {
        background: rgba(255, 255, 255, 0.25);
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        border: 2px solid rgba(255, 255, 255, 0.4);
        backdrop-filter: blur(15px);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
    }

    /* Persona badge styling */
    .persona-badge {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        display: inline-block;
        margin: 0.5rem 0;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
        border: 1px solid rgba(255, 255, 255, 0.2);
    }

    /* Persona selection styling */
    .persona-option {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 8px;
        padding: 0.75rem;
        margin: 0.5rem 0;
        border: 1px solid rgba(255, 255, 255, 0.2);
        transition: all 0.3s ease;
    }

    .persona-option:hover {
        background: rgba(255, 255, 255, 0.2);
        transform: translateY(-2px);
    }

    .persona-option.selected {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-color: rgba(255, 255, 255, 0.4);
    }

    /* Dashboard specific styling */
    .dashboard-container {
        background: var(--bg-white);
        border-radius: 15px;
        padding: 2rem;
        margin: 1rem 0;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
        border: 1px solid rgba(59, 130, 246, 0.1);
    }

    /* Metric cards styling */
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 12px;
        padding: 1.5rem;
        margin: 0.5rem 0;
        color: white;
        text-align: center;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
        transition: transform 0.3s ease;
    }

    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
    }

    /* Chart containers */
    .chart-container {
        background: var(--bg-white);
        border-radius: 10px;
        padding: 1rem;
        margin: 1rem 0;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
        border: 1px solid rgba(59, 130, 246, 0.1);
    }

    /* Section headers */
    .section-header {
        color: var(--text-dark);
        font-weight: 600;
        font-size: 1.2rem;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid var(--accent-blue);
    }

    /* Activity expanders */
    .activity-expander {
        background: var(--bg-light);
        border-radius: 8px;
        margin: 0.5rem 0;
        border-left: 4px solid var(--accent-blue);
    }

    /* Vivid button styling */
    .stButton > button {
        background: linear-gradient(135deg, #10b981, #059669);
        color: white;
        border: 2px solid rgba(255, 255, 255, 0.3);
        border-radius: 12px;
        padding: 1rem 1.5rem;
        font-weight: 700;
        font-size: 1rem;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 0 6px 20px rgba(16, 185, 129, 0.4);
        text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
        letter-spacing: 0.5px;
    }

    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(16, 185, 129, 0.6);
    }

    /* Metric cards for monitoring dashboard */
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 12px;
        padding: 1.5rem;
        color: white;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
        margin: 0.5rem 0;
    }

    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }

    .metric-label {
        font-size: 0.9rem;
        opacity: 0.9;
    }



    /* Chat message styling */
    .chat-message {
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 12px;
        border: 2px solid rgba(59, 130, 246, 0.1);
    }

    .user-message {
        # background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%);
        border-color: #3b82f6;
    }

    .assistant-message {
        # background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
        border-color: #0ea5e9;
    }

    /* Confidence score styling */
    .confidence-high {
        color: #059669;
        font-weight: 600;
    }

    .confidence-medium {
        color: #d97706;
        font-weight: 600;
    }

    .confidence-low {
        color: #dc2626;
        font-weight: 600;
    }

    /* Multimodal content styling */
    .multimodal-badge {
        background: linear-gradient(135deg, #8b5cf6, #a855f7);
        color: white;
        padding: 0.25rem 0.5rem;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 600;
        display: inline-block;
        margin-left: 0.5rem;
    }

    .image-preview {
        border: 2px solid #3b82f6;
        border-radius: 8px;
        padding: 0.5rem;
        margin: 0.5rem 0;
        background: #f8fafc;
    }

    .message-image {
        max-width: 250px;
        border-radius: 8px;
        margin: 0.5rem 0;
        border: 2px solid rgba(255, 255, 255, 0.3);
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    }

    .message-image-container {
        margin-top: 0.5rem;
        display: flex;
        justify-content: flex-end;
    }

    /* Modern chat layout styling */
    .chat-container {
        height: calc(100vh - 300px);
        overflow-y: auto;
        padding: 1rem;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        background: #f9fafb;
        margin-bottom: 1rem;
        position: relative;
    }

    /* Main container */
    .main .block-container {
        padding: 1rem;
        margin: 1rem;
        min-height: 100vh;
    }


    /* Message styling */
    .message-container {
        margin-bottom: 1.5rem;
        max-width: 100%;
    }

    .user-message {
        display: flex;
        justify-content: flex-end;
        margin-bottom: 1rem;
    }

    .assistant-message {
        display: flex;
        justify-content: flex-start;
        margin-bottom: 1rem;
    }

    .message-bubble {
        max-width: 70%;
        padding: 0.75rem 1rem;
        border-radius: 18px;
        word-wrap: break-word;
        line-height: 1.4;
        font-size: 0.95rem;
    }

    .user-bubble {
        background: linear-gradient(135deg, #3b82f6 0%, #1e40af 100%);
        color: white;
        box-shadow: 0 2px 8px rgba(59, 130, 246, 0.3);
    }

    .assistant-bubble {
        background: white;
        border: 1px solid #e5e7eb;
        color: #1f2937;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    }

    /* Ensure chat messages don't overflow */
    .stChatMessage {
        margin-bottom: 1rem;
    }

    /* Hide default chat input container */
    .stChatInputContainer {
        display: none;
    }

    /* Chat input container - unified design like Cursor */
    .chat-input-container {
        display: flex;
        align-items: center;
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 0.75rem 1rem;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
        gap: 0.75rem;
        min-height: 56px;
    }

    .chat-input-field {
        flex: 1;
        border: none;
        outline: none;
        font-size: 1rem;
        padding: 0.5rem 0;
        background: transparent;
        color: #1f2937;
        min-height: 24px;
        resize: none;
    }

    .chat-input-field::placeholder {
        color: #9ca3af;
    }

    .input-actions {
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    .attachment-button {
        background: transparent;
        border: none;
        border-radius: 6px;
        padding: 0.5rem;
        cursor: pointer;
        transition: all 0.2s ease;
        display: flex;
        align-items: center;
        justify-content: center;
        width: 36px;
        height: 36px;
        color: #6b7280;
    }

    .attachment-button:hover {
        background: #e5e7eb;
        color: #374151;
    }

    .send-button {
        background: #3b82f6;
        color: white;
        border: none;
        border-radius: 6px;
        padding: 0.5rem 1rem;
        cursor: pointer;
        transition: all 0.2s ease;
        font-weight: 500;
        font-size: 0.875rem;
        min-width: 60px;
        height: 36px;
        display: flex;
        align-items: center;
        justify-content: center;
        float: right;
    }

    .send-button:hover {
        background: #2563eb;
        transform: translateY(-1px);
    }

    .send-button:disabled {
        background: #9ca3af;
        cursor: not-allowed;
        transform: none;
    }

    .file-preview {
        background: #f9fafb;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: 0.5rem;
        margin-top: 0.5rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    .file-preview img {
        width: 40px;
        height: 40px;
        object-fit: cover;
        border-radius: 4px;
    }

    .remove-file {
        background: #ef4444;
        color: white;
        border: none;
        border-radius: 4px;
        padding: 0.25rem 0.5rem;
        cursor: pointer;
        font-size: 0.75rem;
    }

    /* Modern chat header */
    .chat-header {
        background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%);
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 12px 12px 0 0;
        margin-bottom: 1.5rem;
        font-weight: 600;
        font-size: 1.2rem;
    }

    /* Quick action buttons */
    .quick-action-btn {
        background: linear-gradient(135deg, #f3f4f6 0%, #e5e7eb 100%);
        border: 1px solid #d1d5db;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        margin: 0.25rem;
        font-size: 0.875rem;
        transition: all 0.2s ease;
    }

    .quick-action-btn:hover {
        background: linear-gradient(135deg, #e5e7eb 0%, #d1d5db 100%);
        transform: translateY(-1px);
    }

    /* Typing indicator */
    .typing-indicator {
        display: inline-block;
        animation: blink 1s infinite;
        color: #3b82f6;
        font-weight: bold;
    }

    @keyframes blink {
        0%, 50% { opacity: 1; }
        51%, 100% { opacity: 0; }
    }

    /* Streaming message styling */
    .streaming-message {
        opacity: 0.8;
        transition: opacity 0.3s ease;
    }

    .streaming-message.complete {
        opacity: 1;
    }

    /* Streaming area styling */
    .streaming-area {
        background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
        border: 2px solid #3b82f6;
        border-radius: 12px;
        padding: 1rem;
        margin: 1rem 0;
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.15);
    }

    .streaming-header {
        color: #1e40af;
        font-weight: 600;
        margin-bottom: 0.5rem;
    }

    .streaming-content {
        color: #1f2937;
        line-height: 1.5;
        font-size: 0.95rem;
    }

    .streaming-cursor {
        animation: blink 1s infinite;
        color: #3b82f6;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# API configuration
API_BASE_URL = "http://localhost:8000"

def get_api_url(endpoint: str) -> str:
    """Get full API URL for endpoint"""
    return f"{API_BASE_URL}{endpoint}"

def upload_document(file_content: bytes, filename: str, product_group: Optional[str] = None) -> Dict:
    """Upload document to API"""
    files = {"file": (filename, file_content, "application/pdf")}
    data = {}
    if product_group:
        data["product_group"] = product_group
    
    response = requests.post(get_api_url("/documents/upload"), files=files, data=data)
    response.raise_for_status()
    return response.json()

def chat_with_documents(query: str, image_data: Optional[bytes] = None, session_id: Optional[str] = None, persona_name: Optional[str] = None) -> Dict:
    """Unified chat function that works like ChatGPT - supports both text and images with optional persona"""
    files = {}
    data = {
        "query": query,
        "session_id": session_id
    }
    
    # Add persona if specified
    if persona_name:
        data["persona_name"] = persona_name
    
    if image_data:
        files["image"] = ("image.jpg", image_data, "image/jpeg")
    
    # Always use the unified /chat endpoint
    response = requests.post(get_api_url("/chat"), files=files, data=data)
    response.raise_for_status()
    return response.json()

def chat_with_documents_stream(query: str, image_data: Optional[bytes] = None, session_id: Optional[str] = None, persona_name: Optional[str] = None):
    """Streaming chat function that works like ChatGPT - supports both text and images with optional persona"""
    files = {}
    data = {
        "query": query,
        "session_id": session_id
    }
    
    # Add persona if specified
    if persona_name:
        data["persona_name"] = persona_name
    
    if image_data:
        files["image"] = ("image.jpg", image_data, "image/jpeg")
    
    # Always use the unified /chat/stream endpoint
    response = requests.post(get_api_url("/chat/stream"), files=files, data=data, stream=True)
    response.raise_for_status()
    return response





def process_streaming_response(response, message_index: int):
    """Process streaming response and update the UI in real-time"""
    full_content = ""
    metadata = {}
    chain_of_thought = []
    
    # Create a placeholder for real-time updates in the streaming area
    streaming_placeholder = st.empty()
    cot_placeholder = st.empty()
    
    try:
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data: '):
                    try:
                        data = json.loads(line_str[6:])  # Remove 'data: ' prefix
                        
                        if data.get('type') == 'metadata':
                            # Store metadata and chain of thought
                            metadata = {
                                "sources": data.get("sources", []),
                                "multimodal_content": data.get("multimodal_content", False),
                                "extracted_text": data.get("extracted_text"),
                                "persona_metadata": data.get("persona_metadata", {})
                            }
                            chain_of_thought = data.get("chain_of_thought", [])
                            
                            # Display chain of thought in expander
                            with cot_placeholder.container():
                                display_chain_of_thought(chain_of_thought)
                            
                        elif data.get('type') == 'content':
                            # Append content
                            full_content += data.get('content', '')
                            
                            # Update the message in session state
                            st.session_state.messages[message_index]["content"] = full_content
                            st.session_state.messages[message_index]["metadata"] = metadata
                            st.session_state.messages[message_index]["persona_metadata"] = metadata.get("persona_metadata", {})
                            st.session_state.messages[message_index]["is_streaming"] = True
                            st.session_state.messages[message_index]["chain_of_thought"] = chain_of_thought
                            
                            # Update the streaming area with current content
                            with streaming_placeholder.container():
                                st.markdown("""
                                <div class="streaming-area">
                                    <div class="streaming-header">🤖 Assistant is typing...</div>
                                    <div class="streaming-content">
                                        """ + full_content + """<span class="streaming-cursor">▋</span>
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)
                            
                        elif data.get('type') == 'error':
                            st.error(f"Error: {data.get('content', 'Unknown error')}")
                            break
                        elif data.get('type') == 'end':
                            # Mark streaming as complete
                            st.session_state.messages[message_index]["is_streaming"] = False
                            break
                    except json.JSONDecodeError:
                        # Skip malformed JSON lines instead of breaking
                        continue
                    except Exception as parse_error:
                        # Log parse errors but don't break the stream
                        print(f"Parse error in streaming: {str(parse_error)}")
                        continue
    except Exception as e:
        # Log streaming errors but don't throw to avoid triggering fallback
        print(f"Streaming error: {str(e)}")
        st.error(f"Streaming error: {str(e)}")
        # Don't set full_content to error message to avoid triggering fallback
    
    return full_content, metadata, chain_of_thought

def list_documents() -> List[Dict]:
    """List all documents"""
    response = requests.get(get_api_url("/documents"))
    response.raise_for_status()
    return response.json()

def get_product_groups() -> List[Dict]:
    """Get available product groups"""
    response = requests.get(get_api_url("/product-groups"))
    response.raise_for_status()
    return response.json()

def delete_document(document_id: str) -> Dict:
    """Delete a document"""
    response = requests.delete(get_api_url(f"/documents/{document_id}"))
    response.raise_for_status()
    return response.json()

def create_new_conversation():
    """Create a new conversation session"""
    if "conversation_id" not in st.session_state:
        st.session_state.conversation_id = str(uuid.uuid4())
    else:
        st.session_state.conversation_id = str(uuid.uuid4())
    
    if "messages" not in st.session_state:
        st.session_state.messages = []
    else:
        st.session_state.messages = []

def get_current_conversation():
    """Get current conversation ID"""
    if "conversation_id" not in st.session_state:
        st.session_state.conversation_id = str(uuid.uuid4())
    return st.session_state.conversation_id

def get_confidence_class(score: float) -> str:
    """Get CSS class for confidence score"""
    if score >= 0.8:
        return "confidence-high"
    elif score >= 0.6:
        return "confidence-medium"
    else:
        return "confidence-low"

def display_chain_of_thought(chain_of_thought: List[Dict[str, Any]]):
    """Display chain of thought steps in the UI using Streamlit expander"""
    if not chain_of_thought:
        return
    
    with st.expander("🧠 Chain of Thought", expanded=False):
        for i, step in enumerate(chain_of_thought):
            agent = step.get("agent", "Unknown Agent")
            thought = step.get("thought", "")
            status = step.get("status", "unknown")
            details = step.get("details", {})
            
            # Create status badge with color coding
            status_colors = {
                "started": "🔵",
                "completed": "🟢", 
                "error": "🔴",
                "warning": "🟡",
                "unknown": "⚪"
            }
            status_icon = status_colors.get(status, "⚪")
            
            # Display the step
            st.markdown(f"**{status_icon} {agent}**")
            st.write(f"*{thought}*")
            
            # Show details if available
            if details:
                details_text = []
                for key, value in details.items():
                    if isinstance(value, (int, float)):
                        details_text.append(f"**{key}**: {value}")
                    elif isinstance(value, str):
                        details_text.append(f"**{key}**: {value[:100]}{'...' if len(value) > 100 else ''}")
                    else:
                        details_text.append(f"**{key}**: {str(value)[:100]}{'...' if len(str(value)) > 100 else ''}")
                
                if details_text:
                    st.markdown("**Details:**")
                    for detail in details_text:
                        st.markdown(f"• {detail}")
            
            # Add separator between steps
            if i < len(chain_of_thought) - 1:
                st.divider()

# Monitoring Dashboard Functions
def fetch_analytics(days: int = 30):
    """Fetch analytics data from the API"""
    try:
        response = requests.get(get_api_url(f"/dashboard/analytics?days={days}"))
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Failed to fetch analytics: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Error fetching analytics: {str(e)}")
        return None

def fetch_recent_events(limit: int = 50):
    """Fetch recent events from the API"""
    try:
        response = requests.get(get_api_url(f"/dashboard/recent-events?limit={limit}"))
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Failed to fetch recent events: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Error fetching recent events: {str(e)}")
        return None

def create_metric_card(title: str, value: str, subtitle: str = ""):
    """Create a metric card with custom styling"""
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">{value}</div>
        <div class="metric-label">{title}</div>
        {f'<div style="font-size: 0.8rem; opacity: 0.8; margin-top: 0.5rem;">{subtitle}</div>' if subtitle else ''}
    </div>
    """, unsafe_allow_html=True)

def create_daily_activity_chart(daily_activity):
    """Create a daily activity line chart"""
    if not daily_activity:
        return None
    
    df = pd.DataFrame(daily_activity)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    
    fig = px.line(df, x='date', y='count', 
                  title="Daily Activity",
                  labels={'count': 'Number of Queries', 'date': 'Date'},
                  line_shape='linear',
                  render_mode='svg')
    
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#1f2937'),
        title_font_size=16,
        showlegend=False
    )
    
    fig.update_traces(line_color='#3b82f6', line_width=3)
    
    return fig

def create_question_type_chart(question_types):
    """Create a question type distribution chart"""
    if not question_types:
        return None
    
    df = pd.DataFrame(question_types)
    
    fig = px.pie(df, values='count', names='type', 
                 title="Question Type Distribution",
                 color_discrete_sequence=px.colors.qualitative.Set3)
    
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#1f2937'),
        title_font_size=16
    )
    
    return fig

def create_product_group_chart(product_groups):
    """Create a product group distribution chart"""
    if not product_groups:
        return None
    
    df = pd.DataFrame(product_groups)
    
    fig = px.bar(df, x='group', y='count',
                 title="Product Group Distribution",
                 labels={'count': 'Number of Queries', 'group': 'Product Group'},
                 color='count',
                 color_continuous_scale='Blues')
    
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#1f2937'),
        title_font_size=16,
        xaxis_tickangle=-45
    )
    
    return fig

def create_performance_gauge(value: float, title: str, min_val: float = 0, max_val: float = 100):
    """Create a gauge chart for performance metrics"""
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=value,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': title},
        delta={'reference': max_val * 0.8},
        gauge={
            'axis': {'range': [min_val, max_val]},
            'bar': {'color': "#3b82f6"},
            'steps': [
                {'range': [min_val, max_val * 0.6], 'color': "#ef4444"},
                {'range': [max_val * 0.6, max_val * 0.8], 'color': "#f59e0b"},
                {'range': [max_val * 0.8, max_val], 'color': "#10b981"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': max_val * 0.9
            }
        }
    ))
    
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#1f2937'),
        title_font_size=16
    )
    
    return fig



def show_monitoring_dashboard():
    """Display the monitoring dashboard"""
    st.title("📊 iScaps Monitoring Dashboard")
    st.markdown("---")
    
    # Sidebar for controls
    with st.sidebar:
        st.markdown('<div class="sidebar-container">', unsafe_allow_html=True)
        
        st.header("🎛️ Dashboard Controls")
        
        # Time range selector
        days = st.selectbox(
            "Time Range",
            [7, 14, 30, 60, 90],
            index=2,
            help="Select the number of days to analyze"
        )
        
        # Auto-refresh toggle
        auto_refresh = st.checkbox("Auto-refresh", value=True, help="Automatically refresh data every 30 seconds")
        
        # Refresh button
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.rerun()
        
        st.markdown("---")
        st.markdown("### 📈 Quick Stats")
        
        # Fetch summary stats
        try:
            summary_response = requests.get(get_api_url("/dashboard/stats/summary"))
            if summary_response.status_code == 200:
                summary = summary_response.json()
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Total Queries", summary.get("total_queries", 0))
                    st.metric("Success Rate", f"{summary.get('success_rate', 0):.1f}%")
                    st.metric("Distinct Product Groups", summary.get("distinct_product_groups", 0))
                with col2:
                    st.metric("Avg Response Time", f"{summary.get('avg_response_time', 0):.0f}ms")
                    st.metric("Total Uploads", summary.get("total_uploads", 0))
            else:
                st.error("Failed to fetch summary stats")
        except Exception as e:
            st.error(f"Error fetching summary: {str(e)}")
        
        st.markdown("---")
        st.markdown("### 🚀 Quick Actions")
        
        # Quick action buttons
        if st.button("📊 View Detailed Analytics", use_container_width=True):
            st.info("Navigate to the detailed analytics section below")
        
        if st.button("📋 Export Data", use_container_width=True):
            st.info("Export functionality coming soon!")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Main dashboard content
    st.markdown('<div class="dashboard-container">', unsafe_allow_html=True)
    
    st.header("📊 System Analytics Dashboard")
    
    # Fetch analytics data
    analytics = fetch_analytics(days)
    
    if analytics:
        chat_stats = analytics.get("chat_stats", {})
        
        # ===== TOP SECTION: KEY METRICS =====
        st.subheader("📈 Key Performance Indicators")
        
        # Key metrics row - 5 equal columns
        metric_col1, metric_col2, metric_col3, metric_col4, metric_col5 = st.columns(5)
        
        with metric_col1:
            create_metric_card(
                "Total Queries",
                f"{chat_stats.get('total_queries', 0):,}",
                f"Last {days} days"
            )
        
        with metric_col2:
            create_metric_card(
                "Success Rate",
                f"{chat_stats.get('success_rate', 0):.1f}%",
                "Agent performance"
            )
        
        with metric_col3:
            create_metric_card(
                "Avg Response Time",
                f"{chat_stats.get('avg_response_time', 0):.0f}ms",
                "System performance"
            )
        
        with metric_col4:
            create_metric_card(
                "Multimodal Queries",
                f"{chat_stats.get('multimodal_queries', 0):,}",
                "Image + text queries"
            )
        
        with metric_col5:
            # Calculate distinct product groups
            product_groups = analytics.get("product_groups", [])
            distinct_groups = len(product_groups)
            create_metric_card(
                "Distinct Product Groups",
                f"{distinct_groups}",
                "Product diversity"
            )
        
        st.markdown("---")
        
        # ===== MIDDLE SECTION: CHARTS =====
        st.subheader("📊 Analytics & Trends")
        
        # First row: Activity and Question Types
        chart_row1_col1, chart_row1_col2 = st.columns(2)
        
        with chart_row1_col1:
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            st.markdown("#### 📅 Daily Activity")
            daily_fig = create_daily_activity_chart(analytics.get("daily_activity", []))
            if daily_fig:
                st.plotly_chart(daily_fig, use_container_width=True, height=300)
            else:
                st.info("No daily activity data available")
            st.markdown('</div>', unsafe_allow_html=True)
        
        with chart_row1_col2:
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            st.markdown("#### ❓ Question Type Distribution")
            question_fig = create_question_type_chart(analytics.get("question_types", []))
            if question_fig:
                st.plotly_chart(question_fig, use_container_width=True, height=300)
            else:
                st.info("No question type data available")
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Second row: Product Groups and Performance
        chart_row2_col1, chart_row2_col2 = st.columns(2)
        
        with chart_row2_col1:
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            st.markdown("#### 🏥 Product Group Distribution")
            product_fig = create_product_group_chart(analytics.get("product_groups", []))
            if product_fig:
                st.plotly_chart(product_fig, use_container_width=True, height=300)
            else:
                st.info("No product group data available")
            st.markdown('</div>', unsafe_allow_html=True)
        
        with chart_row2_col2:
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            st.markdown("#### 🎯 Performance Metrics")
            
            # Performance gauges in a more compact layout
            gauge_col1, gauge_col2 = st.columns(2)
            
            with gauge_col1:
                success_gauge = create_performance_gauge(
                    chat_stats.get('success_rate', 0),
                    "Success Rate",
                    0, 100
                )
                st.plotly_chart(success_gauge, use_container_width=True, height=200)
            
            with gauge_col2:
                confidence_gauge = create_performance_gauge(
                    chat_stats.get('avg_confidence', 0) * 100,
                    "Avg Confidence",
                    0, 100
                )
                st.plotly_chart(confidence_gauge, use_container_width=True, height=200)
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("---")
        
        # ===== PRODUCT DIVERSITY SECTION =====
        st.subheader("🏥 Product Diversity Analytics")
        
        # Fetch product diversity analytics
        try:
            diversity_response = requests.get(get_api_url("/dashboard/stats/product-diversity"))
            if diversity_response.status_code == 200:
                diversity_data = diversity_response.json()
                
                # Display diversity metrics in columns
                div_col1, div_col2, div_col3 = st.columns(3)
                
                with div_col1:
                    st.markdown("#### 📊 Diversity Metrics")
                    st.metric(
                        "Distinct Groups", 
                        diversity_data["diversity_metrics"]["distinct_groups_recent"],
                        f"of {diversity_data['diversity_metrics']['total_possible_groups']} total"
                    )
                    st.metric(
                        "Coverage", 
                        f"{diversity_data['diversity_metrics']['coverage_percentage_recent']}%",
                        f"Product groups covered"
                    )
                
                with div_col2:
                    st.markdown("#### 📈 Engagement Metrics")
                    st.metric(
                        "Avg Queries/Group", 
                        diversity_data["engagement_metrics"]["avg_queries_per_group"],
                        "Engagement level"
                    )
                    st.metric(
                        "Unclassified", 
                        diversity_data["engagement_metrics"]["unclassified_queries"],
                        "Queries without product group"
                    )
                
                with div_col3:
                    st.markdown("#### 💡 Insights")
                    st.info(f"**Diversity Score:** {diversity_data['insights']['diversity_score']}%")
                    st.info(f"**Engagement Level:** {diversity_data['insights']['engagement_level']}")
                    st.success(f"**Recommendation:** {diversity_data['insights']['recommendation']}")
            
            else:
                st.warning("Could not load product diversity analytics")
        except Exception as e:
            st.warning(f"Error loading product diversity data: {str(e)}")
        
        st.markdown("---")
        
        # ===== BOTTOM SECTION: RECENT ACTIVITY =====
        st.subheader("📋 Recent Activity")
        
        # Fetch recent events
        events = fetch_recent_events(20)
        
        if events:
            # Three columns for different activity types
            activity_col1, activity_col2, activity_col3 = st.columns(3)
            
            with activity_col1:
                st.markdown("#### 💬 Recent Chat Events")
                chat_events = events.get("chat_events", [])
                
                for i, event in enumerate(chat_events[:5]):
                    with st.expander(f"Query {i+1}: {event['query'][:40]}...", expanded=False):
                        st.write(f"**Response:** {event['response'][:80]}...")
                        st.write(f"**Type:** {event['question_type']}")
                        st.write(f"**Product Group:** {event['product_group'] or 'N/A'}")
                        st.write(f"**Response Time:** {event['response_time_ms']}ms")
                        st.write(f"**Confidence:** {event['confidence_score']:.2f}")
                        
                        # Status indicator
                        status = event['agent_status']
                        if status == 'success':
                            st.success("✅ Success")
                        elif status == 'partial':
                            st.warning("⚠️ Partial")
                        else:
                            st.error("❌ Failed")
            
            with activity_col2:
                st.markdown("#### 📄 Recent Document Uploads")
                doc_events = events.get("document_events", [])
                
                for i, event in enumerate(doc_events[:3]):
                    with st.expander(f"File {i+1}: {event['filename'][:30]}...", expanded=False):
                        st.write(f"**Size:** {event['file_size']:,} bytes")
                        st.write(f"**Chunks:** {event['chunk_count']}")
                        st.write(f"**Product Group:** {event['product_group'] or 'N/A'}")
                        st.write(f"**Processing Time:** {event['processing_time_ms']}ms")
            
            with activity_col3:
                st.markdown("#### ⚙️ Recent System Events")
                sys_events = events.get("system_events", [])
                
                if sys_events:
                    for i, event in enumerate(sys_events[:3]):
                        with st.expander(f"Event {i+1}: {event['component']}", expanded=False):
                            st.write(f"**Operation:** {event['operation']}")
                            st.write(f"**Status:** {event['status']}")
                            st.write(f"**Timestamp:** {event['timestamp']}")
                            if event['error_message']:
                                st.error(f"**Error:** {event['error_message']}")
                else:
                    st.info("No system events recorded")
        
        else:
            st.error("Failed to load recent events")
    
    else:
        st.error("Failed to load analytics data")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Auto-refresh functionality
    if auto_refresh:
        time.sleep(30)
        st.rerun()

# Main app
def main():
    # Page selection
    page = st.sidebar.selectbox(
        "Choose a page",
        ["💊 Chat Assistant", "📊 Monitoring Dashboard"],
        index=0
    )
    
    if page == "📊 Monitoring Dashboard":
        show_monitoring_dashboard()
        return
    
    # Main chat interface
    st.title("💊 iScaps Product Knowledge Assistant")
    
    # Initialize persona selection in session state
    if "selected_persona" not in st.session_state:
        st.session_state.selected_persona = None
    
    # Sidebar - Document upload and persona selection
    with st.sidebar:
        st.markdown("### 🎭 Persona Selection")
        
        # Get available personas from persona manager
        try:
            from src.domain.persona import PersonaManager
            persona_manager = PersonaManager()
            all_personas = persona_manager.get_all_personas()
            
            if all_personas:
                # Create a simple persona selector
                persona_options = ["Default (No Persona)"] + [p.name for p in all_personas]
                selected_persona_display = st.selectbox(
                    "Choose a persona:",
                    options=persona_options,
                    index=0,
                    help="Select a persona to customize how the AI responds"
                )
                
                # Set the selected persona
                if selected_persona_display == "Default (No Persona)":
                    st.session_state.selected_persona = None
                else:
                    st.session_state.selected_persona = selected_persona_display.lower()
                
                # Show current persona info
                if st.session_state.selected_persona:
                    current_persona = persona_manager.get_persona(st.session_state.selected_persona)
                    if current_persona:
                        st.markdown(f"**Current:** {current_persona.name}")
                        st.markdown(f"*{current_persona.description}*")
                        
                        # Show persona characteristics
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Temperature", f"{current_persona.temperature}")
                        with col2:
                            st.metric("Type", current_persona.persona_type.value.replace('_', ' ').title())
                        
                        # Show features
                        features = []
                        if current_persona.include_sources:
                            features.append("📚 Sources")
                        if current_persona.include_confidence:
                            features.append("🎯 Confidence")
                        if current_persona.include_suggestions:
                            features.append("💡 Suggestions")
                        if current_persona.strict_validation:
                            features.append("🛡️ Strict")
                        if current_persona.clinical_safety_check:
                            features.append("🏥 Clinical")
                        
                        if features:
                            st.markdown("**Features:**")
                            st.markdown(" ".join(features))
                else:
                    st.markdown("**Current:** Default AI Assistant")
                    st.markdown("*Standard AI responses without persona customization*")
                    st.info("💡 Try selecting a persona above to customize response style!")
                
            else:
                st.warning("No personas available")
                st.session_state.selected_persona = None
                
        except Exception as e:
            st.error(f"Failed to load personas: {str(e)}")
            st.session_state.selected_persona = None
        
        st.markdown("---")
        st.markdown("### 📚 Document Upload")
        
        # Upload section
        uploaded_file = st.file_uploader(
            "Choose a PDF file",
            type=['pdf'],
            help="Upload product knowledge PDF documents"
        )
        
        if uploaded_file is not None:
            # Product group selection
            try:
                product_groups = get_product_groups()
                product_group_names = {pg["name"]: pg["value"] for pg in product_groups}
                
                selected_product_group = st.selectbox(
                    "Select Product Group",
                    options=[""] + list(product_group_names.keys()),
                    help="Select the product group for this document"
                )
                
                if st.button("📤 Upload Document", type="primary"):
                    with st.spinner("Uploading and processing document..."):
                        try:
                            result = upload_document(
                                uploaded_file.read(),
                                uploaded_file.name,
                                product_group_names.get(selected_product_group) if selected_product_group else None
                            )
                            st.success(f"✅ Document uploaded successfully!")
                            st.json(result)
                        except Exception as e:
                            st.error(f"❌ Upload failed: {str(e)}")
            except Exception as e:
                st.error(f"❌ Failed to load product groups: {str(e)}")
        
        st.markdown("---")
        
        # Quick actions in sidebar
        st.markdown("### 🎯 Quick Actions")
        
        # New conversation
        if st.button("🆕 New Conversation", type="primary"):
            create_new_conversation()
            st.success("New conversation started!")
            st.rerun()
        
        # Quick questions
        st.markdown("#### 💡 Quick Questions")
        quick_questions = [
            "What are the intended uses?",
            "What are the contraindications?",
            "What are the safety precautions?",
            "How do I operate this device?",
            "What are the maintenance requirements?",
            "What are the potential complications?",
            "What are the device specifications?",
            "How do I troubleshoot this device?"
        ]
        
        for question in quick_questions:
            if st.button(question, key=f"quick_{question}"):
                # Add to chat
                st.session_state.messages.append({"role": "user", "content": question})
                # Set a flag to trigger chat response
                st.session_state.quick_question_triggered = question
                st.rerun()
    
    # Main content area - Modern chat interface
    st.markdown("---")
    
    # Chat header
    st.markdown('<div class="chat-header">🤖 Product Knowledge Chat</div>', unsafe_allow_html=True)
    
    # Chat interface
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    
    # Display chat messages using custom styling
    for i, message in enumerate(st.session_state.messages):
        if message["role"] == "user":
            # Check if message has image
            has_image = "image_base64" in message
            
            if has_image:
                # User message with image - display both text and image together
                st.markdown(f"""
                <div class="message-container">
                    <div class="user-message">
                        <div class="message-bubble user-bubble">
                            {message["content"]}
                            <div class="message-image-container">
                                <img src="data:image/jpeg;base64,{message['image_base64']}" class="message-image" alt="Attached image">
                            </div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
            else:
                # User message without image
                st.markdown(f"""
                <div class="message-container">
                    <div class="user-message">
                        <div class="message-bubble user-bubble">
                            {message["content"]}
                        </div>
                    </div>
                """, unsafe_allow_html=True)
        else:
            # Check if this is a streaming message
            is_streaming = message.get("is_streaming", False)
            content = message["content"]
            
            # Skip displaying streaming messages in chat history since they're shown in streaming area
            if is_streaming:
                continue
            
            # Display completed assistant message with HTML styling
            st.markdown(f"""
            <div class="message-container">
                <div class="assistant-message">
                    <div class="message-bubble assistant-bubble">
                        {content}
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Show persona badge if available
            if "persona_metadata" in message and message["persona_metadata"]:
                persona_meta = message["persona_metadata"]["persona"]
                st.markdown(f"""
                <div class="persona-badge">
                    🎭 {persona_meta['name']} ({persona_meta['style']})
                </div>
                """, unsafe_allow_html=True)
            
            # Show additional info for assistant messages (only when not streaming)
            if "metadata" in message and not is_streaming:
                metadata = message["metadata"]
                
                # Multimodal badge
                if metadata.get("multimodal_content"):
                    st.markdown('<span class="multimodal-badge">🖼️ Multimodal</span>', unsafe_allow_html=True)
                
                # Chain of Thought
                if "chain_of_thought" in message and message["chain_of_thought"]:
                    display_chain_of_thought(message["chain_of_thought"])
                
                # Sources
                if "sources" in metadata and metadata["sources"]:
                    with st.expander("📚 Sources"):
                        for source in metadata["sources"]:
                            st.write(f"• {source}")
                
                # Extracted text from image
                if "extracted_text" in metadata and metadata["extracted_text"]:
                    with st.expander("📝 Text extracted from image"):
                        st.write(metadata["extracted_text"])
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    
    # Streaming area - dedicated space for real-time responses
    if st.session_state.messages and st.session_state.messages[-1].get("is_streaming", False):
        with st.container():
            st.markdown("---")
            st.markdown("""
            <div class="streaming-area">
                <div class="streaming-header">🤖 Assistant is typing...</div>
                <div class="streaming-content" id="streaming-content">
                    <span class="streaming-cursor">▋</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            streaming_placeholder = st.empty()
            
            # Get the current streaming message
            current_streaming_message = st.session_state.messages[-1]
            content = current_streaming_message.get("content", "")
            
            with streaming_placeholder.container():
                st.markdown(f"**Assistant:** {content}▋")
    
    # Text input field (takes most space)
    prompt = st.text_input("Ask about product knowledge...", key=f"user_input_{st.session_state.get('text_key', 0)}", label_visibility="collapsed", placeholder="Ask about product knowledge...")
    
    # Action buttons container
    st.markdown('<div class="input-actions">', unsafe_allow_html=True)
    
    # Attachment button
    uploaded_image = st.file_uploader(
        "📎",
        type=['png', 'jpg', 'jpeg'],
        key=f"chat_image_uploader_{st.session_state.get('upload_key', 0)}",
        label_visibility="collapsed",
        help="Attach an image to your message"
    )
    
    # Send button
    send_clicked = st.button("Send", key="send_button", type="primary")
    
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Handle message submission
    if (prompt and send_clicked) or (uploaded_image and send_clicked) or st.session_state.get("quick_question_triggered"):
        # Determine the query to use
        current_query = prompt
        if st.session_state.get("quick_question_triggered"):
            current_query = st.session_state.quick_question_triggered
            # Clear the trigger
            del st.session_state.quick_question_triggered
        
        # Add user message
        message_data = {"role": "user", "content": current_query}
        if uploaded_image:
            # Convert image to base64 for inline display
            import base64
            image_bytes = uploaded_image.read()
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            message_data["image_base64"] = image_base64
            uploaded_image.seek(0)  # Reset file pointer for API call
            # Only add image if there's also a text prompt
            if not current_query:
                st.error("Please provide a question along with the image.")
                return
        
        st.session_state.messages.append(message_data)
        
        # Add assistant message placeholder for streaming
        assistant_message_index = len(st.session_state.messages)
        st.session_state.messages.append({
            "role": "assistant",
            "content": "",
            "metadata": {},
            "is_streaming": True
        })
        
        # Get streaming assistant response
        try:
            # Prepare image data if present
            image_data = None
            if uploaded_image:
                image_data = uploaded_image.read()
                uploaded_image.seek(0)  # Reset file pointer
            
            # Try streaming first
            streaming_success = False
            try:
                # Use streaming chat function with persona
                response = chat_with_documents_stream(
                    query=current_query,
                    image_data=image_data,
                    session_id=get_current_conversation(),
                    persona_name=st.session_state.selected_persona
                )
                
                # Process streaming response
                full_content, metadata, chain_of_thought = process_streaming_response(response, assistant_message_index)
                
                # Mark streaming as complete
                st.session_state.messages[assistant_message_index]["is_streaming"] = False
                streaming_success = True
                
            except Exception as streaming_error:
                print(f"Streaming error: {str(streaming_error)}")
                st.warning("Streaming failed, falling back to regular response...")
                
                # Only fallback if streaming actually failed
                if not streaming_success:
                    # Fallback to non-streaming API
                    response = chat_with_documents(
                        query=current_query,
                        image_data=image_data,
                        session_id=get_current_conversation(),
                        persona_name=st.session_state.selected_persona
                    )
                    
                                    # Update the message with the response
                st.session_state.messages[assistant_message_index]["content"] = response["answer"]
                st.session_state.messages[assistant_message_index]["metadata"] = {
                    "sources": response.get("sources", []),
                    "multimodal_content": response.get("multimodal_content", False),
                    "extracted_text": response.get("extracted_text")
                }
                st.session_state.messages[assistant_message_index]["chain_of_thought"] = response.get("chain_of_thought", [])
                st.session_state.messages[assistant_message_index]["persona_metadata"] = response.get("persona_metadata", {})
                st.session_state.messages[assistant_message_index]["is_streaming"] = False
            
            # Clear both input fields by changing their keys
            st.session_state.text_key = st.session_state.get('text_key', 0) + 1
            st.session_state.upload_key = st.session_state.get('upload_key', 0) + 1
                
        except Exception as e:
            error_msg = f"❌ Error: {str(e)}"
            st.error(error_msg)
            st.session_state.messages[assistant_message_index] = {
                "role": "assistant",
                "content": error_msg,
                "is_streaming": False
            }
        
        # Rerun to update the display
        st.rerun()
    
    # System info at bottom
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"**Conversation ID:** {get_current_conversation()}")
    
    with col2:
        st.markdown(f"**Messages:** {len(st.session_state.messages)}")
    
    with col3:
        if st.session_state.selected_persona:
            st.markdown(f"**Persona:** {st.session_state.selected_persona.title()}")
        elif st.session_state.messages:
            st.markdown("**Last Query:** " + st.session_state.messages[-1]["content"][:30] + "...")
    
    # Chat tips
    st.markdown("---")
    st.markdown("#### 💡 Chat Tips")
    
    # Show persona-specific tips if a persona is selected
    if st.session_state.selected_persona:
        st.markdown("**🎭 Persona Mode Active**")
        
        # Show persona-specific tips
        persona_tips = {
            "summary": "Get quick, bullet-point responses with key information only",
            "technical": "Receive detailed technical specifications and analysis",
            "creative": "Enjoy engaging, storytelling responses with examples",
            "clinical": "Get medical terminology and clinical safety focus",
            "sales_assistant": "Focus on product benefits and value propositions",
            "technical_expert": "Access deep technical specifications and compliance",
            "clinical_advisor": "Medical applications and safety considerations",
            "training_instructor": "Educational explanations with step-by-step guidance",
            "analytical": "Data-driven, structured responses with analysis",
            "conversational": "Friendly, chat-like interactions",
            "advisory": "Professional consultation style with recommendations",
            "educational": "Teaching-focused responses with learning objectives"
        }
        
        persona_tip = persona_tips.get(st.session_state.selected_persona, "Custom persona responses")
        st.markdown(f"**Current Persona:** {persona_tip}")
        st.markdown("*Switch personas in the sidebar to change response style*")
    else:
        st.markdown("**🤖 Default Mode**")
        st.markdown("Select a persona in the sidebar to customize AI responses")
    
    st.markdown("""
    **General Usage:**
    - **Text only**: Just type your question
    - **With image**: Upload an image and ask about it
    - **Product labels**: Upload medication labels for analysis
    - **Medical images**: Share medical images for insights
    - **Documents**: Upload PDFs to build knowledge base
    """)

if __name__ == "__main__":
    main() 