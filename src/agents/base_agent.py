from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnableLambda
from src.infrastructure.openai_service import OpenAIService
from src.infrastructure.guardrails_service import GuardrailsService
from src.infrastructure.langsmith_setup import get_tracer
import os

class BaseAgent(ABC):
    """Base class for all agents in the product knowledge system"""
    
    def __init__(self, openai_service: OpenAIService, name: str, enable_guardrails: bool = True):
        self.openai_service = openai_service
        self.name = name
        self.enable_guardrails = enable_guardrails
        
        # Setup LangSmith tracing
        self.tracer = get_tracer()
        
        # Initialize LLM with tracing
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.1,
            api_key=openai_service.api_key,
            callbacks=[self.tracer] if self.tracer else None,
        )
        
        # Initialize Guardrails service
        self.guardrails_service = None
        if self.enable_guardrails:
            try:
                self.guardrails_service = GuardrailsService()
            except Exception as e:
                print(f"⚠️ Warning: Guardrails service initialization failed for {name}: {e}")
                self.enable_guardrails = False
    
    @abstractmethod
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the agent's main logic"""
        pass
    
    def log(self, message: str, state: Dict[str, Any]) -> None:
        """Log agent activity with tracing metadata"""
        print(f"[{self.name}] {message}")
        if "agent_logs" not in state:
            state["agent_logs"] = []
        
        log_entry = {
            "agent": self.name,
            "message": message,
            "timestamp": str(os.getenv("TIMESTAMP", "")),
            "metadata": {
                "agent_name": self.name,
                "tracing_enabled": True,
                "guardrails_enabled": self.enable_guardrails
            }
        }
        state["agent_logs"].append(log_entry)
    
    def validate_input(self, input_text: str, context: str = "") -> Dict[str, Any]:
        """Validate input using Guardrails AI"""
        if not self.enable_guardrails or not self.guardrails_service:
            return {
                "is_valid": True,
                "violations": [],
                "confidence_score": 1.0,
                "disabled": True
            }
        
        try:
            result = self.guardrails_service.validate_user_input(input_text, context)
            return {
                "is_valid": result.is_valid,
                "violations": result.violations,
                "confidence_score": result.confidence_score,
                "corrected_input": result.corrected_input,
                "disabled": False
            }
        except Exception as e:
            self.log(f"Guardrails validation failed: {str(e)}", {})
            return {
                "is_valid": True,  # Default to valid on error
                "violations": [{"error": str(e)}],
                "confidence_score": 0.0,
                "disabled": True
            }
    
    def validate_output(self, output_text: str, original_input: str) -> Dict[str, Any]:
        """Validate output using Guardrails AI"""
        if not self.enable_guardrails or not self.guardrails_service:
            return {
                "is_valid": True,
                "violations": [],
                "confidence_score": 1.0,
                "disabled": True
            }
        
        try:
            result = self.guardrails_service.validate_agent_response(output_text, original_input)
            return {
                "is_valid": result.is_valid,
                "violations": result.violations,
                "confidence_score": result.confidence_score,
                "corrected_output": result.corrected_input,
                "disabled": False
            }
        except Exception as e:
            self.log(f"Guardrails validation failed: {str(e)}", {})
            return {
                "is_valid": True,  # Default to valid on error
                "violations": [{"error": str(e)}],
                "confidence_score": 0.0,
                "disabled": True
            }
    
    def create_runnable(self, func, name: str = None):
        """Create a properly traced runnable for LangGraph"""
        runnable_name = name or f"{self.name}_{func.__name__}"
        return RunnableLambda(func, name=runnable_name) 