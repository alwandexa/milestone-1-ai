from typing import List, Dict, Any, TypedDict, Optional, Union, AsyncGenerator
from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.runnables import RunnableLambda
from src.domain.document import DocumentChunk
from src.infrastructure.openai_service import OpenAIService
from src.infrastructure.guardrails_service import GuardrailsService
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
    input_validation: Optional[Dict[str, Any]]  # Guardrails input validation
    response_validation: Optional[Dict[str, Any]]  # Guardrails response validation


class LangGraphChat:
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
        """Create the LangGraph workflow with multimodal support and guardrails"""

        # Define the state schema
        workflow = StateGraph(ChatState)

        # Add nodes with proper tracing
        workflow.add_node("validate_input", RunnableLambda(self._validate_input, name="validate_input"))
        workflow.add_node("process_multimodal_input", RunnableLambda(self._process_multimodal_input, name="process_multimodal_input"))
        workflow.add_node("search_documents", RunnableLambda(self._search_documents, name="search_documents"))
        workflow.add_node("evaluate_results", RunnableLambda(self._evaluate_results, name="evaluate_results"))
        workflow.add_node("generate_answer", RunnableLambda(self._generate_answer, name="generate_answer"))
        workflow.add_node("validate_response", RunnableLambda(self._validate_response, name="validate_response"))
        workflow.add_node("modify_query", RunnableLambda(self._modify_query, name="modify_query"))

        # Define edges
        workflow.add_edge("validate_input", "process_multimodal_input")
        workflow.add_edge("process_multimodal_input", "search_documents")
        workflow.add_edge("search_documents", "evaluate_results")
        workflow.add_conditional_edges(
            "evaluate_results",
            RunnableLambda(self._should_generate_answer, name="should_generate_answer"),
            {"generate_answer": "generate_answer", "modify_query": "modify_query"},
        )
        workflow.add_edge("modify_query", "search_documents")
        workflow.add_edge("generate_answer", "validate_response")
        workflow.add_edge("validate_response", END)

        # Set entry point
        workflow.set_entry_point("validate_input")

        # Return the compiled workflow, but type as Any to avoid mypy type error
        return workflow.compile(checkpointer=self.memory)  # type: ignore

    def _validate_input(self, state: ChatState) -> ChatState:
        """Validate user input using Guardrails AI"""
        query = state["query"]
        image_data = state.get("image_data")
        
        # Initialize chain of thought
        if "chain_of_thought" not in state:
            state["chain_of_thought"] = []
        
        # Add reasoning step with LangSmith tracing
        validation_step = {
            "step": "input_validation",
            "agent": "Guardrails Validator",
            "thought": f"Validating user input: '{query[:100]}...'",
            "status": "started",
            "metadata": {
                "node_name": "validate_input",
                "tracing_enabled": True
            }
        }
        state["chain_of_thought"].append(validation_step)
        
        try:
            if not self.enable_guardrails or not self.guardrails_service:
                # Skip validation if Guardrails is disabled
                state["input_validation"] = {
                    "validation_type": "input_validation",
                    "is_valid": True,
                    "confidence_score": 1.0,
                    "violation_count": 0,
                    "violations": [],
                    "has_correction": False,
                    "disabled": True
                }
                state["chain_of_thought"].append({
                    "step": "input_validation",
                    "agent": "Guardrails Validator",
                    "thought": "Input validation skipped (Guardrails disabled)",
                    "status": "skipped",
                    "metadata": {
                        "node_name": "validate_input",
                        "tracing_enabled": True,
                        "guardrails_disabled": True
                    }
                })
                return state
            
            if image_data:
                # Validate multimodal input
                validation_result = self.guardrails_service.validate_multimodal_input(
                    text=query,
                    image_description="Image uploaded by user"
                )
            else:
                # Validate text-only input
                validation_result = self.guardrails_service.validate_user_input(query)
            
            # Store validation result
            state["input_validation"] = self.guardrails_service.get_validation_summary(validation_result)
            
            # Update chain of thought
            state["chain_of_thought"].append({
                "step": "input_validation",
                "agent": "Guardrails Validator",
                "thought": f"Input validation {'passed' if validation_result.is_valid else 'failed'}",
                "status": "completed",
                "details": {
                    "is_valid": validation_result.is_valid,
                    "violation_count": len(validation_result.violations),
                    "confidence_score": validation_result.confidence_score
                }
            })
            
            # If input is invalid, modify the query to be safe
            if not validation_result.is_valid and validation_result.corrected_input:
                state["query"] = validation_result.corrected_input
                state["chain_of_thought"].append({
                    "step": "input_correction",
                    "agent": "Guardrails Validator",
                    "thought": "Applied input correction for safety",
                    "status": "completed"
                })
            
        except Exception as e:
            # If validation fails, continue with original input but log the error
            state["input_validation"] = {
                "validation_type": "input_validation",
                "is_valid": True,  # Default to valid to avoid blocking
                "confidence_score": 0.0,
                "violation_count": 0,
                "violations": [{"error": f"Validation service error: {str(e)}"}],
                "has_correction": False
            }
            
            state["chain_of_thought"].append({
                "step": "input_validation",
                "agent": "Guardrails Validator",
                "thought": f"Validation service error: {str(e)}",
                "status": "error"
            })
        
        return state

    def _validate_response(self, state: ChatState) -> ChatState:
        """Validate agent response using Guardrails AI"""
        answer = state.get("answer", "")
        original_query = state["original_query"]
        
        # Add reasoning step with LangSmith tracing
        validation_step = {
            "step": "response_validation",
            "agent": "Guardrails Validator",
            "thought": f"Validating agent response for safety and quality",
            "status": "started",
            "metadata": {
                "node_name": "validate_response",
                "tracing_enabled": True
            }
        }
        state["chain_of_thought"].append(validation_step)
        
        try:
            if not self.enable_guardrails or not self.guardrails_service:
                # Skip validation if Guardrails is disabled
                state["response_validation"] = {
                    "validation_type": "response_validation",
                    "is_valid": True,
                    "confidence_score": 1.0,
                    "violation_count": 0,
                    "violations": [],
                    "has_correction": False,
                    "disabled": True
                }
                state["chain_of_thought"].append({
                    "step": "response_validation",
                    "agent": "Guardrails Validator",
                    "thought": "Response validation skipped (Guardrails disabled)",
                    "status": "skipped",
                    "metadata": {
                        "node_name": "validate_response",
                        "tracing_enabled": True,
                        "guardrails_disabled": True
                    }
                })
                return state
            
            validation_result = self.guardrails_service.validate_agent_response(
                response=answer,
                original_query=original_query
            )
            
            # Store validation result
            state["response_validation"] = self.guardrails_service.get_validation_summary(validation_result)
            
            # Update chain of thought
            state["chain_of_thought"].append({
                "step": "response_validation",
                "agent": "Guardrails Validator",
                "thought": f"Response validation {'passed' if validation_result.is_valid else 'failed'}",
                "status": "completed",
                "details": {
                    "is_valid": validation_result.is_valid,
                    "violation_count": len(validation_result.violations),
                    "confidence_score": validation_result.confidence_score
                }
            })
            
            # If response is invalid, provide a safe fallback
            if not validation_result.is_valid:
                safe_response = (
                    "I apologize, but I cannot provide that information as it may violate safety guidelines. "
                    "Please try rephrasing your question or ask about a different topic."
                )
                state["answer"] = safe_response
                
                state["chain_of_thought"].append({
                    "step": "response_correction",
                    "agent": "Guardrails Validator",
                    "thought": "Applied response correction for safety",
                    "status": "completed"
                })
            
        except Exception as e:
            # If validation fails, keep original response but log the error
            state["response_validation"] = {
                "validation_type": "response_validation",
                "is_valid": True,  # Default to valid to avoid blocking
                "confidence_score": 0.0,
                "violation_count": 0,
                "violations": [{"error": f"Validation service error: {str(e)}"}],
                "has_correction": False
            }
            
            state["chain_of_thought"].append({
                "step": "response_validation",
                "agent": "Guardrails Validator",
                "thought": f"Validation service error: {str(e)}",
                "status": "error"
            })
        
        return state

    def _process_multimodal_input(self, state: ChatState) -> ChatState:
        """Process multimodal input (text + image)"""
        query = state["query"]
        image_data = state.get("image_data")
        
        # Initialize chain of thought
        if "chain_of_thought" not in state:
            state["chain_of_thought"] = []
        
        # Add reasoning step with LangSmith tracing
        processing_step = {
            "step": "multimodal_processing",
            "agent": "Input Processor",
            "thought": f"Processing user query: '{query}'",
            "status": "started",
            "metadata": {
                "node_name": "process_multimodal_input",
                "tracing_enabled": True
            }
        }
        state["chain_of_thought"].append(processing_step)
        
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

        # Add reasoning step with LangSmith tracing
        search_step = {
            "step": "document_search",
            "agent": "Document Retriever",
            "thought": f"Searching for documents relevant to: '{query[:100]}...'",
            "status": "started",
            "metadata": {
                "node_name": "search_documents",
                "tracing_enabled": True
            }
        }
        state["chain_of_thought"].append(search_step)

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

        # Add reasoning step with LangSmith tracing
        evaluation_step = {
            "step": "evaluate_results",
            "agent": "Result Evaluator",
            "thought": f"Evaluating {len(search_results)} search results for relevance",
            "status": "started",
            "metadata": {
                "node_name": "evaluate_results",
                "tracing_enabled": True
            }
        }
        state["chain_of_thought"].append(evaluation_step)

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

        # Add reasoning step with LangSmith tracing
        generation_step = {
            "step": "generate_answer",
            "agent": "Answer Generator",
            "thought": f"Generating answer for: '{query[:100]}...'",
            "status": "started",
            "metadata": {
                "node_name": "generate_answer",
                "tracing_enabled": True
            },
            "details": {
                "multimodal": multimodal_content,
                "has_context": bool(context),
                "search_results_count": len(search_results)
            }
        }
        state["chain_of_thought"].append(generation_step)

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
            "input_validation": result.get("input_validation"),
            "response_validation": result.get("response_validation"),
            "chain_of_thought": result.get("chain_of_thought", [])
        }

    async def chat_stream(self, query: str, session_id: Optional[str] = None, image_data: Optional[bytes] = None) -> AsyncGenerator[Dict[str, Any], None]:
        """Streaming chat with the document-based system with multimodal support using LangGraph workflow"""
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
        
        # Execute the LangGraph workflow for proper tracing
        try:
            # Use the LangGraph workflow for proper tracing
            final_state = self.graph.invoke(state, config)
            
            # Generate streaming answer based on the workflow results
            async for chunk in self._generate_streaming_answer(final_state):
                yield chunk
                
        except Exception as e:
            # Fallback to direct method calls if LangGraph fails
            print(f"LangGraph workflow failed, falling back to direct methods: {str(e)}")
            
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
