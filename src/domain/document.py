from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

@dataclass(frozen=True)
class DocumentChunk:
    id: str
    document_id: str
    content: str
    embedding: Optional[List[float]] = None
    metadata: Optional[dict] = None

@dataclass(frozen=True)
class Document:
    id: str
    filename: str
    content: str
    chunks: List[DocumentChunk]
    uploaded_at: datetime
    metadata: Optional[dict] = None 