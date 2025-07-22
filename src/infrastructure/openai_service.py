import openai
from typing import List, Dict, Optional, Union
import os
import base64
from PIL import Image
import io

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
        """Get chat completion using GPT-4o-mini"""
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,  # type: ignore
                max_tokens=max_tokens,
                temperature=0.7
            )
            content = response.choices[0].message.content
            return content if content else "No response generated"
        except Exception as e:
            raise Exception(f"Error getting chat completion: {e}")
    
    def analyze_image(self, image_data: bytes, prompt: str) -> str:
        """Analyze image using GPT-4o-mini multimodal capabilities"""
        try:
            # Convert image to base64
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=1000,
                temperature=0.7
            )
            
            content = response.choices[0].message.content
            return content if content else "No analysis generated"
        except Exception as e:
            raise Exception(f"Error analyzing image: {e}")
    
    def analyze_multimodal_content(self, text: str, image_data: Optional[bytes] = None, prompt: str = "") -> str:
        """Analyze combined text and image content"""
        try:
            messages = []
            
            if image_data:
                # Convert image to base64
                image_base64 = base64.b64encode(image_data).decode('utf-8')
                
                # Create multimodal message
                content = []
                if prompt:
                    content.append({
                        "type": "text",
                        "text": f"{prompt}\n\nText content: {text}"
                    })
                else:
                    content.append({
                        "type": "text",
                        "text": f"Please analyze the following text and image content:\n\nText: {text}"
                    })
                
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{image_base64}"
                    }
                })
                
                messages.append({
                    "role": "user",
                    "content": content
                })
            else:
                # Text-only analysis
                messages.append({
                    "role": "user",
                    "content": f"{prompt}\n\n{text}" if prompt else text
                })
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=1000,
                temperature=0.7
            )
            
            content = response.choices[0].message.content
            return content if content else "No analysis generated"
        except Exception as e:
            raise Exception(f"Error analyzing multimodal content: {e}")
    
    def extract_text_from_image(self, image_data: bytes) -> str:
        """Extract text from image using OCR capabilities"""
        try:
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Please extract all text from this image. Return only the extracted text without any additional commentary."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=500,
                temperature=0.1
            )
            
            content = response.choices[0].message.content
            return content if content else "No text extracted"
        except Exception as e:
            raise Exception(f"Error extracting text from image: {e}")
    
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