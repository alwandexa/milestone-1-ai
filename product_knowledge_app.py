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
        background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%);
        border-color: #3b82f6;
    }

    .assistant-message {
        background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
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

def query_product_knowledge(query: str, product_group: Optional[str] = None, session_id: Optional[str] = None) -> Dict:
    """Query product knowledge using agentic workflow"""
    payload = {
        "query": query,
        "session_id": session_id
    }
    if product_group:
        payload["product_group"] = product_group
    
    response = requests.post(get_api_url("/product-knowledge/query"), json=payload)
    response.raise_for_status()
    return response.json()

def query_product_knowledge_multimodal(query: str, image_data: bytes, product_group: Optional[str] = None, session_id: Optional[str] = None) -> Dict:
    """Query product knowledge with multimodal support"""
    files = {"image": ("image.jpg", image_data, "image/jpeg")}
    data = {
        "query": query,
        "session_id": session_id
    }
    if product_group:
        data["product_group"] = product_group
    
    response = requests.post(get_api_url("/product-knowledge/multimodal-query"), files=files, data=data)
    response.raise_for_status()
    return response.json()

def analyze_image(image_data: bytes, prompt: str = "Please analyze this image and describe what you see.") -> Dict:
    """Analyze image using multimodal AI"""
    files = {"image": ("image.jpg", image_data, "image/jpeg")}
    data = {"prompt": prompt}
    
    response = requests.post(get_api_url("/analyze-image"), files=files, data=data)
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
    st.markdown("---")
    
    # Sidebar
    with st.sidebar:
        st.markdown("### 📚 Document Management")
        
        # Upload section
        st.markdown("#### Upload Product Knowledge")
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
        
        # Document management
        st.markdown("#### 📋 Document List")
        if st.button("🔄 Refresh Documents"):
            st.rerun()
        
        try:
            documents = list_documents()
            if documents:
                for doc in documents:
                    with st.expander(f"📄 {doc['filename']}"):
                        st.write(f"**ID:** {doc['id']}")
                        st.write(f"**Chunks:** {doc['chunk_count']}")
                        st.write(f"**Product Group:** {doc['product_group'] or 'Not specified'}")
                        st.write(f"**Uploaded:** {doc['uploaded_at']}")
                        
                        if st.button(f"🗑️ Delete", key=f"delete_{doc['id']}"):
                            try:
                                delete_document(doc['id'])
                                st.success("Document deleted!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Delete failed: {str(e)}")
            else:
                st.info("No documents uploaded yet.")
        except Exception as e:
            st.error(f"Failed to load documents: {str(e)}")
        
        st.markdown("---")
        
        # Search by product group
        st.markdown("#### 🔍 Search by Product Group")
        try:
            product_groups = get_product_groups()
            product_group_options = {pg["name"]: pg["value"] for pg in product_groups}
            
            selected_search_group = st.selectbox(
                "Select Product Group to Search",
                options=[""] + list(product_group_options.keys()),
                help="Search for documents in a specific product group"
            )
            
            if selected_search_group:
                search_limit = st.slider("Number of results", 1, 50, 10)
                
                if st.button("🔍 Search", type="primary"):
                    with st.spinner("Searching..."):
                        try:
                            response = requests.get(
                                get_api_url(f"/documents/search/product-group/{product_group_options[selected_search_group]}"),
                                params={"limit": search_limit}
                            )
                            response.raise_for_status()
                            results = response.json()
                            
                            st.success(f"Found {results['count']} chunks in {selected_search_group}")
                            
                            for i, chunk in enumerate(results['chunks'], 1):
                                with st.expander(f"Chunk {i}: {chunk['document_id']}"):
                                    st.write(f"**Content:** {chunk['content'][:200]}...")
                                    st.write(f"**Product Group:** {chunk['product_group']}")
                                    if chunk['metadata']:
                                        st.write(f"**Metadata:** {chunk['metadata']}")
                                        
                        except Exception as e:
                            st.error(f"Search failed: {str(e)}")
        except Exception as e:
            st.error(f"Failed to load product groups for search: {str(e)}")
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### 🤖 Product Knowledge Chat")
        
        # Product group filter for chat
        try:
            product_groups = get_product_groups()
            product_group_options = {pg["name"]: pg["value"] for pg in product_groups}
            
            selected_chat_product_group = st.selectbox(
                "Filter by Product Group (Optional)",
                options=[""] + list(product_group_options.keys()),
                help="Filter responses to specific product groups"
            )
        except:
            selected_chat_product_group = ""
            product_group_options = {}
        
        # Multimodal chat interface
        st.markdown("#### 📸 Multimodal Input")
        
        # Image upload for multimodal chat
        uploaded_image = st.file_uploader(
            "Upload an image (optional)",
            type=['png', 'jpg', 'jpeg'],
            help="Upload an image to analyze along with your text query"
        )
        
        # Display uploaded image
        if uploaded_image is not None:
            st.markdown("**📷 Uploaded Image:**")
            image = Image.open(uploaded_image)
            st.image(image, caption="Uploaded Image", use_column_width=True)
            
            # Image analysis option
            if st.button("🔍 Analyze Image Only"):
                with st.spinner("Analyzing image..."):
                    try:
                        image_data = uploaded_image.read()
                        uploaded_image.seek(0)  # Reset file pointer
                        
                        result = analyze_image(image_data)
                        
                        st.success("✅ Image analysis complete!")
                        st.markdown("**📊 Analysis:**")
                        st.write(result["analysis"])
                        
                        if result.get("extracted_text"):
                            st.markdown("**📝 Extracted Text:**")
                            st.write(result["extracted_text"])
                    except Exception as e:
                        st.error(f"❌ Image analysis failed: {str(e)}")
        
        # Chat interface
        if "messages" not in st.session_state:
            st.session_state.messages = []
        
        # Display chat messages
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                
                # Show additional info for assistant messages
                if message["role"] == "assistant" and "metadata" in message:
                    metadata = message["metadata"]
                    
                    # Multimodal badge
                    if metadata.get("multimodal_content"):
                        st.markdown('<span class="multimodal-badge">🖼️ Multimodal</span>', unsafe_allow_html=True)
                    
                    # Confidence score
                    if "confidence_score" in metadata:
                        confidence_class = get_confidence_class(metadata["confidence_score"])
                        st.markdown(f"**Confidence:** <span class='{confidence_class}'>{metadata['confidence_score']:.2f}</span>", unsafe_allow_html=True)
                    
                    # Product group
                    if "product_group" in metadata and metadata["product_group"]:
                        st.markdown(f"**Product Group:** {metadata['product_group']}")
                    
                    # Extracted text from image
                    if "extracted_text" in metadata and metadata["extracted_text"]:
                        with st.expander("📝 Text extracted from image"):
                            st.write(metadata["extracted_text"])
                    
                    # Suggested follow-up
                    if "suggested_follow_up" in metadata and metadata["suggested_follow_up"]:
                        st.info(f"💡 **Suggested follow-up:** {metadata['suggested_follow_up']}")
        
        # Chat input
        if prompt := st.chat_input("Ask about product knowledge..."):
            # Add user message
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            # Display user message
            with st.chat_message("user"):
                st.markdown(prompt)
            
            # Get assistant response
            with st.chat_message("assistant"):
                with st.spinner("🤔 Thinking..."):
                    try:
                        if uploaded_image is not None:
                            # Multimodal query
                            image_data = uploaded_image.read()
                            uploaded_image.seek(0)  # Reset file pointer
                            
                            response = query_product_knowledge_multimodal(
                                query=prompt,
                                image_data=image_data,
                                product_group=product_group_options.get(selected_chat_product_group) if selected_chat_product_group else None,
                                session_id=get_current_conversation()
                            )
                        else:
                            # Text-only query
                            response = query_product_knowledge(
                                query=prompt,
                                product_group=product_group_options.get(selected_chat_product_group) if selected_chat_product_group else None,
                                session_id=get_current_conversation()
                            )
                        
                        # Display response
                        st.markdown(response["answer"])
                        
                        # Add assistant message with metadata
                        metadata = {
                            "confidence_score": response.get("confidence_score", 0.8),
                            "product_group": response.get("product_group"),
                            "suggested_follow_up": response.get("suggested_follow_up"),
                            "sources": response.get("sources", []),
                            "multimodal_content": response.get("multimodal_content", False),
                            "extracted_text": response.get("extracted_text")
                        }
                        
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": response["answer"],
                            "metadata": metadata
                        })
                        
                    except Exception as e:
                        error_msg = f"❌ Error: {str(e)}"
                        st.error(error_msg)
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": error_msg
                        })
    
    with col2:
        st.markdown("### 🎯 Quick Actions")
        
        # New conversation
        if st.button("🆕 New Conversation", type="primary"):
            create_new_conversation()
            st.success("New conversation started!")
            st.rerun()
        
        # Quick questions
        st.markdown("#### 💡 Quick Questions")
        quick_questions = [
            "What are the main indications for this product?",
            "What are the common side effects?",
            "What is the recommended dosage?",
            "How does this compare to competitors?",
            "What clinical studies support this product?",
            "What are the contraindications?",
            "What patient populations should be considered?",
            "What are the drug interactions?"
        ]
        
        for question in quick_questions:
            if st.button(question, key=f"quick_{question}"):
                # Add to chat
                st.session_state.messages.append({"role": "user", "content": question})
                st.rerun()
        
        st.markdown("---")
        
        # Multimodal quick actions
        st.markdown("#### 🖼️ Multimodal Actions")
        multimodal_actions = [
            "Analyze this product label",
            "What does this medical image show?",
            "Extract text from this document",
            "Compare this image with product information"
        ]
        
        for action in multimodal_actions:
            if st.button(action, key=f"multimodal_{action}"):
                st.info("Please upload an image and ask your question in the chat!")
        
        st.markdown("---")
        
        # System info
        st.markdown("#### ℹ️ System Info")
        st.markdown(f"**Conversation ID:** {get_current_conversation()}")
        st.markdown(f"**Messages:** {len(st.session_state.messages)}")
        
        if st.session_state.messages:
            st.markdown("**Last Query:** " + st.session_state.messages[-1]["content"][:50] + "...")
        
        # Multimodal status
        if uploaded_image is not None:
            st.markdown("**🖼️ Image Ready:** Yes")
        else:
            st.markdown("**🖼️ Image Ready:** No")

if __name__ == "__main__":
    main() 