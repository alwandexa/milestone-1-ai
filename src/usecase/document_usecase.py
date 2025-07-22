from typing import List
from src.domain.document import Document, DocumentChunk
from src.ports.document_repository_port import DocumentRepositoryPort
from src.infrastructure.document_processor import DocumentProcessor
from src.infrastructure.openai_service import OpenAIService
import uuid

class DocumentUsecase:
    def __init__(self, repository: DocumentRepositoryPort, processor: DocumentProcessor, openai_service: OpenAIService):
        self.repository = repository
        self.processor = processor
        self.openai_service = openai_service

    def upload_document(self, file_content: bytes, filename: str) -> Document:
        """Upload and process a document"""
        # Process the document
        document = self.processor.process_pdf(file_content, filename)
        
        # Generate embeddings for chunks
        document_with_embeddings = self._add_embeddings_to_chunks(document)
        
        # Store in repository
        self.repository.upload_document(document_with_embeddings)
        
        return document_with_embeddings

    def _add_embeddings_to_chunks(self, document: Document) -> Document:
        """Add embeddings to document chunks"""
        chunks_with_embeddings = []
        
        for chunk in document.chunks:
            # Generate embedding for chunk content
            embedding = self.openai_service.get_embedding(chunk.content)
            
            # Create new chunk with embedding
            chunk_with_embedding = DocumentChunk(
                id=chunk.id,
                document_id=chunk.document_id,
                content=chunk.content,
                embedding=embedding,
                metadata=chunk.metadata
            )
            chunks_with_embeddings.append(chunk_with_embedding)
        
        # Create new document with embedded chunks
        document_with_embeddings = Document(
            id=document.id,
            filename=document.filename,
            content=document.content,
            chunks=chunks_with_embeddings,
            uploaded_at=document.uploaded_at,
            metadata=document.metadata
        )
        
        return document_with_embeddings

    def search_documents(self, query: str, top_k: int = 5) -> List[DocumentChunk]:
        """Search for relevant document chunks"""
        # Generate embedding for query
        query_embedding = self.openai_service.get_embedding(query)
        
        # Search repository
        return self.repository.search_similar_chunks(query_embedding, top_k)

    def list_documents(self) -> List[Document]:
        """List all documents"""
        return self.repository.list_documents()

    def delete_document(self, document_id: str) -> None:
        """Delete a document"""
        self.repository.delete_document(document_id) 