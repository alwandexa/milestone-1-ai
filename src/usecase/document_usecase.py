from typing import List, Optional
from src.domain.document import Document, DocumentChunk, ProductGroup, ProductKnowledgeQuery, ProductKnowledgeResponse
from src.ports.document_repository_port import DocumentRepositoryPort
from src.infrastructure.document_processor import DocumentProcessor
from src.infrastructure.openai_service import OpenAIService
import uuid

class DocumentUsecase:
    def __init__(self, repository: DocumentRepositoryPort, processor: DocumentProcessor, openai_service: OpenAIService):
        self.repository = repository
        self.processor = processor
        self.openai_service = openai_service
        self._workflow_orchestrator = None

    @property
    def workflow_orchestrator(self):
        """Lazy initialization of workflow orchestrator to avoid circular imports"""
        if self._workflow_orchestrator is None:
            from src.agents.workflow_orchestrator import WorkflowOrchestrator
            self._workflow_orchestrator = WorkflowOrchestrator(self.openai_service, self)
        return self._workflow_orchestrator

    def upload_document(self, file_content: bytes, filename: str, product_group: Optional[ProductGroup] = None) -> Document:
        """Upload and process a document with optional product group"""
        # Process the document with product group
        document = self.processor.process_pdf(file_content, filename, product_group)
        
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
                metadata=chunk.metadata,
                product_group=chunk.product_group
            )
            chunks_with_embeddings.append(chunk_with_embedding)
        
        # Create new document with embedded chunks
        document_with_embeddings = Document(
            id=document.id,
            filename=document.filename,
            content=document.content,
            chunks=chunks_with_embeddings,
            uploaded_at=document.uploaded_at,
            metadata=document.metadata,
            product_group=document.product_group
        )
        
        return document_with_embeddings

    def search_documents(self, query: str, top_k: int = 5, product_group: Optional[ProductGroup] = None) -> List[DocumentChunk]:
        """Search for relevant document chunks with optional product group filter"""
        # Generate embedding for query
        query_embedding = self.openai_service.get_embedding(query)
        
        # Search repository with product group filter
        chunks = self.repository.search_similar_chunks(query_embedding, top_k, product_group)
        
        return chunks

    def search_documents_by_product_group(self, product_group: ProductGroup, top_k: int = 10) -> List[DocumentChunk]:
        """Search for documents by product group only"""
        return self.repository.search_by_product_group(product_group, top_k)

    async def query_product_knowledge(self, query: ProductKnowledgeQuery) -> ProductKnowledgeResponse:
        """Query product knowledge using the agentic workflow"""
        return await self.workflow_orchestrator.execute_workflow(query)

    def list_documents(self) -> List[Document]:
        """List all documents"""
        return self.repository.list_documents()

    def list_documents_by_product_group(self, product_group: ProductGroup) -> List[Document]:
        """List documents filtered by product group"""
        all_documents = self.repository.list_documents()
        filtered_documents = []
        
        for document in all_documents:
            if hasattr(document, 'product_group') and document.product_group:
                if document.product_group == product_group:
                    filtered_documents.append(document)
        
        return filtered_documents

    def delete_document(self, document_id: str) -> None:
        """Delete a document"""
        self.repository.delete_document(document_id)

    def get_product_groups(self) -> List[ProductGroup]:
        """Get all available product groups"""
        return list(ProductGroup) 