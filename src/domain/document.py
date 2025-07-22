from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class ProductGroup(Enum):
    """Product groups for categorization"""
    CARDIOVASCULAR = "cardiovascular"
    RESPIRATORY = "respiratory"
    DIABETES = "diabetes"
    ONCOLOGY = "oncology"
    NEUROLOGY = "neurology"
    GASTROENTEROLOGY = "gastroenterology"
    DERMATOLOGY = "dermatology"
    PEDIATRICS = "pediatrics"
    WOMENS_HEALTH = "womens_health"
    MENS_HEALTH = "mens_health"
    INFECTIOUS_DISEASE = "infectious_disease"
    PAIN_MANAGEMENT = "pain_management"
    PSYCHIATRY = "psychiatry"
    ENDOCRINOLOGY = "endocrinology"
    RHEUMATOLOGY = "rheumatology"
    OTHER = "other"

@dataclass(frozen=True)
class DocumentChunk:
    id: str
    document_id: str
    content: str
    embedding: Optional[List[float]] = None
    metadata: Optional[Dict[str, Any]] = None
    product_group: Optional[ProductGroup] = None

@dataclass(frozen=True)
class Document:
    id: str
    filename: str
    content: str
    chunks: List[DocumentChunk]
    uploaded_at: datetime
    metadata: Optional[Dict[str, Any]] = None
    product_group: Optional[ProductGroup] = None

@dataclass(frozen=True)
class ProductKnowledgeQuery:
    query: str
    product_group: Optional[ProductGroup] = None
    session_id: Optional[str] = None
    user_context: Optional[Dict[str, Any]] = None

@dataclass(frozen=True)
class ProductKnowledgeResponse:
    answer: str
    sources: List[str]
    confidence_score: float
    product_group: Optional[ProductGroup] = None
    suggested_follow_up: Optional[str] = None 