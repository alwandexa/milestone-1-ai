import openai
from typing import List, Dict, Optional
import os

class OpenAIService:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY environment variable.")
        
        self.client = openai.OpenAI(api_key=self.api_key)
    
    def get_embedding(self, text: str) -> List[float]:
        """Get embedding for text using text-embedding-3-small"""
        try:
            response = self.client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            raise Exception(f"Error getting embedding: {e}")
    
    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for multiple texts"""
        try:
            response = self.client.embeddings.create(
                model="text-embedding-3-small",
                input=texts
            )
            return [data.embedding for data in response.data]
        except Exception as e:
            raise Exception(f"Error getting embeddings: {e}")
    
    def get_chat_completion(self, messages: List[Dict[str, str]], max_tokens: int = 500) -> str:
        """Get chat completion using GPT-4.1 nano"""
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # GPT-4.1 nano equivalent
                messages=messages,  # type: ignore
                max_tokens=max_tokens,
                temperature=0.7
            )
            content = response.choices[0].message.content
            return content if content else "No response generated"
        except Exception as e:
            raise Exception(f"Error getting chat completion: {e}")
    
    def generate_faq_answer(self, question: str, context_faqs: List[Dict]) -> str:
        """Generate an answer for a question based on FAQ context"""
        context = "\n\n".join([f"Q: {faq['question']}\nA: {faq['answer']}" for faq in context_faqs])
        
        messages = [
            {
                "role": "system",
                "content": "You are a helpful FAQ assistant. Answer questions based on the provided FAQ context. If the question is not covered in the context, say 'I don't have information about that specific question.' Keep answers concise and helpful."
            },
            {
                "role": "user",
                "content": f"Context:\n{context}\n\nQuestion: {question}"
            }
        ]
        
        return self.get_chat_completion(messages) 