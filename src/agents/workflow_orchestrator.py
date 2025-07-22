from typing import Dict, Any, List
from src.agents.base_agent import BaseAgent
from src.agents.supervisor_agent import SupervisorAgent
from src.agents.product_identifier_agent import ProductIdentifierAgent
from src.agents.rag_agent import RAGAgent
from src.infrastructure.openai_service import OpenAIService
from src.domain.document import ProductKnowledgeQuery, ProductKnowledgeResponse

class WorkflowOrchestrator:
    """Orchestrates the entire agentic workflow for product knowledge queries"""
    
    def __init__(self, openai_service: OpenAIService, document_usecase=None):
        self.openai_service = openai_service
        self.document_usecase = document_usecase
        
        # Initialize agents
        self.supervisor = SupervisorAgent(openai_service)
        self.product_identifier = ProductIdentifierAgent(openai_service)
        self.rag_agent = RAGAgent(openai_service, document_usecase)
        
        # Agent registry
        self.agents = {
            "supervisor": self.supervisor,
            "product_identifier": self.product_identifier,
            "rag_agent": self.rag_agent
        }
    
    async def execute_workflow(self, query: ProductKnowledgeQuery) -> ProductKnowledgeResponse:
        """Execute the complete agentic workflow"""
        
        # Initialize state
        state = {
            "query": query.query,
            "product_group": query.product_group.value if query.product_group else None,
            "session_id": query.session_id,
            "user_context": query.user_context or {},
            "agent_logs": [],
            "workflow_started": True
        }
        
        try:
            # Step 1: Supervisor analysis
            self._log_workflow_step("Starting supervisor analysis", state)
            state = await self.supervisor.execute(state)
            
            # Step 2: Product identification
            self._log_workflow_step("Starting product identification", state)
            state = await self.product_identifier.execute(state)
            
            # Step 3: RAG retrieval and answer generation
            self._log_workflow_step("Starting RAG process", state)
            state = await self.rag_agent.execute(state)
            
            # Step 4: Prepare final response
            response = self._prepare_final_response(state)
            
            self._log_workflow_step("Workflow completed successfully", state)
            
            return response
            
        except Exception as e:
            self._log_workflow_step(f"Workflow failed with error: {str(e)}", state)
            return self._create_error_response(str(e), state)
    
    def _log_workflow_step(self, message: str, state: Dict[str, Any]) -> None:
        """Log workflow step"""
        print(f"[WorkflowOrchestrator] {message}")
        if "workflow_logs" not in state:
            state["workflow_logs"] = []
        state["workflow_logs"].append(f"[WorkflowOrchestrator] {message}")
    
    def _prepare_final_response(self, state: Dict[str, Any]) -> ProductKnowledgeResponse:
        """Prepare the final response from workflow state"""
        
        # Calculate confidence score based on various factors
        confidence_score = self._calculate_confidence_score(state)
        
        # Generate suggested follow-up
        suggested_follow_up = self._generate_suggested_follow_up(state)
        
        # Determine product group from state
        product_group = None
        if state.get("identified_product_groups"):
            try:
                from src.domain.document import ProductGroup
                product_group = ProductGroup(state["identified_product_groups"][0])
            except:
                pass
        
        return ProductKnowledgeResponse(
            answer=state.get("answer", "I couldn't find relevant information for your query."),
            sources=state.get("sources", []),
            product_group=product_group,
            confidence_score=confidence_score,
            suggested_follow_up=suggested_follow_up
        )
    
    def _calculate_confidence_score(self, state: Dict[str, Any]) -> float:
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
    
    def _generate_suggested_follow_up(self, state: Dict[str, Any]) -> str:
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
    
    def _create_error_response(self, error_message: str, state: Dict[str, Any]) -> ProductKnowledgeResponse:
        """Create error response when workflow fails"""
        return ProductKnowledgeResponse(
            answer=f"I encountered an error while processing your query: {error_message}. Please try rephrasing your question or contact support if the issue persists.",
            sources=[],
            product_group=None,
            confidence_score=0.0,
            suggested_follow_up="Please try asking your question again with different wording."
        ) 