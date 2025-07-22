from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.document import Document, DocumentChunk

class DocumentRepositoryPort(ABC):
    @abstractmethod
    def upload_document(self, document: Document) -> None:
        pass

    @abstractmethod
    def search_similar_chunks(self, query_embedding: List[float], top_k: int = 5) -> List[DocumentChunk]:
        pass

    @abstractmethod
    def get_document_by_id(self, document_id: str) -> Optional[Document]:
        pass

    @abstractmethod
    def list_documents(self) -> List[Document]:
        pass

    @abstractmethod
    def delete_document(self, document_id: str) -> None:
        pass 