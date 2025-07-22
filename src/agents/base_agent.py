from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI
from src.infrastructure.openai_service import OpenAIService

class BaseAgent(ABC):
    """Base class for all agents in the product knowledge system"""
    
    def __init__(self, openai_service: OpenAIService, name: str):
        self.openai_service = openai_service
        self.name = name
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.1,
            api_key=openai_service.api_key
        )
    
    @abstractmethod
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the agent's main logic"""
        pass
    
    def log(self, message: str, state: Dict[str, Any]) -> None:
        """Log agent activity"""
        print(f"[{self.name}] {message}")
        if "agent_logs" not in state:
            state["agent_logs"] = []
        state["agent_logs"].append(f"[{self.name}] {message}") 