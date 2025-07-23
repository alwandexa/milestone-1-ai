"""
Guardrails AI Configuration
"""

from typing import Dict, Any, List
from dataclasses import dataclass


@dataclass
class GuardrailsConfig:
    """Configuration for Guardrails AI validation"""
    
    # Enable/disable different validation types
    input_validation_enabled: bool = True
    response_validation_enabled: bool = True
    multimodal_validation_enabled: bool = True
    
    # Validation thresholds
    toxic_language_threshold: float = 0.5
    competitor_check_enabled: bool = True
    competitor_list: List[str] = None
    
    # Error handling
    on_fail_action: str = "exception"  # "exception", "log", "correct"
    
    def __post_init__(self):
        if self.competitor_list is None:
            self.competitor_list = [
                "Apple", "Microsoft", "Google", "Amazon", "Meta", 
                "Facebook", "Twitter", "X", "Tesla", "Netflix"
            ]


def get_validation_config() -> GuardrailsConfig:
    """Get the default validation configuration"""
    return GuardrailsConfig()


def get_error_message(validation_type: str, violations: List[Dict[str, Any]]) -> str:
    """Generate user-friendly error messages for validation failures"""
    
    if not violations:
        return "Validation passed"
    
    error_messages = []
    
    for violation in violations:
        violation_type = violation.get("type", "unknown")
        
        if violation_type == "toxic_language":
            error_messages.append("Content contains inappropriate language")
        elif violation_type == "competitor_mention":
            error_messages.append("Content mentions competitors")
        elif violation_type == "validation_error":
            error_messages.append("Content validation failed")
        else:
            error_messages.append(violation.get("error", "Unknown validation error"))
    
    return "; ".join(error_messages)


def get_guardrails_settings() -> Dict[str, Any]:
    """Get Guardrails AI settings for the application"""
    return {
        "enable_guardrails": True,
        "validation_config": get_validation_config(),
        "error_messages": {
            "input_validation": "Your input contains inappropriate content. Please rephrase your question.",
            "response_validation": "The response contains inappropriate content and has been blocked.",
            "multimodal_validation": "The image and text combination contains inappropriate content."
        }
    } 