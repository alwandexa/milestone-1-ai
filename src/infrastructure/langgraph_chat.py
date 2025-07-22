from typing import List, Dict, Any, TypedDict, Optional, Union
from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from src.domain.document import DocumentChunk
from src.infrastructure.openai_service import OpenAIService
from src.usecase.document_usecase import DocumentUsecase
from src.infrastructure.langsmith_setup import setup_langsmith, get_tracer
import os
from pydantic import SecretStr
import base64


class ChatState(TypedDict):
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


class LangGraphChat:
    def __init__(
        self,
        openai_service: OpenAIService,
        document_usecase: Optional[DocumentUsecase] = None,
    ):
        self.openai_service = openai_service
        self.document_usecase = document_usecase

        # Setup LangSmith
        self.langsmith_client = setup_langsmith()
        self.tracer = get_tracer()

        # Initialize LLM with tracing
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.7,
            api_key=SecretStr(os.getenv("OPENAI_API_KEY", "")),
            callbacks=[self.tracer] if self.tracer else None,
        )

        self.memory = MemorySaver()
        self.graph = self._create_graph()

    def _create_graph(self) -> StateGraph:
        """Create the LangGraph workflow with multimodal support"""

        # Define the state schema
        workflow = StateGraph(ChatState)

        # Add nodes
        workflow.add_node("process_multimodal_input", self._process_multimodal_input)
        workflow.add_node("search_documents", self._search_documents)
        workflow.add_node("evaluate_results", self._evaluate_results)
        workflow.add_node("generate_answer", self._generate_answer)
        workflow.add_node("modify_query", self._modify_query)

        # Define edges
        workflow.add_edge("process_multimodal_input", "search_documents")
        workflow.add_edge("search_documents", "evaluate_results")
        workflow.add_conditional_edges(
            "evaluate_results",
            self._should_generate_answer,
            {"generate_answer": "generate_answer", "modify_query": "modify_query"},
        )
        workflow.add_edge("modify_query", "search_documents")
        workflow.add_edge("generate_answer", END)

        # Set entry point
        workflow.set_entry_point("process_multimodal_input")

        # Return the compiled workflow, but type as Any to avoid mypy type error
        return workflow.compile(checkpointer=self.memory)  # type: ignore

    def _process_multimodal_input(self, state: ChatState) -> ChatState:
        """Process multimodal input (text + image)"""
        query = state["query"]
        image_data = state.get("image_data")
        
        if image_data:
            # Extract text from image if present
            try:
                extracted_text = self.openai_service.extract_text_from_image(image_data)
                state["extracted_text"] = extracted_text
                
                # Combine original query with extracted text
                combined_query = f"{query}\n\nExtracted text from image: {extracted_text}"
                state["query"] = combined_query
                state["multimodal_content"] = True
            except Exception as e:
                # If image processing fails, continue with original query
                state["multimodal_content"] = False
                state["extracted_text"] = None
        else:
            state["multimodal_content"] = False
            state["extracted_text"] = None
        
        return state

    def _search_documents(self, state: ChatState) -> ChatState:
        """Search for relevant document chunks"""
        query = state["query"]

        # Get search results from document usecase
        if self.document_usecase:
            chunks = self.document_usecase.search_documents(query, top_k=5)
        else:
            chunks = []  # Fallback if no document usecase

        state["search_results"] = chunks
        state["search_count"] = state.get("search_count", 0) + 1

        return state

    def _evaluate_results(self, state: ChatState) -> ChatState:
        """Evaluate if search results contain the answer"""
        query = state["query"]
        search_results = state["search_results"]

        if not search_results:
            state["has_answer"] = False
            return state

        # Create context from search results
        context = "\n\n".join([chunk.content for chunk in search_results])

        # Ask LLM to evaluate if context contains answer
        evaluation_prompt = ChatPromptTemplate.from_template(
            """
        Given the user question and the provided context, determine if the context contains enough information to answer the question.
        
        Question: {query}
        Context: {context}
        
        Respond with only 'YES' if the context contains the answer, or 'NO' if it doesn't.
        """
        )

        chain = evaluation_prompt | self.llm
        result = chain.invoke({"query": query, "context": context})

        # Convert result to string and check
        result_text = str(result.content) if hasattr(result, "content") else str(result)
        state["has_answer"] = "YES" in result_text.upper()
        state["context"] = context

        return state

    def _should_generate_answer(self, state: ChatState) -> str:
        """Determine if we should generate answer or modify query"""
        has_answer = state.get("has_answer", False)
        search_count = state.get("search_count", 0)

        if has_answer or search_count >= 3:  # Max 3 search attempts
            return "generate_answer"
        else:
            return "modify_query"

    def _modify_query(self, state: ChatState) -> ChatState:
        """Modify the query to get better results"""
        original_query = state["original_query"]
        search_count = state["search_count"]

        modification_prompt = ChatPromptTemplate.from_template(
            """
        The original query didn't find relevant information. Modify the query to be more specific or use different keywords.
        
        Original query: {original_query}
        Search attempt: {search_count}
        
        Provide a modified query that might find better results:
        """
        )

        chain = modification_prompt | self.llm
        result = chain.invoke(
            {"original_query": original_query, "search_count": search_count}
        )

        # Convert result to string and strip
        result_text = str(result.content) if hasattr(result, "content") else str(result)
        state["query"] = result_text.strip()

        return state

    def _generate_answer(self, state: ChatState) -> ChatState:
        """Generate final answer based on context and multimodal content"""
        query = state["original_query"]
        context = state.get("context", "")
        search_results = state["search_results"]
        image_data = state.get("image_data")
        multimodal_content = state.get("multimodal_content", False)

        if not context and not multimodal_content:
            state["answer"] = (
                "I couldn't find relevant information to answer your question."
            )
            return state

        if multimodal_content and image_data:
            # Use multimodal analysis
            try:
                combined_context = f"Document context: {context}\n\nQuery: {query}"
                answer = self.openai_service.analyze_multimodal_content(
                    text=combined_context,
                    image_data=image_data,
                    prompt="Based on the provided document context and image, please answer the user's question. If the image contains relevant information, incorporate it into your response."
                )
                state["answer"] = answer
            except Exception as e:
                # Fallback to text-only analysis
                answer_prompt = ChatPromptTemplate.from_template(
                    """
                Answer the user's question based on the provided context. If the context doesn't contain enough information, say so.
                
                Context: {context}
                Question: {query}
                
                Provide a clear and helpful answer:
                """
                )
                chain = answer_prompt | self.llm
                result = chain.invoke({"query": query, "context": context})
                result_text = str(result.content) if hasattr(result, "content") else str(result)
                state["answer"] = result_text
        else:
            # Text-only analysis
            answer_prompt = ChatPromptTemplate.from_template(
                """
            Answer the user's question based on the provided context. If the context doesn't contain enough information, say so.
            
            Context: {context}
            Question: {query}
            
            Provide a clear and helpful answer:
            """
            )
            chain = answer_prompt | self.llm
            result = chain.invoke({"query": query, "context": context})
            result_text = str(result.content) if hasattr(result, "content") else str(result)
            state["answer"] = result_text

        state["sources"] = [chunk.document_id for chunk in search_results]

        return state

    def chat(self, query: str, session_id: Optional[str] = None, image_data: Optional[bytes] = None) -> Dict[str, Any]:
        """Chat with the document-based system with multimodal support"""
        # Always provide a thread_id for the checkpointer
        if not session_id:
            session_id = "default_session"

        config = {"configurable": {"thread_id": session_id}}

        # Initialize state
        state = ChatState(
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
        )
        
        # Run the graph
        result = self.graph.invoke(state, config)

        return {
            "answer": result["answer"],
            "sources": result["sources"],
            "search_count": result["search_count"],
            "context": result.get("context", ""),
            "multimodal_content": result.get("multimodal_content", False),
            "extracted_text": result.get("extracted_text"),
        }
