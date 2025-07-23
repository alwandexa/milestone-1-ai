from typing import Dict, Any, Optional, List
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from src.agents.base_agent import BaseAgent
from src.infrastructure.openai_service import OpenAIService
from src.domain.persona import PersonaConfiguration, PersonaManager, PersonaType
import json
import os

class PersonaAgent(BaseAgent):
    """Agent that supports different personas and modes"""
    
    def __init__(self, openai_service: OpenAIService, name: str, enable_guardrails: bool = True):
        super().__init__(openai_service, name, enable_guardrails)
        self.persona_manager = PersonaManager()
        self.current_persona: Optional[PersonaConfiguration] = None
        
    def set_persona(self, persona_name: str) -> bool:
        """Set the current persona for the agent"""
        persona = self.persona_manager.get_persona(persona_name)
        if persona:
            self.current_persona = persona
            # Update LLM temperature based on persona
            self.llm.temperature = persona.temperature
            return True
        return False
    
    def get_current_persona(self) -> Optional[PersonaConfiguration]:
        """Get the current persona configuration"""
        return self.current_persona
    
    def get_available_personas(self) -> List[PersonaConfiguration]:
        """Get all available personas"""
        return self.persona_manager.get_all_personas()
    
    def get_personas_by_type(self, persona_type: PersonaType) -> List[PersonaConfiguration]:
        """Get personas by type"""
        return self.persona_manager.get_personas_by_type(persona_type)
    
    def create_persona_prompt(self, base_prompt: str, user_query: str) -> str:
        """Create a persona-aware prompt"""
        if not self.current_persona:
            return base_prompt
        
        # Combine base prompt with persona modifiers
        persona_prompt = f"{base_prompt}\n\n{self.current_persona.system_prompt_modifier}"
        
        # Add persona-specific user prompt modifier
        if self.current_persona.user_prompt_modifier:
            user_query = f"{self.current_persona.user_prompt_modifier}\n\n{user_query}"
        
        return persona_prompt, user_query
    
    def validate_with_persona_rules(self, input_text: str, context: str = "") -> Dict[str, Any]:
        """Validate input using persona-specific rules"""
        base_validation = super().validate_input(input_text, context)
        
        if not self.current_persona:
            return base_validation
        
        # Apply persona-specific validation rules
        if self.current_persona.strict_validation:
            # More strict validation for technical personas
            base_validation["strict_mode"] = True
            base_validation["confidence_threshold"] = 0.8
        
        if self.current_persona.clinical_safety_check:
            # Additional clinical safety checks
            base_validation["clinical_safety_check"] = True
            base_validation["requires_medical_validation"] = True
        
        return base_validation
    
    def format_response_with_persona(self, response: str, state: Dict[str, Any]) -> Dict[str, Any]:
        """Format response according to persona settings"""
        if not self.current_persona:
            return {"answer": response}
        
        formatted_response = {"answer": response}
        
        # Add persona-specific metadata
        formatted_response["persona"] = {
            "name": self.current_persona.name,
            "type": self.current_persona.persona_type.value,
            "style": self.current_persona.style
        }
        
        # Include sources if configured
        if self.current_persona.include_sources and "sources" in state:
            formatted_response["sources"] = state.get("sources", [])
        
        # Include confidence if configured
        if self.current_persona.include_confidence and "confidence_score" in state:
            formatted_response["confidence_score"] = state.get("confidence_score", 0.0)
        
        # Include suggestions if configured
        if self.current_persona.include_suggestions and "suggested_follow_up" in state:
            formatted_response["suggested_follow_up"] = state.get("suggested_follow_up")
        
        # Add persona-specific response format
        if self.current_persona.response_format == "structured":
            formatted_response["structured_response"] = self._create_structured_response(response)
        
        return formatted_response
    
    def _create_structured_response(self, response: str) -> Dict[str, Any]:
        """Create a structured response based on persona type"""
        if not self.current_persona:
            return {"content": response}
        
        structured = {"content": response}
        
        if self.current_persona.persona_type == PersonaType.RESPONSE_STYLE:
            if self.current_persona.style == "summary":
                structured["format"] = "bullet_points"
                structured["key_points"] = self._extract_key_points(response)
            elif self.current_persona.style == "technical":
                structured["format"] = "technical_specs"
                structured["technical_details"] = self._extract_technical_details(response)
        
        elif self.current_persona.persona_type == PersonaType.ROLE_BASED:
            if self.current_persona.style == "sales_assistant":
                structured["format"] = "sales_pitch"
                structured["benefits"] = self._extract_benefits(response)
                structured["value_proposition"] = self._extract_value_proposition(response)
            elif self.current_persona.style == "clinical_advisor":
                structured["format"] = "clinical_analysis"
                structured["safety_considerations"] = self._extract_safety_considerations(response)
                structured["clinical_applications"] = self._extract_clinical_applications(response)
        
        return structured
    
    def _extract_key_points(self, response: str) -> List[str]:
        """Extract key points from response for summary format"""
        # Simple extraction - in production, use more sophisticated NLP
        lines = response.split('\n')
        key_points = []
        for line in lines:
            line = line.strip()
            if line.startswith('•') or line.startswith('-') or line.startswith('*'):
                key_points.append(line[1:].strip())
        return key_points if key_points else [response]
    
    def _extract_technical_details(self, response: str) -> Dict[str, Any]:
        """Extract technical details from response"""
        # Placeholder for technical detail extraction
        return {
            "specifications": [],
            "compliance": [],
            "technical_analysis": response
        }
    
    def _extract_benefits(self, response: str) -> List[str]:
        """Extract benefits from sales response"""
        # Placeholder for benefit extraction
        return ["Benefit 1", "Benefit 2"]
    
    def _extract_value_proposition(self, response: str) -> str:
        """Extract value proposition from sales response"""
        return "Value proposition extracted from response"
    
    def _extract_safety_considerations(self, response: str) -> List[str]:
        """Extract safety considerations from clinical response"""
        # Placeholder for safety consideration extraction
        return ["Safety consideration 1", "Safety consideration 2"]
    
    def _extract_clinical_applications(self, response: str) -> List[str]:
        """Extract clinical applications from clinical response"""
        # Placeholder for clinical application extraction
        return ["Clinical application 1", "Clinical application 2"]
    
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the agent's main logic with persona support"""
        # This is a base implementation - specific agents should override this
        query = state.get("query", "")
        
        # Get persona configuration
        persona_name = state.get("persona_name")
        if persona_name:
            self.set_persona(persona_name)
        
        # Log persona usage
        if self.current_persona:
            self.log(f"Using persona: {self.current_persona.name} ({self.current_persona.style})", state)
        
        # Create persona-aware prompt
        base_prompt = "You are an AI assistant. Please help with the user's query."
        if self.current_persona:
            system_prompt, user_prompt = self.create_persona_prompt(base_prompt, query)
        else:
            system_prompt = base_prompt
            user_prompt = query
        
        # Generate response
        try:
            from langchain_core.messages import HumanMessage
            messages = [
                HumanMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            response = self.llm.invoke(messages)
            answer = response.content
            
            # Format response according to persona
            result = {"answer": answer}
            if self.current_persona:
                result = self.format_response_with_persona(answer, result)
            
            return result
            
        except Exception as e:
            self.log(f"Error generating response: {str(e)}", state)
            return {"answer": f"I apologize, but I encountered an error: {str(e)}"}

    async def execute_with_persona(self, state: Dict[str, Any], persona_name: Optional[str] = None) -> Dict[str, Any]:
        """Execute the agent with a specific persona"""
        if persona_name:
            self.set_persona(persona_name)
        
        # Log persona usage
        if self.current_persona:
            self.log(f"Using persona: {self.current_persona.name} ({self.current_persona.style})", state)
        
        # Execute the base agent logic
        result = await self.execute(state)
        
        # Format response according to persona
        if "answer" in result:
            result = self.format_response_with_persona(result["answer"], result)
        
        return result
    
    def get_persona_metadata(self) -> Dict[str, Any]:
        """Get metadata about the current persona"""
        if not self.current_persona:
            return {"persona": None}
        
        return {
            "persona": {
                "name": self.current_persona.name,
                "type": self.current_persona.persona_type.value,
                "style": self.current_persona.style,
                "description": self.current_persona.description,
                "temperature": self.current_persona.temperature,
                "response_format": self.current_persona.response_format,
                "include_sources": self.current_persona.include_sources,
                "include_confidence": self.current_persona.include_confidence,
                "include_suggestions": self.current_persona.include_suggestions,
                "strict_validation": self.current_persona.strict_validation,
                "clinical_safety_check": self.current_persona.clinical_safety_check
            }
        } 