import streamlit as st
import requests
import json
from typing import List, Dict
import uuid
from datetime import datetime

# Custom CSS for blueish theme with gradation
st.set_page_config(
    page_title="Document Chatbot",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
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

    .css-1d391kg .css-1lcbmhc {
        background: transparent;
    }

    /* Sidebar text styling */
    .css-1d391kg p, .css-1d391kg div {
        color: white;
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

    /* Vivid button styling for sidebar */
    .css-1d391kg .stButton > button {
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

    .css-1d391kg .stButton > button:hover {
        background: linear-gradient(135deg, #059669, #047857);
        transform: translateY(-3px) scale(1.02);
        box-shadow: 0 10px 30px rgba(16, 185, 129, 0.6);
        border-color: rgba(255, 255, 255, 0.6);
    }

    /* Delete button styling */
    .css-1d391kg .stButton > button[data-testid="baseButton-secondary"] {
        background: linear-gradient(135deg, #ef4444, #dc2626);
        box-shadow: 0 4px 15px rgba(239, 68, 68, 0.4);
        border: 2px solid rgba(255, 255, 255, 0.2);
    }

    .css-1d391kg .stButton > button[data-testid="baseButton-secondary"]:hover {
        background: linear-gradient(135deg, #dc2626, #b91c1c);
        box-shadow: 0 6px 20px rgba(239, 68, 68, 0.6);
        transform: translateY(-2px) scale(1.05);
    }

    /* Button styling */
    .stButton > button {
        background: linear-gradient(135deg, var(--secondary-blue), var(--accent-blue));
        color: white;
        border: none;
        border-radius: 15px;
        padding: 0.75rem 1.5rem;
        font-weight: 600;
        font-size: 0.95rem;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 0 4px 15px rgba(59, 130, 246, 0.3);
        position: relative;
        overflow: hidden;
        letter-spacing: 0.5px;
    }

    .stButton > button::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
        transition: left 0.5s;
    }

    .stButton > button:hover {
        transform: translateY(-3px) scale(1.02);
        box-shadow: 0 8px 25px rgba(59, 130, 246, 0.5);
        background: linear-gradient(135deg, var(--accent-blue), var(--secondary-blue));
    }

    .stButton > button:hover::before {
        left: 100%;
    }

    .stButton > button:active {
        transform: translateY(-1px) scale(0.98);
        box-shadow: 0 4px 15px rgba(59, 130, 246, 0.4);
    }

    /* Special button styling for delete buttons */
    .stButton > button[data-testid="baseButton-secondary"] {
        background: linear-gradient(135deg, #ef4444, #f87171);
        box-shadow: 0 4px 15px rgba(239, 68, 68, 0.3);
    }

    .stButton > button[data-testid="baseButton-secondary"]:hover {
        background: linear-gradient(135deg, #f87171, #ef4444);
        box-shadow: 0 8px 25px rgba(239, 68, 68, 0.5);
    }

    /* New chat button special styling */
    .stButton > button:has-text("➕ New Chat") {
        background: linear-gradient(135deg, #059669, #10b981);
        box-shadow: 0 4px 15px rgba(5, 150, 105, 0.3);
        font-size: 1rem;
        padding: 1rem 2rem;
        border-radius: 20px;
    }

    .stButton > button:has-text("➕ New Chat"):hover {
        background: linear-gradient(135deg, #10b981, #059669);
        box-shadow: 0 8px 25px rgba(5, 150, 105, 0.5);
    }

    /* Chat message styling */
    .stChatMessage {
        background: var(--bg-light);
        border-radius: 15px;
        margin: 0.5rem 0;
        padding: 1rem;
        border: 1px solid rgba(59, 130, 246, 0.2);
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
    }

    .stChatMessage[data-testid="chatMessage"] {
        background: var(--bg-white);
        border: 1px solid rgba(59, 130, 246, 0.3);
    }

    /* Chat message text styling */
    .stChatMessage p, .stChatMessage div {
        color: var(--text-dark);
        line-height: 1.6;
    }

    /* Input styling */
    .stTextInput > div > div > input {
        border-radius: 10px;
        border: 2px solid #d1d5db;
        background: var(--bg-white);
        color: var(--text-dark);
        transition: all 0.3s ease;
        font-size: 1rem;
    }

    .stTextInput > div > div > input:focus {
        border-color: var(--secondary-blue);
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
        background: var(--bg-white);
    }

    .stTextInput > div > div > input::placeholder {
        color: var(--text-light);
    }

    /* File uploader styling */
    .stFileUploader > div {
        border: 2px dashed #d1d5db;
        border-radius: 10px;
        background: var(--bg-light);
        transition: all 0.3s ease;
        color: var(--text-dark);
    }

    .stFileUploader > div:hover {
        border-color: var(--secondary-blue);
        background: var(--bg-white);
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
    }

    .stFileUploader > div > div {
        color: var(--text-dark);
    }

    /* Expander styling */
    .streamlit-expanderHeader {
        background: var(--bg-light);
        border-radius: 8px;
        border: 1px solid #d1d5db;
        color: var(--text-dark);
        font-weight: 600;
        transition: all 0.3s ease;
    }

    .streamlit-expanderHeader:hover {
        background: var(--bg-white);
        border-color: var(--secondary-blue);
    }

    /* Success/Error message styling */
    .stAlert {
        border-radius: 10px;
        border: 1px solid #d1d5db;
        background: var(--bg-white);
        color: var(--text-dark);
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
    }

    .stAlert[data-baseweb="notification"] {
        background: var(--bg-white);
        border: 1px solid #fecaca;
        color: #dc2626;
    }

    /* Spinner styling */
    .stSpinner > div {
        border-color: var(--accent-blue);
        border-top-color: var(--secondary-blue);
    }

    /* Divider styling */
    hr {
        border: none;
        height: 2px;
        background: linear-gradient(90deg, transparent, var(--accent-blue), transparent);
        margin: 1rem 0;
    }

    /* Info box styling */
    .stAlert[data-baseweb="notification"] {
        background: var(--bg-white);
        border: 1px solid #bfdbfe;
        border-radius: 10px;
        color: var(--text-dark);
    }

    /* Custom scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
    }

    ::-webkit-scrollbar-track {
        background: rgba(219, 234, 254, 0.3);
        border-radius: 4px;
    }

    ::-webkit-scrollbar-thumb {
        background: linear-gradient(135deg, var(--accent-blue), var(--secondary-blue));
        border-radius: 4px;
    }

    ::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(135deg, var(--secondary-blue), var(--primary-blue));
    }

    /* Sidebar title styling */
    .css-1d391kg h1, .css-1d391kg h2, .css-1d391kg h3 {
        color: white;
        text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
    }

    /* Sidebar button styling */
    .css-1d391kg .stButton > button {
        background: rgba(255, 255, 255, 0.2);
        color: white;
        border: 1px solid rgba(255, 255, 255, 0.3);
        backdrop-filter: blur(10px);
    }

    .css-1d391kg .stButton > button:hover {
        background: rgba(255, 255, 255, 0.3);
        border-color: rgba(255, 255, 255, 0.5);
    }

    /* Chat input styling */
    .stChatInput > div > div > textarea {
        border-radius: 15px;
        border: 2px solid #d1d5db;
        background: var(--bg-white);
        color: var(--text-dark);
        transition: all 0.3s ease;
        font-size: 1rem;
        line-height: 1.5;
    }

    .stChatInput > div > div > textarea:focus {
        border-color: var(--secondary-blue);
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
        background: var(--bg-white);
    }

    .stChatInput > div > div > textarea::placeholder {
        color: var(--text-light);
    }

    /* Layout improvements */
    .main .block-container {
        max-width: 1200px;
        padding: 2rem 3rem;
        margin: 1rem auto;
    }

    /* Column styling */
    .row-widget.stHorizontal {
        gap: 1.5rem;
        align-items: center;
    }

    /* Custom card styling for conversation items */
    .conversation-item {
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.9), rgba(219, 234, 254, 0.9));
        border-radius: 12px;
        padding: 0.75rem;
        margin: 0.5rem 0;
        border: 1px solid rgba(59, 130, 246, 0.2);
        transition: all 0.3s ease;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
    }

    .conversation-item:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(59, 130, 246, 0.15);
        border-color: rgba(59, 130, 246, 0.4);
    }

    /* Sidebar layout improvements */
    .css-1d391kg {
        padding: 1.5rem;
        min-width: 280px;
    }

    /* Main content area spacing */
    .main .block-container > div {
        margin-bottom: 2rem;
    }

    /* Chat container styling */
    .stChatMessageContainer {
        background: rgba(255, 255, 255, 0.8);
        border-radius: 15px;
        padding: 1rem;
        margin: 1rem 0;
        backdrop-filter: blur(10px);
        border: 1px solid rgba(59, 130, 246, 0.1);
    }

    /* Upload section styling */
    .upload-section {
        background: linear-gradient(135deg, rgba(219, 234, 254, 0.3), rgba(147, 197, 253, 0.3));
        border-radius: 15px;
        padding: 1.5rem;
        margin: 1rem 0;
        border: 1px solid rgba(59, 130, 246, 0.2);
    }

    /* Status indicators */
    .status-indicator {
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        margin-right: 8px;
    }

    .status-connected {
        background: linear-gradient(135deg, #10b981, #059669);
        box-shadow: 0 0 12px rgba(16, 185, 129, 0.7);
        animation: pulse-green 2s infinite;
    }

    .status-disconnected {
        background: linear-gradient(135deg, #ef4444, #dc2626);
        box-shadow: 0 0 12px rgba(239, 68, 68, 0.7);
        animation: pulse-red 2s infinite;
    }

    @keyframes pulse-green {
        0%, 100% { box-shadow: 0 0 12px rgba(16, 185, 129, 0.7); }
        50% { box-shadow: 0 0 20px rgba(16, 185, 129, 0.9); }
    }

    @keyframes pulse-red {
        0%, 100% { box-shadow: 0 0 12px rgba(239, 68, 68, 0.7); }
        50% { box-shadow: 0 0 20px rgba(239, 68, 68, 0.9); }
    }
</style>
""", unsafe_allow_html=True)

# API configuration
API_BASE_URL = "http://localhost:8000"

def upload_document(file_content: bytes, filename: str) -> Dict:
    """Upload document via API"""
    files = {"file": (filename, file_content, "application/pdf")}
    response = requests.post(f"{API_BASE_URL}/documents/upload", files=files)
    return response.json()

def chat_with_documents(query: str, session_id: str | None = None) -> Dict:
    """Chat with document system via API"""
    url = f"{API_BASE_URL}/chat"
    data = {"query": query}
    if session_id:
        data["session_id"] = session_id
    response = requests.post(url, json=data)
    return response.json()

def list_documents() -> List[Dict]:
    """List all documents via API"""
    url = f"{API_BASE_URL}/documents"
    response = requests.get(url)
    return response.json()

def delete_document(document_id: str) -> Dict:
    """Delete document via API"""
    url = f"{API_BASE_URL}/documents/{document_id}"
    response = requests.delete(url)
    return response.json()

# Initialize session state for conversations
if "conversations" not in st.session_state:
    st.session_state.conversations = {}
if "current_conversation_id" not in st.session_state:
    st.session_state.current_conversation_id = None
if "conversation_counter" not in st.session_state:
    st.session_state.conversation_counter = 0

def create_new_conversation():
    """Create a new conversation"""
    conversation_id = str(uuid.uuid4())
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    st.session_state.conversation_counter += 1
    
    st.session_state.conversations[conversation_id] = {
        "id": conversation_id,
        "title": f"New Chat {st.session_state.conversation_counter}",
        "messages": [],
        "created_at": timestamp,
        "updated_at": timestamp
    }
    st.session_state.current_conversation_id = conversation_id
    return conversation_id

def get_current_conversation():
    """Get the current conversation"""
    if st.session_state.current_conversation_id is None:
        create_new_conversation()
    return st.session_state.conversations[st.session_state.current_conversation_id]

def update_conversation_title(conversation_id: str, title: str):
    """Update conversation title"""
    if conversation_id in st.session_state.conversations:
        st.session_state.conversations[conversation_id]["title"] = title
        st.session_state.conversations[conversation_id]["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")

def delete_conversation(conversation_id: str):
    """Delete a conversation"""
    if conversation_id in st.session_state.conversations:
        del st.session_state.conversations[conversation_id]
        if st.session_state.current_conversation_id == conversation_id:
            if st.session_state.conversations:
                st.session_state.current_conversation_id = list(st.session_state.conversations.keys())[0]
            else:
                st.session_state.current_conversation_id = None

# Sidebar for conversations
with st.sidebar:
    st.markdown("""
    <div style="text-align: center; margin-bottom: 2rem;">
        <h2 style="
            color: white;
            font-size: 1.5rem;
            font-weight: 700;
            text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
            margin-bottom: 0.5rem;
        ">💬 Conversations</h2>
    </div>
    """, unsafe_allow_html=True)
    
    # New conversation button with enhanced styling
    st.markdown("""
    <div style="margin-bottom: 1.5rem;">
    """, unsafe_allow_html=True)
    
    if st.button("➕ New Chat", use_container_width=True):
        create_new_conversation()
        st.rerun()
    
    # st.markdown("</div>", unsafe_allow_html=True)
    
    # st.markdown("""
    # <div class="sidebar-container">
    # """, unsafe_allow_html=True)
    
    # Conversation list
    if st.session_state.conversations:
        st.markdown("**Recent Chats:**", help="Click on a conversation to switch to it")
        
        for conv_id, conversation in st.session_state.conversations.items():
            # Create a unique key for each conversation
            col1, col2 = st.columns([4, 1])
            
            with col1:
                # Highlight current conversation with custom styling
                if conv_id == st.session_state.current_conversation_id:
                    st.markdown(f"""
                    <div style="
                        background: linear-gradient(135deg, rgba(255, 255, 255, 0.6), rgba(147, 197, 253, 0.6));
                        border-radius: 12px;
                        padding: 12px 18px;
                        margin: 8px 0;
                        border: 3px solid rgba(255, 255, 255, 0.8);
                        font-weight: 700;
                        color: #1e3a8a;
                        text-shadow: 0 1px 2px rgba(255, 255, 255, 0.5);
                        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3);
                        font-size: 1.1rem;
                        letter-spacing: 0.5px;
                    ">
                        {conversation['title']}
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    if st.button(conversation['title'], key=f"conv_{conv_id}", use_container_width=True):
                        st.session_state.current_conversation_id = conv_id
                        st.rerun()
            
            with col2:
                if st.button("🗑️", key=f"del_{conv_id}", help="Delete conversation"):
                    delete_conversation(conv_id)
                    st.rerun()
    else:
        st.markdown("""
        <div style="
            text-align: center;
            color: black;
            font-style: italic;
            padding: 1rem;
        ">
            No conversations yet.<br>
            Start a new chat to begin!
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    st.divider()
    
    # Document upload section in sidebar
    st.markdown("""
    <div class="sidebar-container">
        <h3 style="
            color: white;
            font-size: 1.3rem;
            font-weight: 700;
            margin-bottom: 1.5rem;
            text-shadow: 0 2px 4px rgba(0, 0, 0, 0.4);
            text-align: center;
        ">📚 Upload Documents</h3>
    """, unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader(
        "Choose a PDF file", 
        type=['pdf'],
        help="Only PDF files are supported",
        key="sidebar_file_uploader"
    )
    
    if uploaded_file is not None:
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.3), rgba(147, 197, 253, 0.3));
            border-radius: 12px;
            padding: 1.2rem;
            margin: 1rem 0;
            border: 2px solid rgba(255, 255, 255, 0.6);
            backdrop-filter: blur(15px);
            box-shadow: 0 6px 20px rgba(0, 0, 0, 0.2);
        ">
            <div style="color: #1e3a8a; margin-bottom: 0.5rem; font-weight: 700; font-size: 1.1rem;">
                📄 {uploaded_file.name}
            </div>
            <div style="color: #374151; font-size: 0.95rem; font-weight: 500;">
                Size: {uploaded_file.size:,} bytes
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🚀 Upload Document", key="sidebar_upload_btn"):
            try:
                with st.spinner("Processing document..."):
                    result = upload_document(uploaded_file.read(), uploaded_file.name)
                
                st.success(f"✅ Document uploaded successfully!")
                
                # Handle the response safely
                if isinstance(result, dict):
                    doc_id = result.get('id', 'Unknown')
                    chunk_count = result.get('chunk_count', 0)
                    uploaded_at = result.get('uploaded_at', 'Unknown')
                    
                    st.markdown(f"""
                    <div style="
                        background: #f0fdf4;
                        border-radius: 8px;
                        padding: 1rem;
                        margin: 1rem 0;
                        border: 1px solid #bbf7d0;
                        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
                    ">
                        <div style="color: #059669; font-weight: 600; margin-bottom: 0.5rem;">
                            📊 Upload Details
                        </div>
                        <div style="color: #374151; font-size: 0.9rem;">
                            <strong style="color: #1f2937;">Document ID:</strong> {doc_id}<br>
                            <strong style="color: #1f2937;">Chunks created:</strong> {chunk_count}<br>
                            <strong style="color: #1f2937;">Uploaded at:</strong> {uploaded_at}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.write(f"**Response:** {result}")
                
                st.rerun()
                
            except requests.exceptions.RequestException as e:
                st.error(f"Error uploading document: {e}")
            except Exception as e:
                st.error(f"Unexpected error: {e}")
                st.write(f"**Response type:** {type(result)}")
                st.write(f"**Response:** {result}")
    
    st.markdown("</div>", unsafe_allow_html=True)

# Main chat interface
st.markdown("""
<div style="text-align: center; margin-bottom: 2rem;">
    <h1 style="
        color: #1f2937;
        font-weight: 700;
        font-size: 2.5rem;
        margin-bottom: 0.5rem;
        text-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    ">📚 Document-Based Chatbot</h1>
    <p style="
        color: #6b7280;
        font-size: 1.1rem;
        margin: 0;
        font-style: italic;
        line-height: 1.5;
    ">Upload PDF documents and chat with them using LangGraph and vector search</p>
</div>
""", unsafe_allow_html=True)

# Get current conversation
current_conversation = get_current_conversation()

# Display conversation title
if current_conversation:
    col1, col2 = st.columns([3, 1])
    with col1:
        
        new_title = st.text_input(
            "Conversation Title:",
            value=current_conversation["title"],
            key=f"title_{current_conversation['id']}"
        )
        if new_title != current_conversation["title"]:
            update_conversation_title(current_conversation["id"], new_title or "Untitled")
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div style="
            background: #f8fafc;
            border-radius: 8px;
            padding: 0.75rem;
            text-align: center;
            border: 1px solid #d1d5db;
            color: #374151;
            font-size: 0.9rem;
        ">
            <strong style="color: #1f2937;">Created:</strong><br>
            {current_conversation['created_at']}
        </div>
        """, unsafe_allow_html=True)

# Display chat messages
if current_conversation and current_conversation["messages"]:
    for message in current_conversation["messages"]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if "sources" in message and message["sources"]:
                with st.expander("📚 Sources used"):
                    for i, source in enumerate(message["sources"], 1):
                        st.write(f"**{i}. {source}**")

# Chat input
if prompt := st.chat_input("Ask a question about your documents..."):
    # Add user message to conversation
    current_conversation["messages"].append({
        "role": "user",
        "content": prompt,
        "timestamp": datetime.now().isoformat()
    })
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Get AI response
    with st.chat_message("assistant"):
        with st.spinner("Searching documents and generating response..."):
            try:
                # Use conversation ID as session ID for LangGraph
                session_id = current_conversation["id"]
                response = chat_with_documents(prompt, session_id)
                answer = response.get("answer", "Sorry, I couldn't generate a response.")
                
                # Display AI response
                st.markdown(answer)
                
                # Show search info
                search_count = response.get("search_count", 0)
                if search_count > 1:
                    st.info(f"🔍 Searched {search_count} times to find the best answer")
                
                # Add assistant message to conversation
                current_conversation["messages"].append({
                    "role": "assistant",
                    "content": answer,
                    "sources": response.get("sources", []),
                    "search_count": search_count,
                    "timestamp": datetime.now().isoformat()
                })
                
                # Update conversation timestamp
                current_conversation["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                
            except requests.exceptions.RequestException as e:
                st.error(f"Error connecting to backend: {e}")
                current_conversation["messages"].append({
                    "role": "assistant",
                    "content": "Sorry, I'm having trouble connecting to the backend.",
                    "timestamp": datetime.now().isoformat()
                })

# Health check with enhanced styling

try:
    health_response = requests.get(f"{API_BASE_URL}/health")
    if health_response.status_code == 200:
        st.markdown("""
        <div style="
            display: flex;
            align-items: center;
            color: #10b981;
            font-weight: 700;
            font-size: 1rem;
            text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
            padding: 0.5rem;
            background: rgba(16, 185, 129, 0.1);
            border-radius: 8px;
            border: 1px solid rgba(16, 185, 129, 0.3);
        ">
            <div class="status-indicator status-connected"></div>
            Backend: Connected
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="
            display: flex;
            align-items: center;
            color: #ef4444;
            font-weight: 700;
            font-size: 1rem;
            text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
            padding: 0.5rem;
            background: rgba(239, 68, 68, 0.1);
            border-radius: 8px;
            border: 1px solid rgba(239, 68, 68, 0.3);
        ">
            <div class="status-indicator status-disconnected"></div>
            Backend: Error
        </div>
        """, unsafe_allow_html=True)
except requests.exceptions.RequestException:
    st.markdown("""
    <div style="
        display: flex;
        align-items: center;
        color: #ef4444;
        font-weight: 700;
        font-size: 1rem;
        text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
        padding: 0.5rem;
        background: rgba(239, 68, 68, 0.1);
        border-radius: 8px;
        border: 1px solid rgba(239, 68, 68, 0.3);
    ">
        <div class="status-indicator status-disconnected"></div>
        Backend: Disconnected
    </div>
    """, unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True) 