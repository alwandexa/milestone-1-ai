from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from src.usecase.document_usecase import DocumentUsecase
from src.infrastructure.langgraph_chat import LangGraphChat
from src.domain.document import Document
import uuid

app = FastAPI(title="Document Chatbot API", version="1.0.0")

# Pydantic models
class ChatRequest(BaseModel):
    query: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    answer: str
    sources: List[str]
    search_count: int
    context: str

class DocumentResponse(BaseModel):
    id: str
    filename: str
    uploaded_at: str
    chunk_count: int

# Dependency injection
document_usecase: Optional[DocumentUsecase] = None
langgraph_chat: Optional[LangGraphChat] = None

def get_document_usecase() -> DocumentUsecase:
    if document_usecase is None:
        raise HTTPException(status_code=500, detail="Document usecase not initialized")
    return document_usecase

def get_langgraph_chat() -> LangGraphChat:
    if langgraph_chat is None:
        raise HTTPException(status_code=500, detail="LangGraph chat not initialized")
    return langgraph_chat

@app.post("/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload and process a PDF document"""
    if not file.filename or not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    try:
        content = await file.read()
        usecase = get_document_usecase()
        document = usecase.upload_document(content, file.filename)
        
        return DocumentResponse(
            id=document.id,
            filename=document.filename,
            uploaded_at=document.uploaded_at.isoformat(),
            chunk_count=len(document.chunks)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")

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
                chunk_count=len(doc.chunks)
            )
            for doc in documents
        ]
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error in list_documents: {e}")
        print(f"Traceback: {error_details}")
        raise HTTPException(status_code=500, detail=f"Error listing documents: {str(e)}")

@app.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    """Delete a document and all its chunks"""
    try:
        usecase = get_document_usecase()
        usecase.delete_document(document_id)
        return {"message": "Document deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=404, detail="Document not found")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"} 