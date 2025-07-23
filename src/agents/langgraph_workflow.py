from typing import List, Dict, Any, TypedDict, Optional, Annotated
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from src.domain.document import ProductGroup, DocumentQuery, DocumentResponse, DocumentChunk
from src.infrastructure.openai_service import OpenAIService
from src.agents.supervisor_agent import SupervisorAgent
from src.agents.product_identifier_agent import ProductIdentifierAgent
from src.agents.rag_agent import RAGAgent
from src.infrastructure.langsmith_setup import get_tracer
import json

# Define the state schema for LangGraph
class ProductKnowledgeState(TypedDict):
    """State for the product knowledge workflow"""
    # Input
    query: str
    product_group: Optional[str]
    session_id: Optional[str]
    user_context: Optional[Dict[str, Any]]
    
    # Supervisor analysis
    supervisor_analysis: Optional[Dict[str, Any]]
    identified_product_groups: List[str]
    query_type: str
    required_agents: List[str]
    priority: str
    
    # Product identification
    product_identification: Optional[Dict[str, Any]]
    specific_products: List[str]
    therapeutic_areas: List[str]
    identification_confidence: float
    
    # RAG results
    retrieved_chunks: List[DocumentChunk]
    context: str
    answer: str
    sources: List[str]
    
    # Final response
    confidence_score: float
    suggested_follow_up: Optional[str]
    
    # Workflow control
    current_step: str
    workflow_logs: List[str]
    error: Optional[str]

