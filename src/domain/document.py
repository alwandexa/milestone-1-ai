from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class ProductGroup(Enum):
    """Product groups for medical device categorization"""
    IMAGING_EQUIPMENT = "imaging_equipment"  # MRI, CT, X-ray, etc.
    SURGICAL_INSTRUMENTS = "surgical_instruments"  # Scalpels, forceps, etc.
    MONITORING_DEVICES = "monitoring_devices"  # Patient monitors, ECG, etc.
    DIAGNOSTIC_EQUIPMENT = "diagnostic_equipment"  # Lab analyzers, testing devices
    THERAPEUTIC_DEVICES = "therapeutic_devices"  # Infusion pumps, ventilators
    ORTHOPEDIC_DEVICES = "orthopedic_devices"  # Implants, prosthetics
    CARDIOVASCULAR_DEVICES = "cardiovascular_devices"  # Stents, pacemakers
    RESPIRATORY_DEVICES = "respiratory_devices"  # Ventilators, oxygen therapy
    DENTAL_EQUIPMENT = "dental_equipment"  # Dental chairs, tools
    STERILIZATION_EQUIPMENT = "sterilization_equipment"  # Autoclaves, sanitizers
    MOBILITY_AIDS = "mobility_aids"  # Wheelchairs, walkers
    WOUND_CARE_DEVICES = "wound_care_devices"  # Dressings, negative pressure
    SURGICAL_IMPLANTS = "surgical_implants"  # Various medical implants
    DISPOSABLE_SUPPLIES = "disposable_supplies"  # Single-use medical items
    REHABILITATION_EQUIPMENT = "rehabilitation_equipment"  # Physical therapy devices
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