from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class ProductGroup(Enum):
    """Product groups for categorization"""
    IMAGING_EQUIPMENT = "imaging_equipment"
    SURGICAL_INSTRUMENTS = "surgical_instruments"
    MONITORING_DEVICES = "monitoring_devices"
    DIAGNOSTIC_EQUIPMENT = "diagnostic_equipment"
    THERAPEUTIC_DEVICES = "therapeutic_devices"
    ORTHOPEDIC_DEVICES = "orthopedic_devices"
    CARDIOVASCULAR_DEVICES = "cardiovascular_devices"
    RESPIRATORY_DEVICES = "respiratory_devices"
    DENTAL_EQUIPMENT = "dental_equipment"
    STERILIZATION_EQUIPMENT = "sterilization_equipment"
    MOBILITY_AIDS = "mobility_aids"
    WOUND_CARE_DEVICES = "wound_care_devices"
    SURGICAL_IMPLANTS = "surgical_implants"
    DISPOSABLE_SUPPLIES = "disposable_supplies"
    REHABILITATION_EQUIPMENT = "rehabilitation_equipment"
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
class DocumentQuery:
    query: str
    product_group: Optional[ProductGroup] = None
    session_id: Optional[str] = None
    user_context: Optional[Dict[str, Any]] = None

@dataclass(frozen=True)
class DocumentResponse:
    answer: str
    sources: List[str]
    confidence_score: float
    product_group: Optional[ProductGroup] = None
    suggested_follow_up: Optional[str] = None 