class LangGraphProductKnowledgeWorkflow:
    """LangGraph-based workflow for product knowledge queries using individual agents"""
    
    def __init__(self, openai_service: OpenAIService, document_usecase=None, enable_guardrails: bool = True):
        self.openai_service = openai_service
        self.document_usecase = document_usecase
        self.enable_guardrails = enable_guardrails
        
        # Setup LangSmith tracing
        self.tracer = get_tracer()
        
        # Initialize individual agents with Guardrails
        self.supervisor_agent = SupervisorAgent(openai_service, enable_guardrails)
        self.product_identifier_agent = ProductIdentifierAgent(openai_service, enable_guardrails)
        self.rag_agent = RAGAgent(openai_service, document_usecase, enable_guardrails)
        
        # Initialize LLM for response generation with tracing
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.1,
            api_key=openai_service.api_key,
            callbacks=[self.tracer] if self.tracer else None,
        )
        
        # Create memory first
        self.memory = MemorySaver()
        
        # Create the graph
        self.graph = self._create_graph()
    
    def _create_graph(self) -> StateGraph:
        """Create the LangGraph workflow using individual agents with proper tracing"""
        
        # Define the state schema
        workflow = StateGraph(ProductKnowledgeState)
        
        # Create properly traced nodes
        supervisor_node = RunnableLambda(
            self._supervisor_node, 
            name="supervisor_agent"
        )
        
        product_identifier_node = RunnableLambda(
            self._product_identifier_node, 
            name="product_identifier_agent"
        )
        
        rag_node = RunnableLambda(
            self._rag_node, 
            name="rag_agent"
        )
        
        response_generator_node = RunnableLambda(
            self._response_generator, 
            name="response_generator"
        )
        
        error_handler_node = RunnableLambda(
            self._error_handler, 
            name="error_handler"
        )
        
        # Add nodes to the workflow
        workflow.add_node("supervisor_agent", supervisor_node)
        workflow.add_node("product_identifier_agent", product_identifier_node)
        workflow.add_node("rag_agent", rag_node)
        workflow.add_node("response_generator", response_generator_node)
        workflow.add_node("error_handler", error_handler_node)
        
        # Define conditional edges with proper routing
        workflow.add_conditional_edges(
            "supervisor_agent",
            RunnableLambda(self._should_continue_or_error, name="should_continue_or_error"),
            {
                "product_identifier_agent": "product_identifier_agent", 
                "error_handler": "error_handler"
            }
        )
        
        workflow.add_conditional_edges(
            "product_identifier_agent",
            RunnableLambda(self._should_continue_or_error, name="should_continue_or_error"),
            {
                "rag_agent": "rag_agent", 
                "error_handler": "error_handler"
            }
        )
        
        workflow.add_conditional_edges(
            "rag_agent",
            RunnableLambda(self._should_continue_or_error, name="should_continue_or_error"),
            {
                "response_generator": "response_generator", 
                "error_handler": "error_handler"
            }
        )
        
        # Add final edges
        workflow.add_edge("response_generator", END)
        workflow.add_edge("error_handler", END)
        
        # Set entry point
        workflow.set_entry_point("supervisor_agent")
        
        # Return the compiled workflow
        return workflow.compile(checkpointer=self.memory)
    
    async def _supervisor_node(self, state: ProductKnowledgeState) -> ProductKnowledgeState:
        """Supervisor node using the SupervisorAgent with proper tracing"""
        try:
            # Initialize workflow logs if not present
            if "workflow_logs" not in state:
                state["workflow_logs"] = []
            
            state["current_step"] = "supervisor_analysis"
            
            # Add tracing metadata
            state["workflow_logs"].append({
                "step": "supervisor_analysis",
                "agent": "Supervisor",
                "status": "started",
                "metadata": {
                    "node_name": "supervisor_agent",
                    "tracing_enabled": True,
                    "guardrails_enabled": self.enable_guardrails
                }
            })
            
            self._log_workflow_step("Starting supervisor analysis", state)
            
            # Execute supervisor agent
            updated_state = await self.supervisor_agent.execute(state)
            
            # Update state with supervisor results
            state.update(updated_state)
            
            # Update tracing metadata
            state["workflow_logs"].append({
                "step": "supervisor_analysis",
                "agent": "Supervisor",
                "status": "completed",
                "metadata": {
                    "node_name": "supervisor_agent",
                    "tracing_enabled": True,
                    "guardrails_enabled": self.enable_guardrails,
                    "supervisor_analysis": state.get("supervisor_analysis", {})
                }
            })
            
            self._log_workflow_step("Supervisor analysis completed", state)
            
        except Exception as e:
            state["error"] = f"Supervisor agent error: {str(e)}"
            state["workflow_logs"].append({
                "step": "supervisor_analysis",
                "agent": "Supervisor",
                "status": "error",
                "metadata": {
                    "node_name": "supervisor_agent",
                    "tracing_enabled": True,
                    "guardrails_enabled": self.enable_guardrails,
                    "error": str(e)
                }
            })
            self._log_workflow_step(f"Supervisor agent failed: {str(e)}", state)
        
        return state
    
    async def _product_identifier_node(self, state: ProductKnowledgeState) -> ProductKnowledgeState:
        """Product identifier node using the ProductIdentifierAgent with proper tracing"""
        try:
            state["current_step"] = "product_identification"
            
            # Add tracing metadata
            state["workflow_logs"].append({
                "step": "product_identification",
                "agent": "ProductIdentifier",
                "status": "started",
                "metadata": {
                    "node_name": "product_identifier_agent",
                    "tracing_enabled": True,
                    "guardrails_enabled": self.enable_guardrails
                }
            })
            
            self._log_workflow_step("Starting product identification", state)
            
            # Execute product identifier agent
            updated_state = await self.product_identifier_agent.execute(state)
            
            # Update state with product identification results
            state.update(updated_state)
            
            # Update tracing metadata
            state["workflow_logs"].append({
                "step": "product_identification",
                "agent": "ProductIdentifier",
                "status": "completed",
                "metadata": {
                    "node_name": "product_identifier_agent",
                    "tracing_enabled": True,
                    "guardrails_enabled": self.enable_guardrails,
                    "product_identification": state.get("product_identification", {})
                }
            })
            
            self._log_workflow_step("Product identification completed", state)
            
        except Exception as e:
            state["error"] = f"Product identifier agent error: {str(e)}"
            state["workflow_logs"].append({
                "step": "product_identification",
                "agent": "ProductIdentifier",
                "status": "error",
                "metadata": {
                    "node_name": "product_identifier_agent",
                    "tracing_enabled": True,
                    "guardrails_enabled": self.enable_guardrails,
                    "error": str(e)
                }
            })
            self._log_workflow_step(f"Product identifier agent failed: {str(e)}", state)
        
        return state
    
    async def _rag_node(self, state: ProductKnowledgeState) -> ProductKnowledgeState:
        """RAG node using the RAGAgent with proper tracing"""
        try:
            state["current_step"] = "rag_processing"
            
            # Add tracing metadata
            state["workflow_logs"].append({
                "step": "rag_processing",
                "agent": "RAG",
                "status": "started",
                "metadata": {
                    "node_name": "rag_agent",
                    "tracing_enabled": True,
                    "guardrails_enabled": self.enable_guardrails
                }
            })
            
            self._log_workflow_step("Starting RAG process", state)
            
            # Execute RAG agent
            updated_state = await self.rag_agent.execute(state)
            
            # Update state with RAG results
            state.update(updated_state)
            
            # Update tracing metadata
            state["workflow_logs"].append({
                "step": "rag_processing",
                "agent": "RAG",
                "status": "completed",
                "metadata": {
                    "node_name": "rag_agent",
                    "tracing_enabled": True,
                    "guardrails_enabled": self.enable_guardrails,
                    "chunks_retrieved": len(state.get("retrieved_chunks", [])),
                    "sources_count": len(state.get("sources", []))
                }
            })
            
            self._log_workflow_step(f"RAG completed with {len(state.get('retrieved_chunks', []))} chunks retrieved", state)
            
        except Exception as e:
            state["error"] = f"RAG agent error: {str(e)}"
            state["workflow_logs"].append({
                "step": "rag_processing",
                "agent": "RAG",
                "status": "error",
                "metadata": {
                    "node_name": "rag_agent",
                    "tracing_enabled": True,
                    "guardrails_enabled": self.enable_guardrails,
                    "error": str(e)
                }
            })
            self._log_workflow_step(f"RAG agent failed: {str(e)}", state)
        
        return state
    
    def _response_generator(self, state: ProductKnowledgeState) -> ProductKnowledgeState:
        """Generate final response with confidence score and suggestions"""
        try:
            state["current_step"] = "response_generation"
            
            # Add tracing metadata
            state["workflow_logs"].append({
                "step": "response_generation",
                "agent": "ResponseGenerator",
                "status": "started",
                "metadata": {
                    "node_name": "response_generator",
                    "tracing_enabled": True,
                    "guardrails_enabled": self.enable_guardrails
                }
            })
            
            self._log_workflow_step("Generating final response", state)
            
            # Calculate confidence score
            confidence_score = self._calculate_confidence_score(state)
            
            # Generate suggested follow-up
            suggested_follow_up = self._generate_suggested_follow_up(state)
            
            # Update state
            state["confidence_score"] = confidence_score
            state["suggested_follow_up"] = suggested_follow_up
            
            # Update tracing metadata
            state["workflow_logs"].append({
                "step": "response_generation",
                "agent": "ResponseGenerator",
                "status": "completed",
                "metadata": {
                    "node_name": "response_generator",
                    "tracing_enabled": True,
                    "guardrails_enabled": self.enable_guardrails,
                    "confidence_score": confidence_score
                }
            })
            
            self._log_workflow_step("Final response generated successfully", state)
            
        except Exception as e:
            state["error"] = f"Response generator error: {str(e)}"
            state["workflow_logs"].append({
                "step": "response_generation",
                "agent": "ResponseGenerator",
                "status": "error",
                "metadata": {
                    "node_name": "response_generator",
                    "tracing_enabled": True,
                    "guardrails_enabled": self.enable_guardrails,
                    "error": str(e)
                }
            })
            self._log_workflow_step(f"Response generator failed: {str(e)}", state)
        
        return state
    
    def _error_handler(self, state: ProductKnowledgeState) -> ProductKnowledgeState:
        """Handle errors in the workflow with proper tracing"""
        error = state.get("error", "Unknown error")
        
        # Add tracing metadata
        state["workflow_logs"].append({
            "step": "error_handling",
            "agent": "ErrorHandler",
            "status": "started",
            "metadata": {
                "node_name": "error_handler",
                "tracing_enabled": True,
                "guardrails_enabled": self.enable_guardrails,
                "error": error
            }
        })
        
        self._log_workflow_step(f"Error handler processing: {error}", state)
        
        # Set default values for error case
        state["answer"] = f"I encountered an error while processing your query: {error}. Please try rephrasing your question or contact support if the issue persists."
        state["sources"] = []
        state["confidence_score"] = 0.0
        state["suggested_follow_up"] = "Please try asking your question again with different wording."
        
        # Update tracing metadata
        state["workflow_logs"].append({
            "step": "error_handling",
            "agent": "ErrorHandler",
            "status": "completed",
            "metadata": {
                "node_name": "error_handler",
                "tracing_enabled": True,
                "guardrails_enabled": self.enable_guardrails,
                "error": error
            }
        })
        
        return state
    
    def _should_continue_or_error(self, state: ProductKnowledgeState) -> str:
        """Determine if workflow should continue or go to error handler"""
        if state.get("error"):
            return "error_handler"
        else:
            current_step = state.get("current_step", "supervisor_agent")
            
            # Map current step to next step
            step_mapping = {
                "supervisor_analysis": "product_identifier_agent",
                "product_identification": "rag_agent",
                "rag_processing": "response_generator"
            }
            
            return step_mapping.get(current_step, "error_handler")
    
    def _calculate_confidence_score(self, state: ProductKnowledgeState) -> float:
        """Calculate confidence score based on various factors"""
        score = 0.5  # Base score
        
        # Factor in identification confidence
        identification_confidence = state.get("identification_confidence", 0.5)
        score += identification_confidence * 0.2
        
        # Factor in number of retrieved chunks
        chunks = state.get("retrieved_chunks", [])
        if len(chunks) > 0:
            score += min(len(chunks) * 0.1, 0.3)
        
        # Factor in supervisor analysis
        supervisor_analysis = state.get("supervisor_analysis", {})
        if supervisor_analysis.get("reasoning"):
            score += 0.1
        
        return min(score, 1.0)
    
    def _generate_suggested_follow_up(self, state: ProductKnowledgeState) -> str:
        """Generate suggested follow-up questions"""
        query_type = state.get("query_type", "general")
        product_groups = state.get("identified_product_groups", [])
        
        suggestions = []
        
        if query_type == "product_info":
            suggestions.append("Would you like to know about the dosage and administration?")
            suggestions.append("Do you need information about side effects and contraindications?")
        elif query_type == "clinical_data":
            suggestions.append("Would you like to see comparative efficacy data?")
            suggestions.append("Do you need information about patient outcomes?")
        elif query_type == "dosage":
            suggestions.append("Would you like to know about special populations (elderly, renal impairment)?")
            suggestions.append("Do you need information about drug interactions?")
        else:
            suggestions.append("Would you like to know more about this product's clinical benefits?")
            suggestions.append("Do you need information about patient selection criteria?")
        
        return suggestions[0] if suggestions else None
    
    def _log_workflow_step(self, message: str, state: ProductKnowledgeState) -> None:
        """Log workflow step"""
        print(f"[LangGraphWorkflow] {message}")
        if "workflow_logs" not in state:
            state["workflow_logs"] = []
        state["workflow_logs"].append(f"[LangGraphWorkflow] {message}")
    
    async def execute_workflow(self, query: DocumentQuery) -> DocumentResponse:
        """Execute the LangGraph workflow with proper tracing"""
        
        # Initialize state
        initial_state = {
            "query": query.query,
            "product_group": query.product_group.value if query.product_group else None,
            "session_id": query.session_id,
            "user_context": query.user_context or {},
            "workflow_logs": [],
            "current_step": "start"
        }
        
        try:
            # Execute the graph with proper tracing
            config = {"configurable": {"thread_id": query.session_id or "default"}}
            
            # Use invoke instead of ainvoke for better tracing
            result = self.graph.invoke(initial_state, config)
            
            # The result should be the final state directly
            final_state = result
            
            # Determine product group from state
            product_group = None
            if final_state.get("identified_product_groups"):
                try:
                    product_group = ProductGroup(final_state["identified_product_groups"][0])
                except:
                    pass
            
            # Create response
            response = DocumentResponse(
                answer=final_state.get("answer", "I couldn't find relevant information for your query."),
                sources=final_state.get("sources", []),
                product_group=product_group,
                confidence_score=final_state.get("confidence_score", 0.0),
                suggested_follow_up=final_state.get("suggested_follow_up")
            )
            
            # Add workflow logs to response if available
            if hasattr(response, 'workflow_logs'):
                response.workflow_logs = final_state.get("workflow_logs", [])
            
            return response
            
        except Exception as e:
            # Return error response
            return DocumentResponse(
                answer=f"I encountered an error while processing your query: {str(e)}. Please try rephrasing your question or contact support if the issue persists.",
                sources=[],
                product_group=None,
                confidence_score=0.0,
                suggested_follow_up="Please try asking your question again with different wording."
            ) 