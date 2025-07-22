from dotenv import load_dotenv
load_dotenv()

import uvicorn
from src.controller.document_controller import app
from src.usecase.document_usecase import DocumentUsecase
from src.repository.document_milvus_repository import DocumentMilvusRepository
from src.infrastructure.document_processor import DocumentProcessor
from src.infrastructure.openai_service import OpenAIService
from src.infrastructure.langgraph_chat import LangGraphChat

def setup_dependencies():
    """Setup dependency injection for document chatbot"""
    # Initialize infrastructure
    openai_service = OpenAIService()
    document_processor = DocumentProcessor()
    
    # Initialize repository
    repository = DocumentMilvusRepository()
    
    # Initialize usecase
    document_usecase = DocumentUsecase(repository, document_processor, openai_service)
    
    # Initialize LangGraph chat with document usecase
    langgraph_chat = LangGraphChat(openai_service, document_usecase)
    
    # Set the dependencies in the controller
    import src.controller.document_controller as controller_module
    controller_module.document_usecase = document_usecase
    controller_module.langgraph_chat = langgraph_chat
    
    return document_usecase, langgraph_chat

if __name__ == "__main__":
    # Setup dependencies
    document_usecase, langgraph_chat = setup_dependencies()
    
    # Start the server
    uvicorn.run(app, host="0.0.0.0", port=8000) 