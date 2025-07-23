from typing import List, Dict, Any, TypedDict, Optional, Union, AsyncGenerator
from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.runnables import RunnableLambda
from src.domain.document import DocumentChunk
from src.domain.persona import PersonaConfiguration, PersonaManager, PersonaType
from src.infrastructure.openai_service import OpenAIService
from src.infrastructure.guardrails_service import GuardrailsService
from src.usecase.document_usecase import DocumentUsecase
from src.infrastructure.langsmith_setup import setup_langsmith, get_tracer
from src.agents.persona_agent import PersonaAgent
import os
from pydantic import SecretStr
import base64
import asyncio


class PersonaChatState(TypedDict):
    query: str
    original_query: str
    search_results: List[DocumentChunk]
    search_count: int
    has_answer: bool
    context: str
    answer: str
    sources: List[str]
    image_data: Optional[bytes]
    multimodal_content: bool
    extracted_text: Optional[str]
    chain_of_thought: List[Dict[str, Any]]
    input_validation: Optional[Dict[str, Any]]
    response_validation: Optional[Dict[str, Any]]
    # Persona-specific fields
    persona_name: Optional[str]
    persona_config: Optional[Dict[str, Any]]
    persona_metadata: Optional[Dict[str, Any]]
    persona_response_format: Optional[Dict[str, Any]]


