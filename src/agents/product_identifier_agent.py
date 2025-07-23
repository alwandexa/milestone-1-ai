from typing import Dict, Any, List
from langchain_core.prompts import ChatPromptTemplate
from src.agents.base_agent import BaseAgent
from src.infrastructure.openai_service import OpenAIService
from src.domain.document import ProductGroup

class ProductIdentifierAgent(BaseAgent):
    """Agent responsible for identifying specific products mentioned in queries"""
    
    def __init__(self, openai_service: OpenAIService, enable_guardrails: bool = True):
        super().__init__(openai_service, "ProductIdentifier", enable_guardrails)
        
        self.product_identifier_prompt = ChatPromptTemplate.from_template("""
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
    
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute product identification logic"""
        query = state.get("query", "")
        product_groups = state.get("identified_product_groups", [])
        
        # Validate input using Guardrails
        input_validation = self.validate_input(query, "Product identifier agent input validation")
        state["product_identifier_input_validation"] = input_validation
        
        if not input_validation["is_valid"] and input_validation.get("corrected_input"):
            query = input_validation["corrected_input"]
            state["query"] = query
            self.log(f"Input corrected due to validation: {query}", state)
        
        # If no product groups identified by supervisor, use all available
        if not product_groups:
            product_groups = [group.value for group in ProductGroup]
        
        # Generate product identification
        messages = self.product_identifier_prompt.format_messages(
            query=query,
            product_groups=product_groups
        )
        
        response = await self.llm.ainvoke(messages)
        response_text = response.content
        
        # Validate output using Guardrails
        output_validation = self.validate_output(response_text, query)
        state["product_identifier_output_validation"] = output_validation
        
        if not output_validation["is_valid"]:
            self.log("Product identifier output validation failed, using fallback", state)
            response_text = '{"identified_products": [], "relevant_product_groups": [], "therapeutic_areas": [], "confidence_score": 0.5, "reasoning": "Fallback due to validation failure"}'
        
        # Parse the response
        try:
            import json
            identification = json.loads(response_text)
        except:
            identification = {
                "identified_products": [],
                "relevant_product_groups": product_groups,
                "therapeutic_areas": [],
                "confidence_score": 0.5,
                "reasoning": "Default identification"
            }
        
        # Update state with product identification
        state["product_identification"] = identification
        state["specific_products"] = identification.get("identified_products", [])
        state["therapeutic_areas"] = identification.get("therapeutic_areas", [])
        state["identification_confidence"] = identification.get("confidence_score", 0.5)
        
        # Add tracing metadata
        state["current_step"] = "product_identification"
        state["workflow_logs"] = state.get("workflow_logs", [])
        state["workflow_logs"].append({
            "step": "product_identification",
            "agent": "ProductIdentifier",
            "status": "completed",
            "metadata": {
                "node_name": "product_identifier_agent",
                "tracing_enabled": True,
                "guardrails_enabled": self.enable_guardrails,
                "input_validation": input_validation,
                "output_validation": output_validation
            }
        })
        
        self.log(f"Product identification completed: {identification}", state)
        
        return state 