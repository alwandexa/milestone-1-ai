from dotenv import load_dotenv
load_dotenv()

import uvicorn
from src.controller.document_controller import app
from src.usecase.document_usecase import DocumentUsecase
from src.repository.document_milvus_repository import DocumentMilvusRepository
from src.infrastructure.document_processor import DocumentProcessor
from src.infrastructure.openai_service import OpenAIService
from src.infrastructure.langgraph_chat import LangGraphChat
from src.infrastructure.persona_langgraph_chat import PersonaLangGraphChat
from src.infrastructure.monitoring_service import MonitoringService
from src.controller.dashboard_controller import set_monitoring_service

def setup_dependencies():
    """Setup dependency injection for product knowledge system"""
    # Initialize infrastructure
    openai_service = OpenAIService()
    document_processor = DocumentProcessor(openai_service=openai_service)
    
    # Initialize repository
    repository = DocumentMilvusRepository()
    
    # Initialize usecase
    document_usecase = DocumentUsecase(repository, document_processor, openai_service)
    
    # Initialize LangGraph chat with document usecase and Guardrails
    langgraph_chat = LangGraphChat(openai_service, document_usecase, enable_guardrails=True)
    
    # Initialize Persona LangGraph chat
    persona_langgraph_chat = PersonaLangGraphChat(openai_service, document_usecase, enable_guardrails=True)
    
    # Initialize monitoring service
    monitoring_service = MonitoringService()
    
    # Set the dependencies in the controllers
    from src.controller.document_controller import set_dependencies
    set_dependencies(document_usecase, langgraph_chat, persona_langgraph_chat)
    set_monitoring_service(monitoring_service)
    
    return document_usecase, langgraph_chat, persona_langgraph_chat, monitoring_service

if __name__ == "__main__":
    # Setup dependencies
    document_usecase, langgraph_chat, persona_langgraph_chat, monitoring_service = setup_dependencies()
    
    print("🚀 Starting iScaps Product Knowledge API...")
    print("📚 Product Knowledge System with Agentic Workflow")
    print("🛡️ Guardrails AI: Enabled" if langgraph_chat.enable_guardrails else "🛡️ Guardrails AI: Disabled")
    print("🔗 API available at: http://localhost:8000")
    print("📖 API documentation at: http://localhost:8000/docs")
    print("💊 Streamlit app available at: http://localhost:8501")
    print("📊 LangSmith tracing: Enabled")
    print("---")
    
    # Start the server
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False) 