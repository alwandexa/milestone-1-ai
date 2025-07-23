import os
import logging
from typing import Dict, Any, Optional, List
from guardrails import Guard
from guardrails.hub import ToxicLanguage, CompetitorCheck, RegexMatch

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
        
        # Initialize validators
        self.toxic_language_validator = ToxicLanguage()
        
        # Define competitor companies for iScaps
        self.competitor_companies = [
            "shopee", "tokopedia", "lazada", "bukalapak", "blibli", 
            "tiktok shop", "instagram shop", "facebook marketplace",
            "amazon", "ebay", "alibaba", "jd.id", "zalora"
        ]
        self.competitor_check_validator = CompetitorCheck(competitors=self.competitor_companies)
        
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
            validators=[
                self.toxic_language_validator,
                self.competitor_check_validator
            ]
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
            validators=[
                self.toxic_language_validator,
                self.competitor_check_validator
            ]
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
    
    def validate_agent_response(self, response: str) -> Dict[str, Any]:
        """
        Validate agent response using Guardrails AI
        
        Args:
            response: The agent's response text
            
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