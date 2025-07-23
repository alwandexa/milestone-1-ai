from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime
import json

class PersonaType(Enum):
    """Types of personas available"""
    RESPONSE_STYLE = "response_style"
    ROLE_BASED = "role_based"
    INTERACTION = "interaction"

class ResponseStyle(Enum):
    """Response style personas"""
    SUMMARY = "summary"
    TECHNICAL = "technical"
    CREATIVE = "creative"
    CLINICAL = "clinical"
    DETAILED = "detailed"
    CONCISE = "concise"

class RoleBased(Enum):
    """Role-based personas"""
    SALES_ASSISTANT = "sales_assistant"
    TECHNICAL_EXPERT = "technical_expert"
    CLINICAL_ADVISOR = "clinical_advisor"
    TRAINING_INSTRUCTOR = "training_instructor"
    COMPLIANCE_SPECIALIST = "compliance_specialist"
    SAFETY_OFFICER = "safety_officer"

class InteractionStyle(Enum):
    """Interaction style personas"""
    ANALYTICAL = "analytical"
    CONVERSATIONAL = "conversational"
    ADVISORY = "advisory"
    EDUCATIONAL = "educational"
    CONSULTATIVE = "consultative"

@dataclass
class PersonaConfiguration:
    """Configuration for a specific persona"""
    name: str
    description: str
    persona_type: PersonaType
    style: str  # ResponseStyle, RoleBased, or InteractionStyle enum value
    
    # Prompt modifications
    system_prompt_modifier: str
    user_prompt_modifier: str
    
    # Response characteristics
    temperature: float = 0.2
    max_tokens: Optional[int] = None
    response_format: str = "text"
    
    # Behavior settings
    include_sources: bool = True
    include_confidence: bool = True
    include_suggestions: bool = True
    
    # Validation settings
    strict_validation: bool = False
    clinical_safety_check: bool = False
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    is_active: bool = True
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "name": self.name,
            "description": self.description,
            "persona_type": self.persona_type.value,
            "style": self.style,
            "temperature": self.temperature,
            "response_format": self.response_format,
            "include_sources": self.include_sources,
            "include_confidence": self.include_confidence,
            "include_suggestions": self.include_suggestions,
            "strict_validation": self.strict_validation,
            "clinical_safety_check": self.clinical_safety_check,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "is_active": self.is_active,
            "tags": self.tags
        }

@dataclass
class PersonaRequest:
    """Request model for persona selection"""
    persona_name: Optional[str] = None
    persona_type: Optional[PersonaType] = None
    style: Optional[str] = None
    custom_config: Optional[Dict[str, Any]] = None

@dataclass
class PersonaResponse:
    """Response model for persona information"""
    persona: PersonaConfiguration
    applied_modifications: Dict[str, Any]
    confidence_score: float
    validation_results: Optional[Dict[str, Any]] = None

