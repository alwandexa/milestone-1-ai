from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from src.usecase.document_usecase import DocumentUsecase
from src.infrastructure.langgraph_chat import LangGraphChat
from src.domain.document import Document, ProductGroup, ProductKnowledgeQuery, ProductKnowledgeResponse
import uuid

app = FastAPI(title="Product Knowledge API", version="1.0.0")

# Pydantic models
class ChatRequest(BaseModel):
    query: str
    session_id: Optional[str] = None

class MultimodalChatRequest(BaseModel):
    query: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    answer: str
    sources: List[str]
    search_count: int
    context: str

class MultimodalChatResponse(BaseModel):
    answer: str
    sources: List[str]
    search_count: int
    context: str
    multimodal_content: bool
    extracted_text: Optional[str] = None

class ProductKnowledgeRequest(BaseModel):
    query: str
    product_group: Optional[str] = None
    session_id: Optional[str] = None

class MultimodalProductKnowledgeRequest(BaseModel):
    query: str
    product_group: Optional[str] = None
    session_id: Optional[str] = None

class ProductKnowledgeResponseModel(BaseModel):
    answer: str
    sources: List[str]
    product_group: Optional[str] = None
    confidence_score: float
    suggested_follow_up: Optional[str] = None

class MultimodalProductKnowledgeResponseModel(BaseModel):
    answer: str
    sources: List[str]
    product_group: Optional[str] = None
    confidence_score: float
    suggested_follow_up: Optional[str] = None
    multimodal_content: bool
    extracted_text: Optional[str] = None

class ImageAnalysisRequest(BaseModel):
    prompt: str

class ImageAnalysisResponse(BaseModel):
    analysis: str
    extracted_text: Optional[str] = None

class DocumentResponse(BaseModel):
    id: str
    filename: str
    uploaded_at: str
    chunk_count: int
    product_group: Optional[str] = None

class ProductGroupResponse(BaseModel):
    value: str
    name: str

# Dependency injection
_document_usecase: Optional[DocumentUsecase] = None
_langgraph_chat: Optional[LangGraphChat] = None

def set_dependencies(document_usecase: DocumentUsecase, langgraph_chat: LangGraphChat):
    """Set the dependencies for the controller"""
    global _document_usecase, _langgraph_chat
    _document_usecase = document_usecase
    _langgraph_chat = langgraph_chat

def get_document_usecase() -> DocumentUsecase:
    if _document_usecase is None:
        raise HTTPException(status_code=500, detail="Document usecase not initialized")
    return _document_usecase

def get_langgraph_chat() -> LangGraphChat:
    if _langgraph_chat is None:
        raise HTTPException(status_code=500, detail="LangGraph chat not initialized")
    return _langgraph_chat

