import streamlit as st
import requests
import json
from typing import List, Dict, Optional
import uuid
from datetime import datetime
import io
from PIL import Image

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
        max-width: 300px;
        border-radius: 8px;
        margin: 0.5rem 0;
        border: 2px solid #3b82f6;
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

    /* Custom input styling */
    .custom-input-container {
        display: flex;
        align-items: center;
        gap: 1rem;
        height: 100%;
    }

    .custom-input-field {
        flex: 1;
        padding: 0.75rem;
        border: 1px solid #d1d5db;
        border-radius: 8px;
        font-size: 1rem;
    }

    .custom-upload-area {
        width: 120px;
        padding: 0.5rem;
        border: 1px solid #d1d5db;
        border-radius: 8px;
        text-align: center;
        font-size: 0.875rem;
        background: #f9fafb;
    }

    /* Modern chat header */
    .chat-header {
        background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%);
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 12px 12px 0 0;
        margin-bottom: 0;
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

def chat_with_documents(query: str, image_data: Optional[bytes] = None, session_id: Optional[str] = None) -> Dict:
    """Unified chat function that works like ChatGPT - supports both text and images"""
    files = {}
    data = {
        "query": query,
        "session_id": session_id
    }
    
    if image_data:
        files["image"] = ("image.jpg", image_data, "image/jpeg")
    
    response = requests.post(get_api_url("/chat"), files=files, data=data)
    response.raise_for_status()
    return response.json()

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

# Main app
def main():
    st.title("💊 iScaps Product Knowledge Assistant")
    
    # Sidebar - Simplified to only include upload functionality
    with st.sidebar:
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
    for message in st.session_state.messages:
        if message["role"] == "user":
            st.markdown(f"""
            <div class="message-container">
                <div class="user-message">
                    <div class="message-bubble user-bubble">
                        {message["content"]}
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Display image if present
            if "image" in message:
                st.image(message["image"], caption="Attached Image", width=300)
        else:
            st.markdown(f"""
            <div class="message-container">
                <div class="assistant-message">
                    <div class="message-bubble assistant-bubble">
                        {message["content"]}
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Show additional info for assistant messages
            if "metadata" in message:
                metadata = message["metadata"]
                
                # Multimodal badge
                if metadata.get("multimodal_content"):
                    st.markdown('<span class="multimodal-badge">🖼️ Multimodal</span>', unsafe_allow_html=True)
                
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
    
    # Input area
    # st.markdown('<div class="input-area">', unsafe_allow_html=True)
    
    # Custom input interface
    col1, col2 = st.columns([4, 1])
    
    with col1:
        prompt = st.text_input("Ask about product knowledge...", key="user_input", label_visibility="collapsed")
    
    with col2:
        uploaded_image = st.file_uploader(
            "📷",
            type=['png', 'jpg', 'jpeg'],
            key="chat_image_uploader",
            label_visibility="collapsed",
            help="Attach an image to your message"
        )
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Handle message submission
    if prompt or uploaded_image or st.session_state.get("quick_question_triggered"):
        # Determine the query to use
        current_query = prompt
        if st.session_state.get("quick_question_triggered"):
            current_query = st.session_state.quick_question_triggered
            # Clear the trigger
            del st.session_state.quick_question_triggered
        
        # Add user message
        message_data = {"role": "user", "content": current_query}
        if uploaded_image:
            message_data["image"] = uploaded_image
            # Only add image if there's also a text prompt
            if not current_query:
                st.error("Please provide a question along with the image.")
                return
        
        st.session_state.messages.append(message_data)
        
        # Get assistant response
        with st.spinner("🤔 Thinking..."):
            try:
                # Prepare image data if present
                image_data = None
                if uploaded_image:
                    image_data = uploaded_image.read()
                    uploaded_image.seek(0)  # Reset file pointer
                
                # Use unified chat function
                response = chat_with_documents(
                    query=current_query,
                    image_data=image_data,
                    session_id=get_current_conversation()
                )
                
                # Add assistant message with metadata
                metadata = {
                    "sources": response.get("sources", []),
                    "multimodal_content": response.get("multimodal_content", False),
                    "extracted_text": response.get("extracted_text")
                }
                
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response["answer"],
                    "metadata": metadata
                })
                
                # Clear the input field
                if "user_input" in st.session_state:
                    del st.session_state.user_input
                
            except Exception as e:
                error_msg = f"❌ Error: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg
                })
        
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
        if st.session_state.messages:
            st.markdown("**Last Query:** " + st.session_state.messages[-1]["content"][:30] + "...")
    
    # Chat tips
    st.markdown("---")
    st.markdown("#### 💡 Chat Tips")
    st.markdown("""
    - **Text only**: Just type your question
    - **With image**: Upload an image and ask about it
    - **Product labels**: Upload medication labels for analysis
    - **Medical images**: Share medical images for insights
    - **Documents**: Upload PDFs to build knowledge base
    """)

if __name__ == "__main__":
    main() 