class PersonaManager:
    """Manages available personas and their configurations"""
    
    def __init__(self):
        self._personas: Dict[str, PersonaConfiguration] = {}
        self._initialize_default_personas()
    
    def _initialize_default_personas(self):
        """Initialize default personas"""
        
        # Response Style Personas
        self._personas["summary"] = PersonaConfiguration(
            name="Summary",
            description="Provides concise, bullet-point responses with key information only",
            persona_type=PersonaType.RESPONSE_STYLE,
            style=ResponseStyle.SUMMARY.value,
            system_prompt_modifier="You are a concise assistant. Provide brief, bullet-point responses focusing on key information only. Keep responses under 100 words when possible.",
            user_prompt_modifier="Provide a summary response with key points only.",
            temperature=0.1,
            include_suggestions=False
        )
        
        self._personas["technical"] = PersonaConfiguration(
            name="Technical Expert",
            description="Provides detailed technical specifications and analysis",
            persona_type=PersonaType.RESPONSE_STYLE,
            style=ResponseStyle.TECHNICAL.value,
            system_prompt_modifier="You are a technical expert. Provide detailed technical specifications, compliance information, and engineering analysis. Use precise technical terminology.",
            user_prompt_modifier="Provide detailed technical analysis and specifications.",
            temperature=0.1,
            include_sources=True,
            include_confidence=True
        )
        
        self._personas["creative"] = PersonaConfiguration(
            name="Creative",
            description="Engaging, storytelling approach with examples and analogies",
            persona_type=PersonaType.RESPONSE_STYLE,
            style=ResponseStyle.CREATIVE.value,
            system_prompt_modifier="You are a creative communicator. Use engaging storytelling, analogies, and examples to explain complex concepts. Make responses memorable and relatable.",
            user_prompt_modifier="Provide a creative, engaging response with examples.",
            temperature=0.7,
            include_suggestions=True
        )
        
        self._personas["clinical"] = PersonaConfiguration(
            name="Clinical Advisor",
            description="Medical terminology and clinical focus with patient safety emphasis",
            persona_type=PersonaType.RESPONSE_STYLE,
            style=ResponseStyle.CLINICAL.value,
            system_prompt_modifier="You are a clinical advisor. Use medical terminology appropriately, emphasize patient safety, clinical applications, and evidence-based information.",
            user_prompt_modifier="Provide clinical analysis with medical terminology.",
            temperature=0.2,
            clinical_safety_check=True,
            include_confidence=True
        )
        
        # Role-Based Personas
        self._personas["sales_assistant"] = PersonaConfiguration(
            name="Sales Assistant",
            description="Focus on product benefits, competitive advantages, and value propositions",
            persona_type=PersonaType.ROLE_BASED,
            style=RoleBased.SALES_ASSISTANT.value,
            system_prompt_modifier="You are a sales assistant. Focus on product benefits, competitive advantages, value propositions, and ROI. Highlight features that solve customer problems.",
            user_prompt_modifier="Provide sales-focused analysis with benefits and value propositions.",
            temperature=0.3,
            include_suggestions=True
        )
        
        self._personas["technical_expert"] = PersonaConfiguration(
            name="Technical Expert",
            description="Deep technical specifications, compliance, and engineering analysis",
            persona_type=PersonaType.ROLE_BASED,
            style=RoleBased.TECHNICAL_EXPERT.value,
            system_prompt_modifier="You are a technical expert. Provide detailed technical specifications, compliance requirements, engineering analysis, and technical troubleshooting.",
            user_prompt_modifier="Provide comprehensive technical analysis and specifications.",
            temperature=0.1,
            include_sources=True,
            strict_validation=True
        )
        
        self._personas["clinical_advisor"] = PersonaConfiguration(
            name="Clinical Advisor",
            description="Medical applications, patient safety, and clinical best practices",
            persona_type=PersonaType.ROLE_BASED,
            style=RoleBased.CLINICAL_ADVISOR.value,
            system_prompt_modifier="You are a clinical advisor. Focus on medical applications, patient safety, clinical best practices, and evidence-based recommendations.",
            user_prompt_modifier="Provide clinical analysis with medical applications and safety considerations.",
            temperature=0.2,
            clinical_safety_check=True,
            include_confidence=True
        )
        
        self._personas["training_instructor"] = PersonaConfiguration(
            name="Training Instructor",
            description="Educational explanations with step-by-step guidance and examples",
            persona_type=PersonaType.ROLE_BASED,
            style=RoleBased.TRAINING_INSTRUCTOR.value,
            system_prompt_modifier="You are a training instructor. Provide educational explanations, step-by-step guidance, practical examples, and learning objectives.",
            user_prompt_modifier="Provide educational guidance with examples and step-by-step instructions.",
            temperature=0.4,
            include_suggestions=True
        )
        
        # Interaction Personas
        self._personas["analytical"] = PersonaConfiguration(
            name="Analytical",
            description="Data-driven, structured responses with analysis",
            persona_type=PersonaType.INTERACTION,
            style=InteractionStyle.ANALYTICAL.value,
            system_prompt_modifier="You are an analytical assistant. Provide data-driven, structured responses with clear analysis, comparisons, and logical reasoning.",
            user_prompt_modifier="Provide analytical analysis with structured reasoning.",
            temperature=0.1,
            include_confidence=True
        )
        
        self._personas["conversational"] = PersonaConfiguration(
            name="Conversational",
            description="Friendly, chat-like interactions with natural language",
            persona_type=PersonaType.INTERACTION,
            style=InteractionStyle.CONVERSATIONAL.value,
            system_prompt_modifier="You are a conversational assistant. Use friendly, natural language, ask clarifying questions, and maintain an engaging dialogue.",
            user_prompt_modifier="Provide a conversational, friendly response.",
            temperature=0.6,
            include_suggestions=True
        )
        
        self._personas["advisory"] = PersonaConfiguration(
            name="Advisory",
            description="Professional consultation style with recommendations",
            persona_type=PersonaType.INTERACTION,
            style=InteractionStyle.ADVISORY.value,
            system_prompt_modifier="You are an advisory consultant. Provide professional recommendations, risk assessments, and strategic guidance with clear rationale.",
            user_prompt_modifier="Provide professional advisory recommendations.",
            temperature=0.3,
            include_confidence=True,
            include_suggestions=True
        )
        
        self._personas["educational"] = PersonaConfiguration(
            name="Educational",
            description="Teaching-focused with explanations and learning objectives",
            persona_type=PersonaType.INTERACTION,
            style=InteractionStyle.EDUCATIONAL.value,
            system_prompt_modifier="You are an educational instructor. Focus on teaching concepts, providing explanations, setting learning objectives, and encouraging understanding.",
            user_prompt_modifier="Provide educational content with explanations and learning objectives.",
            temperature=0.4,
            include_suggestions=True
        )
    
    def get_persona(self, name: str) -> Optional[PersonaConfiguration]:
        """Get a persona by name"""
        return self._personas.get(name)
    
    def get_all_personas(self) -> List[PersonaConfiguration]:
        """Get all available personas"""
        return list(self._personas.values())
    
    def get_personas_by_type(self, persona_type: PersonaType) -> List[PersonaConfiguration]:
        """Get personas by type"""
        return [p for p in self._personas.values() if p.persona_type == persona_type]
    
    def add_persona(self, persona: PersonaConfiguration) -> bool:
        """Add a new persona"""
        if persona.name in self._personas:
            return False
        self._personas[persona.name] = persona
        return True
    
    def update_persona(self, name: str, persona: PersonaConfiguration) -> bool:
        """Update an existing persona"""
        if name not in self._personas:
            return False
        persona.updated_at = datetime.now()
        self._personas[name] = persona
        return True
    
    def delete_persona(self, name: str) -> bool:
        """Delete a persona"""
        if name not in self._personas:
            return False
        del self._personas[name]
        return True
    
    def get_default_persona(self) -> PersonaConfiguration:
        """Get the default persona (analytical)"""
        return self._personas.get("analytical", self._personas["technical"]) 