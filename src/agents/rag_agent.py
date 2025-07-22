from typing import Dict, Any, List
from langchain_core.prompts import ChatPromptTemplate
from src.agents.base_agent import BaseAgent
from src.infrastructure.openai_service import OpenAIService
from src.domain.document import ProductGroup, DocumentChunk

class RAGAgent(BaseAgent):
    """Agent responsible for retrieving and generating answers from product knowledge"""
    
    def __init__(self, openai_service: OpenAIService, document_usecase=None):
        super().__init__(openai_service, "RAG")
        self.document_usecase = document_usecase
        
        self.rag_prompt = ChatPromptTemplate.from_template("""
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
    
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute RAG logic to retrieve and generate answers"""
        query = state.get("query", "")
        product_groups = state.get("identified_product_groups", [])
        specific_products = state.get("specific_products", [])
        
        # Build search query with product context
        search_query = self._build_search_query(query, product_groups, specific_products)
        
        # Retrieve relevant documents
        try:
            if self.document_usecase:
                chunks = self.document_usecase.search_documents(search_query, top_k=8)
                
                # Filter by product group if specified
                if product_groups:
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
                chunks = []
        except Exception as e:
            self.log(f"Error retrieving documents: {e}", state)
            chunks = []
        
        # Prepare context from retrieved chunks
        context = self._prepare_context(chunks)
        
        # Generate answer using LLM
        messages = self.rag_prompt.format_messages(
            context=context,
            query=query,
            product_groups=product_groups,
            specific_products=specific_products
        )
        
        response = await self.llm.ainvoke(messages)
        
        # Update state with RAG results
        state["retrieved_chunks"] = chunks
        state["context"] = context
        state["answer"] = response.content
        state["sources"] = [chunk.document_id for chunk in chunks if hasattr(chunk, 'document_id')]
        
        self.log(f"RAG completed with {len(chunks)} chunks retrieved", state)
        
        return state
    
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