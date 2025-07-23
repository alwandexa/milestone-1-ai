import os
import re
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from guardrails import Guard, OnFailAction


@dataclass
class GuardrailsValidationResult:
    """Result of a guardrails validation"""
    is_valid: bool
    violations: List[Dict[str, Any]]
    corrected_input: Optional[str] = None
    confidence_score: float = 0.0
    validation_type: str = ""


class GuardrailsService:
    """Service for integrating Guardrails AI validation using basic validation logic"""
    
    def __init__(self, enable_guardrails: bool = True):
        self.enable_guardrails = enable_guardrails
        
        if not enable_guardrails:
            return
        
        # Initialize basic validation patterns
        self._setup_validation_patterns()
    
    def _setup_validation_patterns(self):
        """Setup basic validation patterns for content filtering"""
        
        # Toxic language patterns
        self.toxic_patterns = [
            r'\b(shut\s+up|fuck|shit|damn|hell|ass|bitch|bastard)\b',
            r'\b(kill|murder|suicide|die|death)\b',
            r'\b(hate|racist|sexist|homophobic)\b',
            r'\b(violence|weapon|bomb|explosive)\b'
        ]
        
        # Competitor names
        self.competitor_names = [
            "Kalbe", "Phapros", "Kimia Farma", "Indofarma"
        ]
        
        # Compile patterns
        self.toxic_regex = re.compile('|'.join(self.toxic_patterns), re.IGNORECASE)
    
    def validate_user_input(self, user_input: str, context: Optional[str] = None) -> GuardrailsValidationResult:
        """
        Validate user input for safety and appropriateness using basic validation
        
        Args:
            user_input: The user's query or input
            context: Optional context about the conversation
            
        Returns:
            GuardrailsValidationResult with validation details
        """
        if not self.enable_guardrails:
            return GuardrailsValidationResult(
                is_valid=True,
                violations=[],
                validation_type="input_validation"
            )
        
        violations = []
        
        # Check for toxic language
        if self.toxic_regex.search(user_input):
            violations.append({
                "type": "toxic_language",
                "error": "Content contains inappropriate language",
                "details": "Toxic language detected in input"
            })
        
        # Check for competitor mentions
        for competitor in self.competitor_names:
            if competitor.lower() in user_input.lower():
                violations.append({
                    "type": "competitor_mention",
                    "error": f"Content mentions competitor: {competitor}",
                    "details": f"Competitor '{competitor}' mentioned in input"
                })
                break
        
        is_valid = len(violations) == 0
        confidence_score = 1.0 if is_valid else 0.0
        
        return GuardrailsValidationResult(
            is_valid=is_valid,
            violations=violations,
            confidence_score=confidence_score,
            validation_type="input_validation"
        )

    def validate_agent_response(self, response: str, original_query: str, context: Optional[str] = None) -> GuardrailsValidationResult:
        """
        Validate agent response for accuracy, safety, and quality using basic validation
        
        Args:
            response: The agent's response
            original_query: The original user query
            context: Optional context about the conversation
            
        Returns:
            GuardrailsValidationResult with validation details
        """
        if not self.enable_guardrails:
            return GuardrailsValidationResult(
                is_valid=True,
                violations=[],
                validation_type="response_validation"
            )
        
        violations = []
        
        # Check for toxic language in response
        if self.toxic_regex.search(response):
            violations.append({
                "type": "toxic_language",
                "error": "Response contains inappropriate language",
                "details": "Toxic language detected in response"
            })
        
        # Check for competitor mentions in response
        for competitor in self.competitor_names:
            if competitor.lower() in response.lower():
                violations.append({
                    "type": "competitor_mention",
                    "error": f"Response mentions competitor: {competitor}",
                    "details": f"Competitor '{competitor}' mentioned in response"
                })
                break
        
        # Check for potential harmful content
        harmful_patterns = [
            r'\b(how\s+to\s+make\s+bomb)\b',
            r'\b(how\s+to\s+kill)\b',
            r'\b(how\s+to\s+commit\s+suicide)\b',
            r'\b(how\s+to\s+hack)\b'
        ]
        
        for pattern in harmful_patterns:
            if re.search(pattern, response, re.IGNORECASE):
                violations.append({
                    "type": "harmful_content",
                    "error": "Response contains harmful instructions",
                    "details": "Harmful content detected in response"
                })
                break
        
        is_valid = len(violations) == 0
        confidence_score = 1.0 if is_valid else 0.0
        
        return GuardrailsValidationResult(
            is_valid=is_valid,
            violations=violations,
            confidence_score=confidence_score,
            validation_type="response_validation"
        )

    def validate_multimodal_input(self, text: str, image_description: Optional[str] = None) -> GuardrailsValidationResult:
        """
        Validate multimodal input (text + image description) using basic validation
        
        Args:
            text: The text input
            image_description: Optional description of the image content
            
        Returns:
            GuardrailsValidationResult with validation details
        """
        if not self.enable_guardrails:
            return GuardrailsValidationResult(
                is_valid=True,
                violations=[],
                validation_type="multimodal_validation"
            )
        
        # Combine text and image description for validation
        full_input = text
        if image_description:
            full_input = f"{text}\n\nImage content: {image_description}"
        
        violations = []
        
        # Check for toxic language in combined input
        if self.toxic_regex.search(full_input):
            violations.append({
                "type": "toxic_language",
                "error": "Multimodal content contains inappropriate language",
                "details": "Toxic language detected in text or image description"
            })
        
        # Check for inappropriate image content
        inappropriate_image_patterns = [
            r'\b(nude|naked|sexual|porn)\b',
            r'\b(violence|blood|gore)\b',
            r'\b(weapon|gun|knife)\b'
        ]
        
        if image_description:
            for pattern in inappropriate_image_patterns:
                if re.search(pattern, image_description, re.IGNORECASE):
                    violations.append({
                        "type": "inappropriate_image",
                        "error": "Image description contains inappropriate content",
                        "details": "Inappropriate image content detected"
                    })
                    break
        
        is_valid = len(violations) == 0
        confidence_score = 1.0 if is_valid else 0.0
        
        return GuardrailsValidationResult(
            is_valid=is_valid,
            violations=violations,
            confidence_score=confidence_score,
            validation_type="multimodal_validation"
        )
    
    def get_validation_summary(self, result: GuardrailsValidationResult) -> Dict[str, Any]:
        """Get a summary of validation results for logging"""
        return {
            "validation_type": result.validation_type,
            "is_valid": result.is_valid,
            "confidence_score": result.confidence_score,
            "violation_count": len(result.violations),
            "violations": result.violations,
            "has_correction": result.corrected_input is not None
        } 