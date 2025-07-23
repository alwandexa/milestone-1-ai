from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional, AsyncGenerator
from src.usecase.document_usecase import DocumentUsecase
from src.infrastructure.langgraph_chat import LangGraphChat
from src.domain.document import Document, ProductGroup, DocumentQuery, DocumentResponse
from src.controller.dashboard_controller import router as dashboard_router
import uuid
import json

app = FastAPI(title="Product Knowledge API", version="1.0.0")

# Include dashboard router
app.include_router(dashboard_router)

# Pydantic models
class ChatRequest(BaseModel):
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
    chain_of_thought: List[Dict[str, Any]] = []
    input_validation: Optional[Dict[str, Any]] = None
    response_validation: Optional[Dict[str, Any]] = None

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
    import time
    start_time = time.time()
    
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
        
        # Calculate processing time
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        # Log the document event for monitoring
        try:
            from src.controller.dashboard_controller import get_monitoring_service
            monitoring_service = get_monitoring_service()
            
            monitoring_service.log_document_event(
                filename=file.filename,
                file_size=len(content),
                chunk_count=len(document.chunks),
                processing_time_ms=processing_time_ms,
                product_group=document.product_group.value if document.product_group else None
            )
        except Exception as monitoring_error:
            # Don't fail the main request if monitoring fails
            print(f"Monitoring error: {monitoring_error}")
        
        return DocumentResponse(
            id=document.id,
            filename=document.filename,
            uploaded_at=document.uploaded_at.isoformat(),
            chunk_count=len(document.chunks),
            product_group=document.product_group.value if document.product_group else None
        )
    except Exception as e:
        # Log error event
        try:
            from src.controller.dashboard_controller import get_monitoring_service
            monitoring_service = get_monitoring_service()
            monitoring_service.log_system_event(
                component="document_upload",
                operation="upload_document",
                status="failed",
                error_message=str(e)
            )
        except:
            pass
        
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")

@app.post("/chat", response_model=MultimodalChatResponse)
async def chat_with_documents(
    query: str = Form(...),
    session_id: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None)
):
    """Unified chat endpoint that works like ChatGPT - supports both text and images"""
    import time
    start_time = time.time()
    
    try:
        chat = get_langgraph_chat()
        
        # Read image data if provided
        image_data = None
        multimodal = False
        extracted_text = None
        if image:
            if not image.content_type.startswith('image/'):
                raise HTTPException(status_code=400, detail="Only image files are supported")
            image_data = await image.read()
            multimodal = True
        
        # Use LangGraph chat with multimodal support
        result = chat.chat(
            query=query,
            session_id=session_id,
            image_data=image_data
        )
        
        # Calculate response time
        response_time_ms = int((time.time() - start_time) * 1000)
        
        # Log the chat event for monitoring
        try:
            from src.controller.dashboard_controller import get_monitoring_service
            monitoring_service = get_monitoring_service()
            
            # Extract product group from context if available
            product_group = None
            if result.get("context"):
                # Try to extract product group from context
                context_lower = result["context"].lower()
                for group in ProductGroup:
                    if group.value.lower() in context_lower:
                        product_group = group.value
                        break
            
            monitoring_service.log_chat_event(
                query=query,
                response=result["answer"],
                session_id=session_id,
                product_group=product_group,
                response_time_ms=response_time_ms,
                token_count=len(result["answer"].split()),  # Approximate token count
                confidence_score=result.get("confidence_score", 0.5),
                sources_count=len(result["sources"]),
                chain_of_thought=result.get("chain_of_thought"),
                input_validation=result.get("input_validation"),
                response_validation=result.get("response_validation"),
                multimodal=multimodal,
                extracted_text=result.get("extracted_text")
            )
        except Exception as monitoring_error:
            # Don't fail the main request if monitoring fails
            print(f"Monitoring error: {monitoring_error}")
        
        return MultimodalChatResponse(
            answer=result["answer"],
            sources=result["sources"],
            search_count=result["search_count"],
            context=result["context"],
            multimodal_content=result.get("multimodal_content", False),
            extracted_text=result.get("extracted_text"),
            chain_of_thought=result.get("chain_of_thought", [])
        )
    except Exception as e:
        # Log error event
        try:
            from src.controller.dashboard_controller import get_monitoring_service
            monitoring_service = get_monitoring_service()
            monitoring_service.log_system_event(
                component="chat",
                operation="chat_with_documents",
                status="failed",
                session_id=session_id,
                error_message=str(e)
            )
        except:
            pass
        
        raise HTTPException(status_code=500, detail=f"Error in chat: {str(e)}")

@app.post("/chat/stream")
async def chat_with_documents_stream(
    query: str = Form(...),
    session_id: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None)
):
    """Streaming chat endpoint that works like ChatGPT - supports both text and images"""
    try:
        chat = get_langgraph_chat()
        
        # Read image data if provided
        image_data = None
        if image:
            if not image.content_type.startswith('image/'):
                raise HTTPException(status_code=400, detail="Only image files are supported")
            image_data = await image.read()
        
        async def generate_stream() -> AsyncGenerator[str, None]:
            """Generate streaming response"""
            try:
                async for chunk in chat.chat_stream(
                    query=query,
                    session_id=session_id,
                    image_data=image_data
                ):
                    # Send each chunk as a Server-Sent Event
                    yield f"data: {json.dumps(chunk)}\n\n"
                
                # Send end marker
                yield f"data: {json.dumps({'type': 'end'})}\n\n"
            except Exception as e:
                error_chunk = {
                    'type': 'error',
                    'content': f"Error: {str(e)}"
                }
                yield f"data: {json.dumps(error_chunk)}\n\n"
        
        return StreamingResponse(
            generate_stream(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream",
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in streaming chat: {str(e)}")

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