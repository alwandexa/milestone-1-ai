from typing import List, Dict, Any, TypedDict, Optional, Union, AsyncGenerator
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
import asyncio


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
    chain_of_thought: List[Dict[str, Any]]  # Track agent reasoning steps


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
        
        # Initialize streaming LLM
        self.streaming_llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.7,
            api_key=SecretStr(os.getenv("OPENAI_API_KEY", "")),
            callbacks=[self.tracer] if self.tracer else None,
            streaming=True,
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
        
        # Initialize chain of thought
        if "chain_of_thought" not in state:
            state["chain_of_thought"] = []
        
        # Add reasoning step
        state["chain_of_thought"].append({
            "step": "multimodal_processing",
            "agent": "Input Processor",
            "thought": f"Processing user query: '{query}'",
            "status": "started"
        })
        
        if image_data:
            # Extract text from image if present
            try:
                extracted_text = self.openai_service.extract_text_from_image(image_data)
                state["extracted_text"] = extracted_text
                
                # Combine original query with extracted text
                combined_query = f"{query}\n\nExtracted text from image: {extracted_text}"
                state["query"] = combined_query
                state["multimodal_content"] = True
                
                # Update chain of thought
                state["chain_of_thought"].append({
                    "step": "image_analysis",
                    "agent": "Image Analyzer",
                    "thought": f"Extracted text from image: {extracted_text[:100]}...",
                    "status": "completed"
                })
            except Exception as e:
                # If image processing fails, continue with original query
                state["multimodal_content"] = False
                state["extracted_text"] = None
                
                # Update chain of thought with error
                state["chain_of_thought"].append({
                    "step": "image_analysis",
                    "agent": "Image Analyzer",
                    "thought": f"Failed to extract text from image: {str(e)}",
                    "status": "error"
                })
        else:
            state["multimodal_content"] = False
            state["extracted_text"] = None
            
            # Update chain of thought
            state["chain_of_thought"].append({
                "step": "text_only",
                "agent": "Input Processor",
                "thought": "Processing text-only query",
                "status": "completed"
            })
        
        return state

    def _search_documents(self, state: ChatState) -> ChatState:
        """Search for relevant document chunks"""
        query = state["query"]

        # Add reasoning step
        state["chain_of_thought"].append({
            "step": "document_search",
            "agent": "Document Retriever",
            "thought": f"Searching for documents relevant to: '{query[:100]}...'",
            "status": "started"
        })

        # Get search results from document usecase
        if self.document_usecase:
            chunks = self.document_usecase.search_documents(query, top_k=5)
            
            # Update chain of thought with results
            state["chain_of_thought"].append({
                "step": "document_search",
                "agent": "Document Retriever",
                "thought": f"Found {len(chunks)} relevant document chunks",
                "status": "completed",
                "details": {
                    "chunks_found": len(chunks),
                    "search_query": query[:100]
                }
            })
        else:
            chunks = []  # Fallback if no document usecase
            
            # Update chain of thought with no results
            state["chain_of_thought"].append({
                "step": "document_search",
                "agent": "Document Retriever",
                "thought": "No document usecase available, using fallback",
                "status": "warning"
            })

        state["search_results"] = chunks
        state["search_count"] = state.get("search_count", 0) + 1

        return state

    def _evaluate_results(self, state: ChatState) -> ChatState:
        """Evaluate if search results contain the answer"""
        query = state["query"]
        search_results = state["search_results"]

        # Add reasoning step
        state["chain_of_thought"].append({
            "step": "evaluate_results",
            "agent": "Result Evaluator",
            "thought": f"Evaluating {len(search_results)} search results for relevance",
            "status": "started"
        })

        if not search_results:
            state["has_answer"] = False
            
            # Update chain of thought with no results
            state["chain_of_thought"].append({
                "step": "evaluate_results",
                "agent": "Result Evaluator",
                "thought": "No search results found, cannot answer the question",
                "status": "completed",
                "details": {
                    "has_answer": False,
                    "reason": "no_search_results"
                }
            })
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

        # Update chain of thought with evaluation result
        state["chain_of_thought"].append({
            "step": "evaluate_results",
            "agent": "Result Evaluator",
            "thought": f"Evaluation result: {'Sufficient information found' if state['has_answer'] else 'Insufficient information'}",
            "status": "completed",
            "details": {
                "has_answer": state["has_answer"],
                "evaluation_response": result_text,
                "context_length": len(context)
            }
        })

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

        # Add reasoning step
        state["chain_of_thought"].append({
            "step": "generate_answer",
            "agent": "Answer Generator",
            "thought": f"Generating answer for: '{query[:100]}...'",
            "status": "started",
            "details": {
                "multimodal": multimodal_content,
                "has_context": bool(context),
                "search_results_count": len(search_results)
            }
        })

        if not context and not multimodal_content:
            state["answer"] = (
                "I couldn't find relevant information to answer your question."
            )
            
            # Update chain of thought with no answer
            state["chain_of_thought"].append({
                "step": "generate_answer",
                "agent": "Answer Generator",
                "thought": "No context or multimodal content available, providing fallback response",
                "status": "completed",
                "details": {
                    "answer_generated": False,
                    "reason": "no_context_or_multimodal"
                }
            })
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
                
                # Update chain of thought with multimodal answer
                state["chain_of_thought"].append({
                    "step": "generate_answer",
                    "agent": "Answer Generator",
                    "thought": "Generated answer using multimodal analysis (text + image)",
                    "status": "completed",
                    "details": {
                        "method": "multimodal",
                        "answer_length": len(answer)
                    }
                })
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
                
                # Update chain of thought with fallback
                state["chain_of_thought"].append({
                    "step": "generate_answer",
                    "agent": "Answer Generator",
                    "thought": f"Multimodal analysis failed, using text-only fallback: {str(e)}",
                    "status": "completed",
                    "details": {
                        "method": "text_only_fallback",
                        "error": str(e),
                        "answer_length": len(result_text)
                    }
                })
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
            
            # Update chain of thought with text-only answer
            state["chain_of_thought"].append({
                "step": "generate_answer",
                "agent": "Answer Generator",
                "thought": "Generated answer using text-only analysis",
                "status": "completed",
                "details": {
                    "method": "text_only",
                    "answer_length": len(result_text)
                }
            })

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
            chain_of_thought=[],
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

    async def chat_stream(self, query: str, session_id: Optional[str] = None, image_data: Optional[bytes] = None) -> AsyncGenerator[Dict[str, Any], None]:
        """Streaming chat with the document-based system with multimodal support"""
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
            chain_of_thought=[],
        )
        
        # Process multimodal input first
        state = self._process_multimodal_input(state)
        
        # Search documents
        state = self._search_documents(state)
        
        # Evaluate results
        state = self._evaluate_results(state)
        
        # Generate streaming answer
        async for chunk in self._generate_streaming_answer(state):
            yield chunk

    async def _generate_streaming_answer(self, state: ChatState) -> AsyncGenerator[Dict[str, Any], None]:
        """Generate streaming answer based on context and multimodal content"""
        query = state["original_query"]
        context = state.get("context", "")
        search_results = state["search_results"]
        image_data = state.get("image_data")
        multimodal_content = state.get("multimodal_content", False)

        if not context and not multimodal_content:
            yield {
                "type": "content",
                "content": "I couldn't find relevant information to answer your question."
            }
            return

        # Send initial metadata with chain of thought
        yield {
            "type": "metadata",
            "sources": [chunk.document_id for chunk in search_results],
            "search_count": state.get("search_count", 0),
            "multimodal_content": multimodal_content,
            "extracted_text": state.get("extracted_text"),
            "chain_of_thought": state.get("chain_of_thought", [])
        }

        if multimodal_content and image_data:
            # Use multimodal analysis with streaming
            try:
                combined_context = f"Document context: {context}\n\nQuery: {query}"
                async for chunk in self._stream_multimodal_analysis(
                    text=combined_context,
                    image_data=image_data,
                    prompt="Based on the provided document context and image, please answer the user's question. If the image contains relevant information, incorporate it into your response."
                ):
                    yield chunk
            except Exception as e:
                # Fallback to text-only streaming analysis
                async for chunk in self._stream_text_analysis(query, context):
                    yield chunk
        else:
            # Text-only streaming analysis
            async for chunk in self._stream_text_analysis(query, context):
                yield chunk

    async def _stream_text_analysis(self, query: str, context: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream text-only analysis"""
        answer_prompt = ChatPromptTemplate.from_template(
            """
        Answer the user's question based on the provided context. If the context doesn't contain enough information, say so.
        
        Context: {context}
        Question: {query}
        
        Provide a clear and helpful answer:
        """
        )
        
        chain = answer_prompt | self.streaming_llm
        
        try:
            async for chunk in chain.astream({"query": query, "context": context}):
                if hasattr(chunk, 'content') and chunk.content:
                    yield {
                        "type": "content",
                        "content": chunk.content
                    }
        except Exception as e:
            yield {
                "type": "error",
                "content": f"Error generating response: {str(e)}"
            }

    async def _stream_multimodal_analysis(self, text: str, image_data: bytes, prompt: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream multimodal analysis"""
        try:
            # Convert image to base64
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            # Create multimodal message
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"{prompt}\n\nText content: {text}"
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ]
            
            # Stream the response
            async for chunk in self.streaming_llm.astream(messages):
                if hasattr(chunk, 'content') and chunk.content:
                    yield {
                        "type": "content",
                        "content": chunk.content
                    }
        except Exception as e:
            yield {
                "type": "error",
                "content": f"Error in multimodal analysis: {str(e)}"
            }
