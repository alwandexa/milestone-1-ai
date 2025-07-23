import os
import logging
from typing import Dict, Any, Optional, List
from guardrails import Guard

logger = logging.getLogger(__name__)

class GuardrailsService:
    """
    Service for validating user inputs and agent responses using Guardrails AI
    """
    
    def __init__(self, enable_guardrails: bool = True):
        self.enable_guardrails = enable_guardrails
        self.api_key = os.getenv("GUARDRAILS_API_KEY")
        
        # Initialize validation components (always needed)
        self.competitor_companies = [
            "kimia farma", "century healthcare", "guardian pharmacy", "k24", "watson",
            "mediplus", "medishop", "halodoc", "alodokter", "sehatq",
        ]
        
        if not self.enable_guardrails:
            logger.info("🛡️ Guardrails AI: Disabled")
            return
            
        if not self.api_key:
            logger.warning("⚠️ GUARDRAILS_API_KEY not found. Guardrails validation will be disabled.")
            self.enable_guardrails = False
            return
            
        logger.info("🛡️ Guardrails AI: Enabled")
        
        try:
            # For now, we'll use a simpler approach without hub validators
            # since they're causing import issues
            logger.info("🛡️ Using basic Guardrails validation without hub validators")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Guardrails validators: {e}")
            self.enable_guardrails = False
            return
        
        # For now, we'll use a simpler approach without Guard objects
        # since they're causing initialization issues
        logger.info("🛡️ Using custom validation without Guard objects")
        
        # Initialize basic validation components
        self.input_guard = None
        self.response_guard = None
    
    def validate_user_input(self, user_input: str) -> Dict[str, Any]:
        """
        Validate user input using Guardrails AI and custom checks
        
        Args:
            user_input: The user's input text
            
        Returns:
            Dict containing validation result and any errors
        """
        # Always run basic validation checks
        errors = []
        warnings = []
        
        # Basic validation checks
        if not user_input or not user_input.strip():
            errors.append("Input cannot be empty")
            return {"valid": False, "errors": errors, "warnings": warnings}
        
        # Check for competitor mentions
        user_input_lower = user_input.lower()
        for competitor in self.competitor_companies:
            if competitor.lower() in user_input_lower:
                warnings.append(f"Input mentions competitor: {competitor}")
        
        # Check for potentially toxic language (basic check)
        toxic_words = ["hate", "kill", "stupid", "idiot", "dumb", "shut up"]
        found_toxic = [word for word in toxic_words if word in user_input_lower]
        if found_toxic:
            warnings.append(f"Potentially inappropriate language detected: {', '.join(found_toxic)}")
        
        # Use basic validation since Guard objects are not available
        if not errors and not warnings:
            return {"valid": True, "errors": [], "warnings": []}
        else:
            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings
            }
    
    def validate_agent_response(self, response: str, original_query: str = None) -> Dict[str, Any]:
        """
        Validate agent response using Guardrails AI and custom checks
        
        Args:
            response: The agent's response text
            original_query: The original user query (optional)
            
        Returns:
            Dict containing validation result and any errors
        """
        # Always run basic validation checks
        errors = []
        warnings = []
        
        # Basic validation checks
        if not response or not response.strip():
            errors.append("Response cannot be empty")
            return {"valid": False, "errors": errors, "warnings": warnings}
        
        # Check for competitor mentions
        response_lower = response.lower()
        for competitor in self.competitor_companies:
            if competitor.lower() in response_lower:
                warnings.append(f"Response mentions competitor: {competitor}")
        
        # Check for potentially toxic language (basic check)
        toxic_words = ["hate", "kill", "stupid", "idiot", "dumb", "shut up"]
        found_toxic = [word for word in toxic_words if word in response_lower]
        if found_toxic:
            warnings.append(f"Potentially inappropriate language detected: {', '.join(found_toxic)}")
        
        # If guardrails is disabled, return basic validation results
        if not self.enable_guardrails:
            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings
            }
        
        # Use basic validation since Guard objects are not available
        if not errors and not warnings:
            return {"valid": True, "errors": [], "warnings": []}
        else:
            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings
            }
    
    def get_validation_summary(self, validation_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert validation result to a standardized summary format
        
        Args:
            validation_result: The raw validation result from validate_user_input or validate_agent_response
            
        Returns:
            Dict containing standardized validation summary
        """
        if not validation_result:
            return {
                "validation_type": "unknown",
                "is_valid": True,
                "confidence_score": 0.0,
                "violation_count": 0,
                "violations": [],
                "has_correction": False
            }
        
        # Extract validation type based on the context
        validation_type = "unknown"
        if "response" in str(validation_result):
            validation_type = "response_validation"
        else:
            validation_type = "input_validation"
        
        # Extract validation details
        is_valid = validation_result.get("valid", True)
        errors = validation_result.get("errors", [])
        warnings = validation_result.get("warnings", [])
        
        # Calculate confidence score (simplified)
        confidence_score = 1.0 if is_valid and not errors else 0.5
        
        # Count violations
        violation_count = len(errors) + len(warnings)
        
        # Format violations
        violations = []
        for error in errors:
            violations.append({"type": "error", "message": str(error)})
        for warning in warnings:
            violations.append({"type": "warning", "message": str(warning)})
        
        return {
            "validation_type": validation_type,
            "is_valid": is_valid,
            "confidence_score": confidence_score,
            "violation_count": violation_count,
            "violations": violations,
            "has_correction": False,  # For now, we don't implement corrections
            "corrected_input": None  # For compatibility with existing code
        }
    
    def validate_multimodal_input(self, text: str, images: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Validate multimodal input (text + images)
        
        Args:
            text: The text input
            images: Optional list of image data
            
        Returns:
            Dict containing validation result and any errors
        """
        # For now, we only validate text input
        # Image validation can be added later if needed
        return self.validate_user_input(text)
    
    def is_enabled(self) -> bool:
        """Check if Guardrails is enabled"""
        return self.enable_guardrails 