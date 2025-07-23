from typing import Dict, Any, List
from langchain_core.prompts import ChatPromptTemplate
from src.agents.base_agent import BaseAgent
from src.infrastructure.openai_service import OpenAIService
from src.domain.document import ProductGroup

class SupervisorAgent(BaseAgent):
    """Supervisor agent that orchestrates the entire product knowledge workflow"""
    
    def __init__(self, openai_service: OpenAIService, enable_guardrails: bool = True):
        super().__init__(openai_service, "Supervisor", enable_guardrails)
        
        self.supervisor_prompt = ChatPromptTemplate.from_template("""
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
    
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute supervisor logic to orchestrate the workflow"""
        query = state.get("query", "")
        
        # Validate input using Guardrails
        input_validation = self.validate_input(query, "Supervisor agent input validation")
        state["supervisor_input_validation"] = input_validation
        
        if not input_validation["is_valid"] and input_validation.get("corrected_input"):
            query = input_validation["corrected_input"]
            state["query"] = query
            self.log(f"Input corrected due to validation: {query}", state)
        
        # Get available product groups
        product_groups = [group.value for group in ProductGroup]
        
        # Generate supervisor analysis
        messages = self.supervisor_prompt.format_messages(
            query=query,
            product_groups=product_groups
        )
        
        response = await self.llm.ainvoke(messages)
        response_text = response.content
        
        # Validate output using Guardrails
        output_validation = self.validate_output(response_text, query)
        state["supervisor_output_validation"] = output_validation
        
        if not output_validation["is_valid"]:
            self.log("Supervisor output validation failed, using fallback", state)
            response_text = '{"product_groups": [], "query_type": "general", "required_agents": ["product_identifier", "rag_agent"], "priority": "medium", "reasoning": "Fallback due to validation failure"}'
        
        # Parse the response (assuming it's JSON)
        try:
            import json
            analysis = json.loads(response_text)
        except:
            # Fallback if JSON parsing fails
            analysis = {
                "product_groups": [],
                "query_type": "general",
                "required_agents": ["product_identifier", "rag_agent"],
                "priority": "medium",
                "reasoning": "Default analysis"
            }
        
        # Update state with supervisor analysis
        state["supervisor_analysis"] = analysis
        state["identified_product_groups"] = analysis.get("product_groups", [])
        state["query_type"] = analysis.get("query_type", "general")
        state["required_agents"] = analysis.get("required_agents", [])
        state["priority"] = analysis.get("priority", "medium")
        
        # Add tracing metadata
        state["current_step"] = "supervisor_analysis"
        state["workflow_logs"] = state.get("workflow_logs", [])
        state["workflow_logs"].append({
            "step": "supervisor_analysis",
            "agent": "Supervisor",
            "status": "completed",
            "metadata": {
                "node_name": "supervisor_agent",
                "tracing_enabled": True,
                "guardrails_enabled": self.enable_guardrails,
                "input_validation": input_validation,
                "output_validation": output_validation
            }
        })
        
        self.log(f"Supervisor analysis completed: {analysis}", state)
        
        return state 