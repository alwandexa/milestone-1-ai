"""
Guardrails AI Configuration
"""

from typing import Dict, List, Any
from dataclasses import dataclass


@dataclass
class GuardrailsConfig:
    """Configuration for Guardrails AI validation"""
    
    # Input validation settings
    input_validation_enabled: bool = True
    input_checks: List[str] = None
    
    # Response validation settings
    response_validation_enabled: bool = True
    response_checks: List[str] = None
    
    # Multimodal validation settings
    multimodal_validation_enabled: bool = True
    multimodal_checks: List[str] = None
    
    # Safety thresholds
    toxicity_threshold: float = 0.7
    hate_speech_threshold: float = 0.7
    violence_threshold: float = 0.7
    self_harm_threshold: float = 0.7
    
    # Quality thresholds
    factual_accuracy_threshold: float = 0.8
    hallucination_threshold: float = 0.6
    
    # Fallback behavior
    allow_fallback_on_error: bool = True
    log_validation_errors: bool = True
    
    def __post_init__(self):
        """Set default validation checks if not provided"""
        if self.input_checks is None:
            self.input_checks = [
                "toxicity",
                "hate_speech",
                "sexual_content", 
                "violence",
                "self_harm",
                "jailbreak_attempts",
                "prompt_injection"
            ]
        
        if self.response_checks is None:
            self.response_checks = [
                "factual_accuracy",
                "hallucination_detection",
                "toxicity",
                "hate_speech",
                "sexual_content",
                "violence", 
                "self_harm",
                "jailbreak_attempts",
                "prompt_injection",
                "pii_detection",
                "sensitive_info_leak"
            ]
        
        if self.multimodal_checks is None:
            self.multimodal_checks = [
                "toxicity",
                "hate_speech",
                "sexual_content",
                "violence",
                "self_harm", 
                "jailbreak_attempts",
                "prompt_injection",
                "inappropriate_image_content"
            ]


# Default configuration
DEFAULT_GUARDRAILS_CONFIG = GuardrailsConfig()


# Validation rules for different contexts
VALIDATION_RULES = {
    "medical_context": {
        "input_checks": [
            "toxicity",
            "hate_speech",
            "self_harm",
            "jailbreak_attempts",
            "prompt_injection",
            "medical_advice_safety"
        ],
        "response_checks": [
            "factual_accuracy",
            "hallucination_detection",
            "medical_disclaimer",
            "pii_detection",
            "sensitive_info_leak"
        ],
        "safety_thresholds": {
            "self_harm_threshold": 0.5,  # Lower threshold for medical context
            "medical_advice_safety_threshold": 0.8
        }
    },
    
    "general_context": {
        "input_checks": [
            "toxicity",
            "hate_speech",
            "sexual_content",
            "violence",
            "self_harm",
            "jailbreak_attempts",
            "prompt_injection"
        ],
        "response_checks": [
            "factual_accuracy",
            "hallucination_detection",
            "toxicity",
            "hate_speech",
            "sexual_content",
            "violence",
            "self_harm",
            "jailbreak_attempts",
            "prompt_injection",
            "pii_detection"
        ]
    }
}


def get_validation_config(context: str = "general_context") -> GuardrailsConfig:
    """Get validation configuration for a specific context"""
    if context not in VALIDATION_RULES:
        context = "general_context"
    
    rules = VALIDATION_RULES[context]
    
    return GuardrailsConfig(
        input_checks=rules.get("input_checks", DEFAULT_GUARDRAILS_CONFIG.input_checks),
        response_checks=rules.get("response_checks", DEFAULT_GUARDRAILS_CONFIG.response_checks),
        multimodal_checks=rules.get("multimodal_checks", DEFAULT_GUARDRAILS_CONFIG.multimodal_checks)
    )


# Error messages for different validation failures
VALIDATION_ERROR_MESSAGES = {
    "input_validation_failed": "Your input contains inappropriate content. Please rephrase your question.",
    "response_validation_failed": "I cannot provide that information as it may violate safety guidelines.",
    "multimodal_validation_failed": "The image or text combination contains inappropriate content.",
    "validation_service_error": "Validation service temporarily unavailable. Proceeding with caution.",
    "toxicity_detected": "Content contains toxic language. Please rephrase.",
    "hate_speech_detected": "Content contains hate speech. Please rephrase.",
    "violence_detected": "Content contains violent language. Please rephrase.",
    "self_harm_detected": "Content contains self-harm references. Please rephrase.",
    "jailbreak_detected": "Attempt to bypass safety measures detected.",
    "prompt_injection_detected": "Attempt to manipulate the system detected.",
    "hallucination_detected": "Response may contain inaccurate information.",
    "pii_detected": "Response contains personal information that should not be shared.",
    "sensitive_info_detected": "Response contains sensitive information that should not be shared."
}


def get_error_message(violation_type: str) -> str:
    """Get appropriate error message for violation type"""
    return VALIDATION_ERROR_MESSAGES.get(violation_type, "Content validation failed. Please rephrase.") 