import os
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import requests
from pydantic import BaseModel
from .guardrails_config import GuardrailsConfig, get_validation_config, get_error_message


@dataclass
class GuardrailsValidationResult:
    """Result of a guardrails validation"""
    is_valid: bool
    violations: List[Dict[str, Any]]
    corrected_input: Optional[str] = None
    confidence_score: float = 0.0
    validation_type: str = ""


class GuardrailsService:
    """Service for integrating Guardrails AI validation"""
    
    def __init__(self, config: Optional[GuardrailsConfig] = None):
        self.api_key = os.getenv("GUARDRAILS_API_KEY")
        if not self.api_key:
            raise ValueError("GUARDRAILS_API_KEY environment variable is required")
        
        self.config = config or get_validation_config()
        self.base_url = "https://api.guardrails.ai/v2"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def validate_user_input(self, user_input: str, context: Optional[str] = None) -> GuardrailsValidationResult:
        """
        Validate user input for safety and appropriateness
        
        Args:
            user_input: The user's query or input
            context: Optional context about the conversation
            
        Returns:
            GuardrailsValidationResult with validation details
        """
        if not self.config.input_validation_enabled:
            return GuardrailsValidationResult(
                is_valid=True,
                violations=[],
                validation_type="input_validation"
            )
        
        try:
            payload = {
                "text": user_input,
                "validation_type": "input_safety",
                "context": context or "Product knowledge chatbot conversation",
                "checks": self.config.input_checks
            }
            
            response = requests.post(
                f"{self.base_url}/validate",
                headers=self.headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return self._parse_validation_response(data, "input_validation")
            else:
                return GuardrailsValidationResult(
                    is_valid=False,
                    violations=[{"error": f"API error: {response.status_code}"}],
                    validation_type="input_validation"
                )
                
        except Exception as e:
            return GuardrailsValidationResult(
                is_valid=False,
                violations=[{"error": f"Validation failed: {str(e)}"}],
                validation_type="input_validation"
            )

    def validate_agent_response(self, response: str, original_query: str, context: Optional[str] = None) -> GuardrailsValidationResult:
        """
        Validate agent response for accuracy, safety, and quality
        
        Args:
            response: The agent's response
            original_query: The original user query
            context: Optional context about the conversation
            
        Returns:
            GuardrailsValidationResult with validation details
        """
        if not self.config.response_validation_enabled:
            return GuardrailsValidationResult(
                is_valid=True,
                violations=[],
                validation_type="response_validation"
            )
        
        try:
            payload = {
                "text": response,
                "validation_type": "response_quality",
                "context": context or "Product knowledge chatbot response",
                "original_query": original_query,
                "checks": self.config.response_checks
            }
            
            response_api = requests.post(
                f"{self.base_url}/validate",
                headers=self.headers,
                json=payload,
                timeout=10
            )
            
            if response_api.status_code == 200:
                data = response_api.json()
                return self._parse_validation_response(data, "response_validation")
            else:
                return GuardrailsValidationResult(
                    is_valid=False,
                    violations=[{"error": f"API error: {response_api.status_code}"}],
                    validation_type="response_validation"
                )
                
        except Exception as e:
            return GuardrailsValidationResult(
                is_valid=False,
                violations=[{"error": f"Validation failed: {str(e)}"}],
                validation_type="response_validation"
            )

    def validate_multimodal_input(self, text: str, image_description: Optional[str] = None) -> GuardrailsValidationResult:
        """
        Validate multimodal input (text + image description)
        
        Args:
            text: The text input
            image_description: Optional description of the image content
            
        Returns:
            GuardrailsValidationResult with validation details
        """
        if not self.config.multimodal_validation_enabled:
            return GuardrailsValidationResult(
                is_valid=True,
                violations=[],
                validation_type="multimodal_validation"
            )
        
        try:
            # Combine text and image description for validation
            full_input = text
            if image_description:
                full_input = f"{text}\n\nImage content: {image_description}"
            
            payload = {
                "text": full_input,
                "validation_type": "multimodal_input",
                "context": "Product knowledge chatbot with image analysis",
                "checks": self.config.multimodal_checks
            }
            
            response = requests.post(
                f"{self.base_url}/validate",
                headers=self.headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return self._parse_validation_response(data, "multimodal_validation")
            else:
                return GuardrailsValidationResult(
                    is_valid=False,
                    violations=[{"error": f"API error: {response.status_code}"}],
                    validation_type="multimodal_validation"
                )
                
        except Exception as e:
            return GuardrailsValidationResult(
                is_valid=False,
                violations=[{"error": f"Validation failed: {str(e)}"}],
                validation_type="multimodal_validation"
            )

    def _parse_validation_response(self, data: Dict[str, Any], validation_type: str) -> GuardrailsValidationResult:
        """Parse the validation response from Guardrails API"""
        is_valid = data.get("is_valid", True)
        violations = data.get("violations", [])
        corrected_input = data.get("corrected_text")
        confidence_score = data.get("confidence_score", 0.0)
        
        return GuardrailsValidationResult(
            is_valid=is_valid,
            violations=violations,
            corrected_input=corrected_input,
            confidence_score=confidence_score,
            validation_type=validation_type
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