import os
from langsmith import Client
from langchain_core.tracers import LangChainTracer
# from langchain_core.callbacks import LangChainTracer

def setup_langsmith():
    """Setup LangSmith for tracing and monitoring"""
    
    # Get LangSmith credentials from environment
    langsmith_api_key = os.getenv("LANGSMITH_API_KEY")
    langsmith_project = os.getenv("LANGSMITH_PROJECT", "document-chatbot")
    langsmith_endpoint = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")
    
    if langsmith_api_key:
        # Set environment variables for LangSmith
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_ENDPOINT"] = langsmith_endpoint
        os.environ["LANGCHAIN_API_KEY"] = langsmith_api_key
        os.environ["LANGCHAIN_PROJECT"] = langsmith_project
        
        # Initialize LangSmith client
        try:
            client = Client(
                api_url=langsmith_endpoint,
                api_key=langsmith_api_key
            )
            
            # Test the connection
            client.list_projects()
            print(f"✅ LangSmith configured for project: {langsmith_project}")
            return client
        except Exception as e:
            print(f"⚠️  LangSmith connection failed: {e}")
            print("Please check your LANGSMITH_API_KEY and ensure you have access to LangSmith")
            return None
    else:
        print("⚠️  LangSmith API key not found. Set LANGSMITH_API_KEY environment variable for monitoring.")
        return None

def get_tracer():
    """Get LangChain tracer for tracing"""
    return LangChainTracer()

def log_chain_run(chain_name: str, inputs: dict, outputs: dict, metadata: dict = None):
    """Log a chain run to LangSmith using the correct API"""
    try:
        from langsmith import Client
        client = Client()
        
        # Create a run using the correct API
        run = client.create_run(
            run_type="chain",
            name=chain_name,
            inputs=inputs,
            outputs=outputs,
            metadata=metadata or {}
        )
        
        return run
    except Exception as e:
        print(f"Warning: Could not log to LangSmith: {e}")
        return None 