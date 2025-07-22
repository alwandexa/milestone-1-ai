from typing import Dict, Any, List
from langchain_core.prompts import ChatPromptTemplate
from src.agents.base_agent import BaseAgent
from src.infrastructure.openai_service import OpenAIService
from src.domain.document import ProductGroup

class ProductIdentifierAgent(BaseAgent):
    """Agent responsible for identifying specific products mentioned in queries"""
    
    def __init__(self, openai_service: OpenAIService):
        super().__init__(openai_service, "ProductIdentifier")
        
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
        
        # If no product groups identified by supervisor, use all available
        if not product_groups:
            product_groups = [group.value for group in ProductGroup]
        
        # Generate product identification
        messages = self.product_identifier_prompt.format_messages(
            query=query,
            product_groups=product_groups
        )
        
        response = await self.llm.ainvoke(messages)
        
        # Parse the response
        try:
            import json
            identification = json.loads(response.content)
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
        
        self.log(f"Product identification completed: {identification}", state)
        
        return state 