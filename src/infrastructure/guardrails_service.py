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
        
        if not self.enable_guardrails:
            logger.info("🛡️ Guardrails AI: Disabled")
            return
            
        if not self.api_key:
            logger.warning("⚠️ GUARDRAILS_API_KEY not found. Guardrails validation will be disabled.")
            self.enable_guardrails = False
            return
            
        logger.info("🛡️ Guardrails AI: Enabled")
        
        # Try to install and import validators
        self.toxic_language_validator = None
        self.competitor_check_validator = None
        self.regex_match_validator = None
        
        try:
            # Install validators if not available
            from guardrails.hub import install
            
            # Install ToxicLanguage validator
            try:
                install("ToxicLanguage")
                from guardrails.hub import ToxicLanguage
                self.toxic_language_validator = ToxicLanguage()
                logger.info("✅ ToxicLanguage validator installed and loaded")
            except Exception as e:
                logger.warning(f"⚠️ Failed to install ToxicLanguage validator: {e}")
            
            # Install CompetitorCheck validator
            try:
                install("CompetitorCheck")
                from guardrails.hub import CompetitorCheck
                
                # Define competitor companies for iScaps
                self.competitor_companies = [
                    "shopee", "tokopedia", "lazada", "bukalapak", "blibli", 
                    "tiktok shop", "instagram shop", "facebook marketplace",
                    "amazon", "ebay", "alibaba", "jd.id", "zalora"
                ]
                self.competitor_check_validator = CompetitorCheck(competitors=self.competitor_companies)
                logger.info("✅ CompetitorCheck validator installed and loaded")
            except Exception as e:
                logger.warning(f"⚠️ Failed to install CompetitorCheck validator: {e}")
            
            # Install RegexMatch validator
            try:
                install("RegexMatch")
                from guardrails.hub import RegexMatch
                self.regex_match_validator = RegexMatch()
                logger.info("✅ RegexMatch validator installed and loaded")
            except Exception as e:
                logger.warning(f"⚠️ Failed to install RegexMatch validator: {e}")
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize Guardrails validators: {e}")
            self.enable_guardrails = False
            return
        
        # Initialize guards with available validators
        validators = []
        if self.toxic_language_validator:
            validators.append(self.toxic_language_validator)
        if self.competitor_check_validator:
            validators.append(self.competitor_check_validator)
        
        if not validators:
            logger.warning("⚠️ No validators available. Guardrails validation will be disabled.")
            self.enable_guardrails = False
            return
        
        # Initialize input validation guard
        self.input_guard = Guard.from_string(
            """
            You are a validation system for a product knowledge chatbot.
            
            The user's input should be:
            1. A valid question about products, services, or general inquiries
            2. Not contain toxic or harmful language
            3. Not be a competitor promotion
            4. Be relevant to the product knowledge domain
            
            If the input is valid, respond with "VALID".
            If the input is invalid, explain why it's invalid.
            """,
            validators=validators
        )
        
        # Initialize response validation guard
        self.response_guard = Guard.from_string(
            """
            You are validating an AI agent's response to ensure it:
            1. Is helpful and informative
            2. Does not contain toxic or harmful content
            3. Does not promote competitors
            4. Stays within the product knowledge domain
            5. Provides accurate and relevant information
            
            If the response is valid, respond with "VALID".
            If the response is invalid, explain why it's invalid.
            """,
            validators=validators
        )
    
    def validate_user_input(self, user_input: str) -> Dict[str, Any]:
        """
        Validate user input using Guardrails AI
        
        Args:
            user_input: The user's input text
            
        Returns:
            Dict containing validation result and any errors
        """
        if not self.enable_guardrails:
            return {"valid": True, "errors": [], "warnings": []}
        
        try:
            # Validate using the input guard
            validation_result = self.input_guard(user_input)
            
            if validation_result.validated_output == "VALID":
                return {
                    "valid": True,
                    "errors": [],
                    "warnings": []
                }
            else:
                return {
                    "valid": False,
                    "errors": [str(validation_result.validated_output)],
                    "warnings": []
                }
                
        except Exception as e:
            logger.error(f"Guardrails validation error: {e}")
            return {
                "valid": False,
                "errors": [f"Validation error: {str(e)}"],
                "warnings": []
            }
    
    def validate_agent_response(self, response: str, original_query: str = None) -> Dict[str, Any]:
        """
        Validate agent response using Guardrails AI
        
        Args:
            response: The agent's response text
            original_query: The original user query (optional)
            
        Returns:
            Dict containing validation result and any errors
        """
        if not self.enable_guardrails:
            return {"valid": True, "errors": [], "warnings": []}
        
        try:
            # Validate using the response guard
            validation_result = self.response_guard(response)
            
            if validation_result.validated_output == "VALID":
                return {
                    "valid": True,
                    "errors": [],
                    "warnings": []
                }
            else:
                return {
                    "valid": False,
                    "errors": [str(validation_result.validated_output)],
                    "warnings": []
                }
                
        except Exception as e:
            logger.error(f"Guardrails validation error: {e}")
            return {
                "valid": False,
                "errors": [f"Validation error: {str(e)}"],
                "warnings": []
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