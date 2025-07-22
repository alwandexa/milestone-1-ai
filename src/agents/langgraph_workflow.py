from typing import List, Dict, Any, TypedDict, Optional, Annotated
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from src.domain.document import ProductGroup, ProductKnowledgeQuery, ProductKnowledgeResponse, DocumentChunk
from src.infrastructure.openai_service import OpenAIService
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
    """LangGraph-based workflow for product knowledge queries"""
    
    def __init__(self, openai_service: OpenAIService, document_usecase=None):
        self.openai_service = openai_service
        self.document_usecase = document_usecase
        
        # Initialize LLM
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.1,
            api_key=openai_service.api_key
        )
        
        # Create memory first
        self.memory = MemorySaver()
        
        # Create the graph
        self.graph = self._create_graph()
    
    def _create_graph(self) -> StateGraph:
        """Create the LangGraph workflow"""
        
        # Define the state schema
        workflow = StateGraph(ProductKnowledgeState)
        
        # Add nodes
        workflow.add_node("supervisor_agent", self._supervisor_agent)
        workflow.add_node("product_identifier_agent", self._product_identifier_agent)
        workflow.add_node("rag_agent", self._rag_agent)
        workflow.add_node("response_generator", self._response_generator)
        workflow.add_node("error_handler", self._error_handler)
        
        # Define edges with conditional routing
        workflow.add_conditional_edges(
            "supervisor_agent",
            self._should_continue_or_error,
            {"product_identifier_agent": "product_identifier_agent", "error_handler": "error_handler"}
        )
        
        workflow.add_conditional_edges(
            "product_identifier_agent",
            self._should_continue_or_error,
            {"rag_agent": "rag_agent", "error_handler": "error_handler"}
        )
        
        workflow.add_conditional_edges(
            "rag_agent",
            self._should_continue_or_error,
            {"response_generator": "response_generator", "error_handler": "error_handler"}
        )
        
        workflow.add_edge("response_generator", END)
        workflow.add_edge("error_handler", END)
        
        # Set entry point
        workflow.set_entry_point("supervisor_agent")
        
        # Return the compiled workflow
        return workflow.compile(checkpointer=self.memory)
    
    def _supervisor_agent(self, state: ProductKnowledgeState) -> ProductKnowledgeState:
        """Supervisor agent that analyzes the query and determines workflow"""
        try:
            state["current_step"] = "supervisor_analysis"
            self._log_workflow_step("Starting supervisor analysis", state)
            
            # Supervisor prompt
            supervisor_prompt = ChatPromptTemplate.from_template("""
You are a supervisor agent responsible for orchestrating product knowledge queries for a pharmaceutical sales team.

Your role is to:
1. Analyze the user's query
2. Determine the appropriate workflow steps
3. Coordinate between different specialized agents
4. Ensure the final response is comprehensive and accurate

Current query: {query}
Available product groups: {product_groups}

Based on the query, determine:
1. What product group(s) are relevant
2. What type of information is being requested
3. What agents should be involved

Respond with a JSON structure:
{{
    "product_groups": ["list", "of", "relevant", "groups"],
    "query_type": "product_info|comparison|clinical_data|dosage|side_effects|etc",
    "required_agents": ["list", "of", "agent", "names"],
    "priority": "high|medium|low",
    "reasoning": "explanation of your decision"
}}
""")
            
            # Get available product groups
            product_groups = [group.value for group in ProductGroup]
            
            # Generate supervisor analysis
            messages = supervisor_prompt.format_messages(
                query=state["query"],
                product_groups=product_groups
            )
            
            response = self.llm.invoke(messages)
            
            # Parse the response
            try:
                analysis = json.loads(response.content)
            except:
                analysis = {
                    "product_groups": [],
                    "query_type": "general",
                    "required_agents": ["product_identifier", "rag_agent"],
                    "priority": "medium",
                    "reasoning": "Default analysis"
                }
            
            # Update state
            state["supervisor_analysis"] = analysis
            state["identified_product_groups"] = analysis.get("product_groups", [])
            state["query_type"] = analysis.get("query_type", "general")
            state["required_agents"] = analysis.get("required_agents", [])
            state["priority"] = analysis.get("priority", "medium")
            
            self._log_workflow_step(f"Supervisor analysis completed: {analysis}", state)
            
        except Exception as e:
            state["error"] = f"Supervisor agent error: {str(e)}"
            self._log_workflow_step(f"Supervisor agent failed: {str(e)}", state)
        
        return state
    
    def _product_identifier_agent(self, state: ProductKnowledgeState) -> ProductKnowledgeState:
        """Product identifier agent that identifies specific products"""
        try:
            state["current_step"] = "product_identification"
            self._log_workflow_step("Starting product identification", state)
            
            # Product identifier prompt
            product_identifier_prompt = ChatPromptTemplate.from_template("""
You are a product identification agent for a pharmaceutical company. Your job is to identify specific products mentioned in user queries.

Available product groups: {product_groups}

User query: {query}

Analyze the query and identify:
1. Specific product names mentioned
2. Product groups that are relevant
3. Any brand names or generic names
4. Therapeutic areas mentioned

Respond with a JSON structure:
{{
    "identified_products": ["list", "of", "specific", "product", "names"],
    "relevant_product_groups": ["list", "of", "product", "groups"],
    "therapeutic_areas": ["list", "of", "therapeutic", "areas"],
    "confidence_score": 0.95,
    "reasoning": "explanation of your identification"
}}

If no specific products are mentioned, focus on the product groups and therapeutic areas.
""")
            
            query = state["query"]
            product_groups = state.get("identified_product_groups", [])
            
            # If no product groups identified by supervisor, use all available
            if not product_groups:
                product_groups = [group.value for group in ProductGroup]
            
            # Generate product identification
            messages = product_identifier_prompt.format_messages(
                query=query,
                product_groups=product_groups
            )
            
            response = self.llm.invoke(messages)
            
            # Parse the response
            try:
                identification = json.loads(response.content)
            except:
                identification = {
                    "identified_products": [],
                    "relevant_product_groups": product_groups,
                    "therapeutic_areas": [],
                    "confidence_score": 0.5,
                    "reasoning": "Default identification"
                }
            
            # Update state
            state["product_identification"] = identification
            state["specific_products"] = identification.get("identified_products", [])
            state["therapeutic_areas"] = identification.get("therapeutic_areas", [])
            state["identification_confidence"] = identification.get("confidence_score", 0.5)
            
            self._log_workflow_step(f"Product identification completed: {identification}", state)
            
        except Exception as e:
            state["error"] = f"Product identifier agent error: {str(e)}"
            self._log_workflow_step(f"Product identifier agent failed: {str(e)}", state)
        
        return state
    
    def _rag_agent(self, state: ProductKnowledgeState) -> ProductKnowledgeState:
        """RAG agent that retrieves and generates answers"""
        try:
            state["current_step"] = "rag_processing"
            self._log_workflow_step("Starting RAG process", state)
            
            query = state["query"]
            product_groups = state.get("identified_product_groups", [])
            specific_products = state.get("specific_products", [])
            
            # Build search query with product context
            search_query = self._build_search_query(query, product_groups, specific_products)
            
            # Retrieve relevant documents
            chunks = []
            try:
                if self.document_usecase:
                    # Convert product group strings to enum if needed
                    product_group_enum = None
                    if product_groups:
                        try:
                            product_group_enum = ProductGroup(product_groups[0])
                        except ValueError:
                            pass
                    
                    chunks = self.document_usecase.search_documents(search_query, top_k=8, product_group=product_group_enum)
                    
                    # Filter by product group if specified
                    if product_groups and chunks:
                        filtered_chunks = []
                        for chunk in chunks:
                            if hasattr(chunk, 'product_group') and chunk.product_group:
                                if chunk.product_group.value in product_groups:
                                    filtered_chunks.append(chunk)
                            else:
                                # If no product group specified, include it
                                filtered_chunks.append(chunk)
                        chunks = filtered_chunks[:5]  # Limit to top 5 after filtering
                else:
                    self._log_workflow_step("No document usecase available, using empty chunks", state)
            except Exception as e:
                self._log_workflow_step(f"Error retrieving documents: {e}", state)
                chunks = []
            
            # Prepare context from retrieved chunks
            context = self._prepare_context(chunks)
            
            # RAG prompt
            rag_prompt = ChatPromptTemplate.from_template("""
You are a pharmaceutical product knowledge assistant. Your role is to provide accurate, helpful information about pharmaceutical products to sales representatives.

Context from product knowledge base:
{context}

User query: {query}

Product groups involved: {product_groups}
Specific products mentioned: {specific_products}

Instructions:
1. Provide accurate information based on the context provided
2. If the context doesn't contain enough information, clearly state what information is missing
3. Be professional and helpful for sales representatives
4. Include relevant details like dosage, indications, contraindications, side effects when available
5. If comparing products, be objective and factual

Generate a comprehensive response that would be helpful for a sales representative during a detailing session.
""")
            
            # Generate answer using LLM
            messages = rag_prompt.format_messages(
                context=context,
                query=query,
                product_groups=product_groups,
                specific_products=specific_products
            )
            
            response = self.llm.invoke(messages)
            
            # Update state with RAG results
            state["retrieved_chunks"] = chunks
            state["context"] = context
            state["answer"] = response.content
            state["sources"] = [chunk.document_id for chunk in chunks if hasattr(chunk, 'document_id')]
            
            self._log_workflow_step(f"RAG completed with {len(chunks)} chunks retrieved", state)
            
        except Exception as e:
            state["error"] = f"RAG agent error: {str(e)}"
            self._log_workflow_step(f"RAG agent failed: {str(e)}", state)
        
        return state
    
    def _response_generator(self, state: ProductKnowledgeState) -> ProductKnowledgeState:
        """Generate final response with confidence score and suggestions"""
        try:
            state["current_step"] = "response_generation"
            self._log_workflow_step("Generating final response", state)
            
            # Calculate confidence score
            confidence_score = self._calculate_confidence_score(state)
            
            # Generate suggested follow-up
            suggested_follow_up = self._generate_suggested_follow_up(state)
            
            # Update state
            state["confidence_score"] = confidence_score
            state["suggested_follow_up"] = suggested_follow_up
            
            self._log_workflow_step("Final response generated successfully", state)
            
        except Exception as e:
            state["error"] = f"Response generator error: {str(e)}"
            self._log_workflow_step(f"Response generator failed: {str(e)}", state)
        
        return state
    
    def _error_handler(self, state: ProductKnowledgeState) -> ProductKnowledgeState:
        """Handle errors in the workflow"""
        error = state.get("error", "Unknown error")
        self._log_workflow_step(f"Error handler processing: {error}", state)
        
        # Set default values for error case
        state["answer"] = f"I encountered an error while processing your query: {error}. Please try rephrasing your question or contact support if the issue persists."
        state["sources"] = []
        state["confidence_score"] = 0.0
        state["suggested_follow_up"] = "Please try asking your question again with different wording."
        
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
    
    def _build_search_query(self, query: str, product_groups: List[str], specific_products: List[str]) -> str:
        """Build an enhanced search query"""
        enhanced_query = query
        
        # Add product groups to search
        if product_groups:
            enhanced_query += f" {' '.join(product_groups)}"
        
        # Add specific products to search
        if specific_products:
            enhanced_query += f" {' '.join(specific_products)}"
        
        return enhanced_query
    
    def _prepare_context(self, chunks: List[DocumentChunk]) -> str:
        """Prepare context from retrieved chunks"""
        if not chunks:
            return "No relevant product information found in the knowledge base."
        
        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            product_info = ""
            if hasattr(chunk, 'product_group') and chunk.product_group:
                product_info = f" [Product Group: {chunk.product_group.value}]"
            
            context_parts.append(f"Source {i}{product_info}:\n{chunk.content}\n")
        
        return "\n".join(context_parts)
    
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
    
    async def execute_workflow(self, query: ProductKnowledgeQuery) -> ProductKnowledgeResponse:
        """Execute the LangGraph workflow"""
        
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
            # Execute the graph
            config = {"configurable": {"thread_id": query.session_id or "default"}}
            result = await self.graph.ainvoke(initial_state, config)
            
            # Extract final state
            final_state = result.get("supervisor_agent", result)
            
            # Determine product group from state
            product_group = None
            if final_state.get("identified_product_groups"):
                try:
                    product_group = ProductGroup(final_state["identified_product_groups"][0])
                except:
                    pass
            
            # Create response
            response = ProductKnowledgeResponse(
                answer=final_state.get("answer", "I couldn't find relevant information for your query."),
                sources=final_state.get("sources", []),
                product_group=product_group,
                confidence_score=final_state.get("confidence_score", 0.0),
                suggested_follow_up=final_state.get("suggested_follow_up")
            )
            
            return response
            
        except Exception as e:
            # Return error response
            return ProductKnowledgeResponse(
                answer=f"I encountered an error while processing your query: {str(e)}. Please try rephrasing your question or contact support if the issue persists.",
                sources=[],
                product_group=None,
                confidence_score=0.0,
                suggested_follow_up="Please try asking your question again with different wording."
            ) 