class PersonaLangGraphChat:
    def __init__(
        self,
        openai_service: OpenAIService,
        document_usecase: Optional[DocumentUsecase] = None,
        enable_guardrails: bool = True,
    ):
        self.openai_service = openai_service
        self.document_usecase = document_usecase
        self.enable_guardrails = enable_guardrails

        # Setup LangSmith
        self.langsmith_client = setup_langsmith()
        self.tracer = get_tracer()

        # Initialize Guardrails service only if enabled
        self.guardrails_service = None
        if self.enable_guardrails:
            try:
                self.guardrails_service = GuardrailsService(enable_guardrails=self.enable_guardrails)
            except Exception as e:
                print(f"⚠️ Warning: Guardrails service initialization failed: {e}")
                self.enable_guardrails = False

        # Initialize persona manager
        self.persona_manager = PersonaManager()
        
        # Initialize persona-aware agents
        self.persona_agent = PersonaAgent(openai_service, "persona_chat", enable_guardrails)

        # Initialize LLM with tracing
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.2,
            api_key=SecretStr(os.getenv("OPENAI_API_KEY", "")),
            callbacks=[self.tracer] if self.tracer else None,
        )
        
        # Initialize streaming LLM
        self.streaming_llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.2,
            api_key=SecretStr(os.getenv("OPENAI_API_KEY", "")),
            callbacks=[self.tracer] if self.tracer else None,
            streaming=True,
        )

        self.memory = MemorySaver()
        self.graph = self._create_graph()

    def _create_graph(self) -> StateGraph:
        """Create the persona-aware LangGraph workflow"""

        # Define the state schema
        workflow = StateGraph(PersonaChatState)

        # Add nodes with proper tracing
        workflow.add_node("validate_input", RunnableLambda(self._validate_input, name="validate_input"))
        workflow.add_node("process_multimodal_input", RunnableLambda(self._process_multimodal_input, name="process_multimodal_input"))
        workflow.add_node("search_documents", RunnableLambda(self._search_documents, name="search_documents"))
        workflow.add_node("evaluate_results", RunnableLambda(self._evaluate_results, name="evaluate_results"))
        workflow.add_node("generate_persona_answer", RunnableLambda(self._generate_persona_answer, name="generate_persona_answer"))
        workflow.add_node("validate_response", RunnableLambda(self._validate_response, name="validate_response"))
        workflow.add_node("modify_query", RunnableLambda(self._modify_query, name="modify_query"))

        # Define edges
        workflow.add_edge("validate_input", "process_multimodal_input")
        workflow.add_edge("process_multimodal_input", "search_documents")
        workflow.add_edge("search_documents", "evaluate_results")
        workflow.add_conditional_edges(
            "evaluate_results",
            self._should_generate_answer,
            {
                "generate_answer": "generate_persona_answer",
                "modify_query": "modify_query",
                "end": END
            }
        )
        workflow.add_edge("modify_query", "search_documents")
        workflow.add_edge("generate_persona_answer", "validate_response")
        workflow.add_edge("validate_response", END)

        return workflow

    def _validate_input(self, state: PersonaChatState) -> PersonaChatState:
        """Validate input with persona-specific rules"""
        query = state["query"]
        
        # Get persona configuration
        persona_name = state.get("persona_name")
        persona_config = None
        if persona_name:
            persona_config = self.persona_manager.get_persona(persona_name)
            if persona_config:
                # Set persona in agent
                self.persona_agent.set_persona(persona_name)
                state["persona_config"] = persona_config.to_dict()
                state["persona_metadata"] = self.persona_agent.get_persona_metadata()

        # Use persona-specific validation if available
        if persona_config and persona_config.strict_validation:
            validation_result = self.persona_agent.validate_with_persona_rules(query)
        else:
            # Standard validation
            validation_result = {
                "is_valid": True,
                "violations": [],
                "confidence_score": 1.0,
                "disabled": False
            }

        state["input_validation"] = validation_result
        
        if not validation_result["is_valid"]:
            state["error"] = f"Input validation failed: {validation_result['violations']}"
        
        return state

    def _validate_response(self, state: PersonaChatState) -> PersonaChatState:
        """Validate response with persona-specific rules"""
        answer = state.get("answer", "")
        
        # Get persona configuration
        persona_name = state.get("persona_name")
        persona_config = None
        if persona_name:
            persona_config = self.persona_manager.get_persona(persona_name)

        # Use persona-specific validation if available
        if persona_config and persona_config.strict_validation:
            validation_result = self.persona_agent.validate_output(answer, state["original_query"])
        else:
            # Standard validation
            validation_result = {
                "is_valid": True,
                "violations": [],
                "confidence_score": 1.0,
                "disabled": False
            }

        state["response_validation"] = validation_result
        
        if not validation_result["is_valid"]:
            state["error"] = f"Response validation failed: {validation_result['violations']}"
        
        return state

    def _process_multimodal_input(self, state: PersonaChatState) -> PersonaChatState:
        """Process multimodal input with persona awareness"""
        query = state["query"]
        image_data = state.get("image_data")
        
        if image_data:
            state["multimodal_content"] = True
            # Extract text from image (placeholder)
            state["extracted_text"] = "Text extracted from image"
            # Combine text and image query
            state["query"] = f"{query}\n[Image content: {state['extracted_text']}]"
        else:
            state["multimodal_content"] = False
            state["extracted_text"] = None
        
        return state

    def _search_documents(self, state: PersonaChatState) -> PersonaChatState:
        """Search documents with persona-aware context"""
        query = state["query"]
        
        if self.document_usecase:
            try:
                # Get persona-specific search context
                persona_name = state.get("persona_name")
                search_query = query
                
                if persona_name:
                    persona_config = self.persona_manager.get_persona(persona_name)
                    if persona_config:
                        # Modify search query based on persona
                        if persona_config.persona_type == PersonaType.ROLE_BASED:
                            if persona_config.style == "clinical_advisor":
                                search_query = f"clinical applications safety {query}"
                            elif persona_config.style == "technical_expert":
                                search_query = f"technical specifications compliance {query}"
                            elif persona_config.style == "sales_assistant":
                                search_query = f"benefits features value {query}"
                
                # Perform search
                search_results = self.document_usecase.search_documents(search_query, limit=5)
                state["search_results"] = search_results
                state["search_count"] = len(search_results)
                
                # Create context from search results
                context_parts = []
                sources = []
                
                for result in search_results:
                    context_parts.append(result.content)
                    if hasattr(result, 'document_id'):
                        sources.append(f"Document: {result.document_id}")
                
                state["context"] = "\n\n".join(context_parts)
                state["sources"] = sources
                
            except Exception as e:
                state["error"] = f"Search failed: {str(e)}"
                state["search_results"] = []
                state["search_count"] = 0
                state["context"] = ""
                state["sources"] = []
        else:
            state["search_results"] = []
            state["search_count"] = 0
            state["context"] = ""
            state["sources"] = []
        
        return state

    def _evaluate_results(self, state: PersonaChatState) -> PersonaChatState:
        """Evaluate search results with persona-specific criteria"""
        search_results = state.get("search_results", [])
        query = state["query"]
        
        if not search_results:
            state["has_answer"] = False
            return state
        
        # Get persona configuration for evaluation
        persona_name = state.get("persona_name")
        evaluation_criteria = "general"
        
        if persona_name:
            persona_config = self.persona_manager.get_persona(persona_name)
            if persona_config:
                if persona_config.persona_type == PersonaType.ROLE_BASED:
                    if persona_config.style == "clinical_advisor":
                        evaluation_criteria = "clinical_safety"
                    elif persona_config.style == "technical_expert":
                        evaluation_criteria = "technical_accuracy"
                    elif persona_config.style == "sales_assistant":
                        evaluation_criteria = "business_value"
        
        # Evaluate results based on persona
        relevant_results = []
        for result in search_results:
            relevance_score = self._calculate_relevance(result.content, query, evaluation_criteria)
            if relevance_score > 0.5:  # Threshold for relevance
                relevant_results.append(result)
        
        if relevant_results:
            state["has_answer"] = True
            state["search_results"] = relevant_results
            state["context"] = "\n\n".join([r.content for r in relevant_results])
        else:
            state["has_answer"] = False
        
        return state

    def _calculate_relevance(self, content: str, query: str, criteria: str) -> float:
        """Calculate relevance score based on persona criteria"""
        # Simple relevance calculation - in production, use more sophisticated NLP
        query_words = query.lower().split()
        content_words = content.lower().split()
        
        # Count matching words
        matches = sum(1 for word in query_words if word in content_words)
        
        # Adjust based on criteria
        if criteria == "clinical_safety":
            clinical_keywords = ["safety", "clinical", "patient", "medical", "risk"]
            clinical_matches = sum(1 for word in clinical_keywords if word in content.lower())
            return (matches + clinical_matches * 2) / len(query_words)
        elif criteria == "technical_accuracy":
            technical_keywords = ["specification", "technical", "compliance", "standard"]
            technical_matches = sum(1 for word in technical_keywords if word in content.lower())
            return (matches + technical_matches * 2) / len(query_words)
        elif criteria == "business_value":
            business_keywords = ["benefit", "value", "advantage", "feature", "roi"]
            business_matches = sum(1 for word in business_keywords if word in content.lower())
            return (matches + business_matches * 2) / len(query_words)
        else:
            return matches / len(query_words)

    def _should_generate_answer(self, state: PersonaChatState) -> str:
        """Determine if we should generate an answer or modify query"""
        if state.get("has_answer", False):
            return "generate_answer"
        elif state.get("search_count", 0) < 3:
            return "modify_query"
        else:
            return "end"

    def _modify_query(self, state: PersonaChatState) -> PersonaChatState:
        """Modify query for better search results"""
        original_query = state["original_query"]
        
        # Get persona-specific query modification
        persona_name = state.get("persona_name")
        if persona_name:
            persona_config = self.persona_manager.get_persona(persona_name)
            if persona_config:
                # Modify query based on persona
                if persona_config.persona_type == PersonaType.ROLE_BASED:
                    if persona_config.style == "clinical_advisor":
                        state["query"] = f"clinical applications and safety considerations for {original_query}"
                    elif persona_config.style == "technical_expert":
                        state["query"] = f"technical specifications and compliance requirements for {original_query}"
                    elif persona_config.style == "sales_assistant":
                        state["query"] = f"benefits and value propositions for {original_query}"
                else:
                    state["query"] = f"more information about {original_query}"
        else:
            state["query"] = f"more information about {original_query}"
        
        return state

    def _generate_persona_answer(self, state: PersonaChatState) -> PersonaChatState:
        """Generate answer with persona-specific formatting"""
        query = state["original_query"]
        context = state.get("context", "")
        search_results = state.get("search_results", [])
        
        # Get persona configuration
        persona_name = state.get("persona_name")
        persona_config = None
        if persona_name:
            persona_config = self.persona_manager.get_persona(persona_name)
        
        # Create persona-aware prompt
        base_prompt = f"""You are an AI assistant for product knowledge. Answer the user's question based on the provided context.

Context:
{context}

User Question: {query}

Please provide a helpful and accurate response based on the context provided."""

        if persona_config:
            # Use persona-specific prompt
            system_prompt, user_prompt = self.persona_agent.create_persona_prompt(base_prompt, query)
            
            # Update LLM temperature based on persona
            self.llm.temperature = persona_config.temperature
            
            # Create messages
            messages = [
                HumanMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
        else:
            # Use default prompt
            messages = [
                HumanMessage(content=base_prompt)
            ]

        try:
            # Generate response
            response = self.llm.invoke(messages)
            answer = response.content
            
            # Format response with persona
            if persona_config:
                formatted_response = self.persona_agent.format_response_with_persona(answer, state)
                state.update(formatted_response)
                state["persona_response_format"] = formatted_response.get("structured_response")
            else:
                state["answer"] = answer
            
            # Add sources if available
            if search_results and persona_config and persona_config.include_sources:
                sources = []
                for result in search_results:
                    if hasattr(result, 'document_id'):
                        sources.append(f"Document: {result.document_id}")
                state["sources"] = sources
            
        except Exception as e:
            state["error"] = f"Failed to generate answer: {str(e)}"
            state["answer"] = "I apologize, but I encountered an error while generating the response."
        
        return state

    def chat(self, query: str, session_id: Optional[str] = None, image_data: Optional[bytes] = None, persona_name: Optional[str] = None) -> Dict[str, Any]:
        """Chat with persona support"""
        # Initialize state
        state = PersonaChatState(
            query=query,
            original_query=query,
            search_results=[],
            search_count=0,
            has_answer=False,
            context="",
            answer="",
            sources=[],
            image_data=image_data,
            multimodal_content=False,
            extracted_text=None,
            chain_of_thought=[],
            input_validation=None,
            response_validation=None,
            persona_name=persona_name,
            persona_config=None,
            persona_metadata=None,
            persona_response_format=None
        )
        
        # Execute workflow
        try:
            result = self.graph.invoke(state)
            
            # Format response
            response = {
                "answer": result.get("answer", ""),
                "sources": result.get("sources", []),
                "search_count": result.get("search_count", 0),
                "context": result.get("context", ""),
                "multimodal_content": result.get("multimodal_content", False),
                "extracted_text": result.get("extracted_text"),
                "chain_of_thought": result.get("chain_of_thought", []),
                "input_validation": result.get("input_validation"),
                "response_validation": result.get("response_validation"),
                "persona_metadata": result.get("persona_metadata"),
                "persona_response_format": result.get("persona_response_format")
            }
            
            if result.get("error"):
                response["error"] = result["error"]
            
            return response
            
        except Exception as e:
            return {
                "answer": f"I apologize, but I encountered an error: {str(e)}",
                "sources": [],
                "search_count": 0,
                "context": "",
                "error": str(e),
                "persona_metadata": result.get("persona_metadata") if 'result' in locals() else None
            }

    async def chat_stream(self, query: str, session_id: Optional[str] = None, image_data: Optional[bytes] = None, persona_name: Optional[str] = None) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream chat with persona support"""
        # Initialize state
        state = PersonaChatState(
            query=query,
            original_query=query,
            search_results=[],
            search_count=0,
            has_answer=False,
            context="",
            answer="",
            sources=[],
            image_data=image_data,
            multimodal_content=False,
            extracted_text=None,
            chain_of_thought=[],
            input_validation=None,
            response_validation=None,
            persona_name=persona_name,
            persona_config=None,
            persona_metadata=None,
            persona_response_format=None
        )
        
        try:
            # Execute workflow
            result = self.graph.invoke(state)
            
            # Stream the response
            if result.get("answer"):
                # Get persona configuration for streaming
                persona_config = None
                if persona_name:
                    persona_config = self.persona_manager.get_persona(persona_name)
                
                # Stream the answer with persona formatting
                async for chunk in self._stream_persona_response(result["answer"], persona_config):
                    yield chunk
            
            # Send final metadata
            yield {
                "type": "metadata",
                "sources": result.get("sources", []),
                "search_count": result.get("search_count", 0),
                "context": result.get("context", ""),
                "multimodal_content": result.get("multimodal_content", False),
                "extracted_text": result.get("extracted_text"),
                "persona_metadata": result.get("persona_metadata"),
                "persona_response_format": result.get("persona_response_format")
            }
            
        except Exception as e:
            yield {
                "type": "error",
                "error": str(e)
            }

    async def _stream_persona_response(self, answer: str, persona_config: Optional[PersonaConfiguration]) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream response with persona-specific formatting"""
        if not persona_config:
            # Stream plain text
            words = answer.split()
            for i, word in enumerate(words):
                yield {
                    "type": "content",
                    "content": word + (" " if i < len(words) - 1 else ""),
                    "persona": None
                }
        else:
            # Stream with persona formatting
            words = answer.split()
            for i, word in enumerate(words):
                yield {
                    "type": "content",
                    "content": word + (" " if i < len(words) - 1 else ""),
                    "persona": {
                        "name": persona_config.name,
                        "type": persona_config.persona_type.value,
                        "style": persona_config.style
                    }
                }

    def get_available_personas(self) -> List[Dict[str, Any]]:
        """Get all available personas"""
        return [persona.to_dict() for persona in self.persona_manager.get_all_personas()]

    def get_personas_by_type(self, persona_type: PersonaType) -> List[Dict[str, Any]]:
        """Get personas by type"""
        return [persona.to_dict() for persona in self.persona_manager.get_personas_by_type(persona_type)] 