@app.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    product_group: Optional[str] = Form(None)
):
    """Upload and process a PDF document with optional product group"""
    if not file.filename or not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    # Parse product group if provided
    product_group_enum = None
    if product_group:
        try:
            product_group_enum = ProductGroup(product_group)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid product group: {product_group}")
    
    try:
        content = await file.read()
        usecase = get_document_usecase()
        document = usecase.upload_document(content, file.filename, product_group_enum)
        
        return DocumentResponse(
            id=document.id,
            filename=document.filename,
            uploaded_at=document.uploaded_at.isoformat(),
            chunk_count=len(document.chunks),
            product_group=document.product_group.value if document.product_group else None
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")

@app.post("/product-knowledge/query", response_model=ProductKnowledgeResponseModel)
async def query_product_knowledge(request: ProductKnowledgeRequest):
    """Query product knowledge using the agentic workflow"""
    try:
        usecase = get_document_usecase()
        
        # Parse product group if provided
        product_group_enum = None
        if request.product_group:
            try:
                product_group_enum = ProductGroup(request.product_group)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid product group: {request.product_group}")
        
        # Create query object
        query = ProductKnowledgeQuery(
            query=request.query,
            product_group=product_group_enum,
            session_id=request.session_id
        )
        
        print(f"Processing query: {request.query}")
        print(f"Product group: {product_group_enum}")
        print(f"Session ID: {request.session_id}")
        
        # Execute workflow
        response = await usecase.query_product_knowledge(query)
        
        print(f"Workflow completed successfully")
        print(f"Answer length: {len(response.answer)}")
        print(f"Confidence score: {response.confidence_score}")
        
        return ProductKnowledgeResponseModel(
            answer=response.answer,
            sources=response.sources,
            product_group=response.product_group.value if response.product_group else None,
            confidence_score=response.confidence_score,
            suggested_follow_up=response.suggested_follow_up
        )
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error in product knowledge query: {e}")
        print(f"Traceback: {error_details}")
        raise HTTPException(status_code=500, detail=f"Error in product knowledge query: {str(e)}")

@app.post("/product-knowledge/multimodal-query", response_model=MultimodalProductKnowledgeResponseModel)
async def query_product_knowledge_multimodal(
    request: MultimodalProductKnowledgeRequest,
    image: Optional[UploadFile] = File(None)
):
    """Query product knowledge with multimodal support (text + image)"""
    try:
        chat = get_langgraph_chat()
        
        # Read image data if provided
        image_data = None
        if image:
            if not image.content_type.startswith('image/'):
                raise HTTPException(status_code=400, detail="Only image files are supported")
            image_data = await image.read()
        
        # Use LangGraph chat with multimodal support
        result = chat.chat(
            query=request.query,
            session_id=request.session_id,
            image_data=image_data
        )
        
        return MultimodalProductKnowledgeResponseModel(
            answer=result["answer"],
            sources=result["sources"],
            product_group=request.product_group,
            confidence_score=0.8,  # Default confidence for multimodal
            suggested_follow_up=None,
            multimodal_content=result.get("multimodal_content", False),
            extracted_text=result.get("extracted_text")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in multimodal product knowledge query: {str(e)}")

@app.post("/chat", response_model=ChatResponse)
async def chat_with_documents(request: ChatRequest):
    """Chat with the document-based system using LangGraph"""
    try:
        chat = get_langgraph_chat()
        result = chat.chat(request.query, request.session_id)
        
        return ChatResponse(
            answer=result["answer"],
            sources=result["sources"],
            search_count=result["search_count"],
            context=result["context"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in chat: {str(e)}")

@app.post("/chat/multimodal", response_model=MultimodalChatResponse)
async def chat_with_documents_multimodal(
    request: MultimodalChatRequest,
    image: Optional[UploadFile] = File(None)
):
    """Chat with the document-based system using LangGraph with multimodal support"""
    try:
        chat = get_langgraph_chat()
        
        # Read image data if provided
        image_data = None
        if image:
            if not image.content_type.startswith('image/'):
                raise HTTPException(status_code=400, detail="Only image files are supported")
            image_data = await image.read()
        
        result = chat.chat(
            query=request.query,
            session_id=request.session_id,
            image_data=image_data
        )
        
        return MultimodalChatResponse(
            answer=result["answer"],
            sources=result["sources"],
            search_count=result["search_count"],
            context=result["context"],
            multimodal_content=result.get("multimodal_content", False),
            extracted_text=result.get("extracted_text")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in multimodal chat: {str(e)}")

@app.post("/analyze-image", response_model=ImageAnalysisResponse)
async def analyze_image(
    image: UploadFile = File(...),
    request: ImageAnalysisRequest = None
):
    """Analyze an image using GPT-4o-mini multimodal capabilities"""
    try:
        if not image.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="Only image files are supported")
        
        image_data = await image.read()
        
        # Get OpenAI service for direct image analysis
        from src.infrastructure.openai_service import OpenAIService
        openai_service = OpenAIService()
        
        # Analyze image
        prompt = request.prompt if request else "Please analyze this image and describe what you see."
        analysis = openai_service.analyze_image(image_data, prompt)
        
        # Extract text from image
        extracted_text = openai_service.extract_text_from_image(image_data)
        
        return ImageAnalysisResponse(
            analysis=analysis,
            extracted_text=extracted_text
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing image: {str(e)}")

@app.get("/documents", response_model=List[DocumentResponse])
async def list_documents():
    """List all uploaded documents"""
    try:
        usecase = get_document_usecase()
        documents = usecase.list_documents()
        
        return [
            DocumentResponse(
                id=doc.id,
                filename=doc.filename,
                uploaded_at=doc.uploaded_at.isoformat() if doc.uploaded_at else "",
                chunk_count=len(doc.chunks),
                product_group=doc.product_group.value if doc.product_group else None
            )
            for doc in documents
        ]
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error in list_documents: {e}")
        print(f"Traceback: {error_details}")
        error_msg = str(e) if str(e) else "Unknown error occurred"
        raise HTTPException(status_code=500, detail=f"Error listing documents: {error_msg}")

@app.get("/documents/product-group/{product_group}", response_model=List[DocumentResponse])
async def list_documents_by_product_group(product_group: str):
    """List documents filtered by product group"""
    try:
        # Parse product group
        try:
            product_group_enum = ProductGroup(product_group)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid product group: {product_group}")
        
        usecase = get_document_usecase()
        documents = usecase.list_documents_by_product_group(product_group_enum)
        
        return [
            DocumentResponse(
                id=doc.id,
                filename=doc.filename,
                uploaded_at=doc.uploaded_at.isoformat() if doc.uploaded_at else "",
                chunk_count=len(doc.chunks),
                product_group=doc.product_group.value if doc.product_group else None
            )
            for doc in documents
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing documents: {str(e)}")

@app.get("/documents/search/product-group/{product_group}")
async def search_documents_by_product_group(product_group: str, limit: int = 10):
    """Search for documents by product group"""
    try:
        # Parse product group
        try:
            product_group_enum = ProductGroup(product_group)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid product group: {product_group}")
        
        usecase = get_document_usecase()
        chunks = usecase.search_documents_by_product_group(product_group_enum, limit)
        
        # Convert chunks to response format
        results = []
        for chunk in chunks:
            results.append({
                "id": chunk.id,
                "document_id": chunk.document_id,
                "content": chunk.content,
                "product_group": chunk.product_group.value if chunk.product_group else None,
                "metadata": chunk.metadata
            })
        
        return {
            "product_group": product_group,
            "count": len(results),
            "chunks": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching documents: {str(e)}")

@app.get("/product-groups", response_model=List[ProductGroupResponse])
async def get_product_groups():
    """Get all available product groups"""
    try:
        usecase = get_document_usecase()
        product_groups = usecase.get_product_groups()
        
        return [
            ProductGroupResponse(
                value=group.value,
                name=group.value.replace("_", " ").title()
            )
            for group in product_groups
        ]
    except Exception as e:
        error_msg = str(e) if str(e) else "Unknown error occurred"
        raise HTTPException(status_code=500, detail=f"Error getting product groups: {error_msg}")

@app.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    """Delete a document"""
    try:
        usecase = get_document_usecase()
        usecase.delete_document(document_id)
        return {"message": "Document deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting document: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "Product Knowledge API"} 