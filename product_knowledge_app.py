import streamlit as st
import requests
import json
from typing import List, Dict, Optional
import uuid
from datetime import datetime
import io
from PIL import Image
import asyncio
import aiohttp
import time

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

def chat_with_documents_stream(query: str, image_data: Optional[bytes] = None, session_id: Optional[str] = None):
    """Streaming chat function that works like ChatGPT - supports both text and images"""
    files = {}
    data = {
        "query": query,
        "session_id": session_id
    }
    
    if image_data:
        files["image"] = ("image.jpg", image_data, "image/jpeg")
    
    # Use the streaming endpoint
    response = requests.post(get_api_url("/chat/stream"), files=files, data=data, stream=True)
    response.raise_for_status()
    return response

def process_streaming_response(response, message_index: int):
    """Process streaming response and update the UI in real-time"""
    full_content = ""
    metadata = {}
    
    # Create a placeholder for real-time updates
    placeholder = st.empty()
    
    try:
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data: '):
                    try:
                        data = json.loads(line_str[6:])  # Remove 'data: ' prefix
                        
                        if data.get('type') == 'metadata':
                            # Store metadata
                            metadata = {
                                "sources": data.get("sources", []),
                                "multimodal_content": data.get("multimodal_content", False),
                                "extracted_text": data.get("extracted_text")
                            }
                        elif data.get('type') == 'content':
                            # Append content
                            full_content += data.get('content', '')
                            
                            # Update the message in session state
                            st.session_state.messages[message_index]["content"] = full_content
                            st.session_state.messages[message_index]["metadata"] = metadata
                            st.session_state.messages[message_index]["is_streaming"] = True
                            
                            # Update the placeholder with current content using native Streamlit
                            with placeholder.container():
                                st.markdown("**Assistant:**")
                                st.write(full_content + "▋")
                            
                        elif data.get('type') == 'error':
                            st.error(f"Error: {data.get('content', 'Unknown error')}")
                            break
                        elif data.get('type') == 'end':
                            # Mark streaming as complete
                            st.session_state.messages[message_index]["is_streaming"] = False
                            break
                    except json.JSONDecodeError:
                        continue
    except Exception as e:
        st.error(f"Streaming error: {str(e)}")
        full_content = f"Error during streaming: {str(e)}"
    
    return full_content, metadata

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
            
            # Add typing indicator for streaming messages
            if is_streaming and not content:
                content = "🤔 Thinking..."
            
            # For streaming messages, use native Streamlit components to avoid HTML rendering issues
            if is_streaming:
                st.markdown("**Assistant:**")
                st.write(content + "▋")
            else:
                # Display assistant message with HTML styling for completed messages
                st.markdown(f"""
                <div class="message-container">
                    <div class="assistant-message">
                        <div class="message-bubble assistant-bubble">
                            {content}
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            # Show additional info for assistant messages (only when not streaming)
            if "metadata" in message and not is_streaming:
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
            try:
                # Use streaming chat function
                response = chat_with_documents_stream(
                    query=current_query,
                    image_data=image_data,
                    session_id=get_current_conversation()
                )
                
                # Process streaming response
                full_content, metadata = process_streaming_response(response, assistant_message_index)
                
                # Mark streaming as complete
                st.session_state.messages[assistant_message_index]["is_streaming"] = False
                
            except Exception as streaming_error:
                st.warning("Streaming failed, falling back to regular response...")
                
                # Fallback to non-streaming API
                response = chat_with_documents(
                    query=current_query,
                    image_data=image_data,
                    session_id=get_current_conversation()
                )
                
                # Update the message with the response
                st.session_state.messages[assistant_message_index]["content"] = response["answer"]
                st.session_state.messages[assistant_message_index]["metadata"] = {
                    "sources": response.get("sources", []),
                    "multimodal_content": response.get("multimodal_content", False),
                    "extracted_text": response.get("extracted_text")
                }
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