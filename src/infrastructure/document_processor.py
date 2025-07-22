import PyPDF2
import io
from typing import List
import uuid
from datetime import datetime
from src.domain.document import Document, DocumentChunk

class DocumentProcessor:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def process_pdf(self, file_content: bytes, filename: str) -> Document:
        """Process PDF file and create document with chunks"""
        # Extract text from PDF
        text = self._extract_text_from_pdf(file_content)
        
        # Create chunks
        chunks = self._create_chunks(text, filename)
        
        # Create document
        document = Document(
            id=str(uuid.uuid4()),
            filename=filename,
            content=text,
            chunks=chunks,
            uploaded_at=datetime.now()
        )
        
        return document

    def _extract_text_from_pdf(self, file_content: bytes) -> str:
        """Extract text from PDF bytes"""
        try:
            pdf_file = io.BytesIO(file_content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            
            return text.strip()
        except Exception as e:
            raise Exception(f"Error extracting text from PDF: {e}")

    def _create_chunks(self, text: str, document_id: str) -> List[DocumentChunk]:
        """Create chunks based on Q&A pairs"""
        chunks = []
        
        # First, try to split by numbered questions if the text contains them
        qa_pairs = self._extract_qa_pairs_from_text(text)
        
        if qa_pairs:
            # Create chunks from extracted Q&A pairs
            for qa_index, (question, answer) in enumerate(qa_pairs):
                chunk_content = f"{question}\n{answer}"
                chunk = DocumentChunk(
                    id=str(uuid.uuid4()),
                    document_id=document_id,
                    content=chunk_content,
                    metadata={
                        "qa_index": qa_index,
                        "question": question,
                        "answer": answer,
                        "chunk_type": "qa_pair"
                    }
                )
                chunks.append(chunk)
        else:
            # Fall back to line-by-line processing
            chunks = self._create_chunks_line_by_line(text, document_id)
        
        # If still no chunks, fall back to original chunking strategy
        if not chunks:
            return self._create_fallback_chunks(text, document_id)
        
        return chunks
    
    def _extract_qa_pairs_from_text(self, text: str) -> List[tuple]:
        """Extract Q&A pairs from text that may contain multiple pairs on one line"""
        import re
        
        qa_pairs = []
        
        # Pattern to match numbered questions followed by answers
        # This matches patterns like "19. Question? Answer. 20. Question? Answer."
        # The pattern looks for: number + dot + question text ending with ? + answer text until next number
        pattern = r'(\d+\.\s*[^?]+\?)\s*([^0-9]+?)(?=\d+\.|$)'
        
        matches = re.findall(pattern, text, re.DOTALL)
        
        for question, answer in matches:
            question = question.strip()
            answer = answer.strip()
            if question and answer:
                qa_pairs.append((question, answer))
        
        # If regex didn't find all expected Q&A pairs, try the fallback approach
        # Count the number of numbered questions in the text
        numbered_questions = re.findall(r'\d+\.', text)
        if len(qa_pairs) < len(numbered_questions):
            # Use the fallback approach instead of the regex approach
            qa_pairs = []  # Clear the regex results
            # Split by numbered patterns and try to extract Q&A pairs
            numbered_sections = re.split(r'(\d+\.)', text)
            
            for i in range(1, len(numbered_sections) - 1, 2):
                if i + 1 < len(numbered_sections):
                    number = numbered_sections[i]
                    content = numbered_sections[i + 1]
                    
                    # Try to find the question and answer in the content
                    # Look for the first question mark to separate question from answer
                    qa_split = content.split('?', 1)
                    if len(qa_split) == 2:
                        question = number + qa_split[0] + '?'
                        answer = qa_split[1].strip()
                        if question and answer:
                            qa_pairs.append((question, answer))
        
        return qa_pairs
    
    def _create_chunks_line_by_line(self, text: str, document_id: str) -> List[DocumentChunk]:
        """Create chunks using line-by-line processing"""
        chunks = []
        
        # Split text into lines and process Q&A pairs
        lines = text.split('\n')
        current_qa = {"question": "", "answer": ""}
        qa_index = 0
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check if line starts with a question pattern
            if self._is_question_line(line):
                # Save previous Q&A if exists
                if current_qa["question"] and current_qa["answer"]:
                    chunk_content = f"{current_qa['question']}\n{current_qa['answer']}"
                    chunk = DocumentChunk(
                        id=str(uuid.uuid4()),
                        document_id=document_id,
                        content=chunk_content,
                        metadata={
                            "qa_index": qa_index,
                            "question": current_qa["question"],
                            "answer": current_qa["answer"],
                            "chunk_type": "qa_pair"
                        }
                    )
                    chunks.append(chunk)
                    qa_index += 1
                
                # Start new Q&A pair
                current_qa = {"question": line, "answer": ""}
            else:
                # This line is part of the answer
                if current_qa["question"]:
                    if current_qa["answer"]:
                        current_qa["answer"] += " " + line
                    else:
                        current_qa["answer"] = line
        
        # Don't forget the last Q&A pair
        if current_qa["question"] and current_qa["answer"]:
            chunk_content = f"{current_qa['question']}\n{current_qa['answer']}"
            chunk = DocumentChunk(
                id=str(uuid.uuid4()),
                document_id=document_id,
                content=chunk_content,
                metadata={
                    "qa_index": qa_index,
                    "question": current_qa["question"],
                    "answer": current_qa["answer"],
                    "chunk_type": "qa_pair"
                }
            )
            chunks.append(chunk)
        
        return chunks
    
    def _is_question_line(self, line: str) -> bool:
        """Check if a line starts with a question pattern"""
        import re
        
        # Remove leading/trailing whitespace
        line = line.strip()
        if not line:
            return False
        
        # Check for explicit question patterns
        question_patterns = [
            "Q:", "Q.", "Q ", "Question:", "Question.", "Question ",
            "P:", "P.", "P ", "Pertanyaan:", "Pertanyaan.", "Pertanyaan "
        ]
        
        line_upper = line.upper()
        if any(line_upper.startswith(pattern) for pattern in question_patterns):
            return True
        
        # Check for numbered questions (1., 2., 3., etc.)
        # This regex matches patterns like "19.", "20.", "21.", etc.
        numbered_pattern = re.match(r'^\d+\.\s*', line)
        if numbered_pattern:
            return True
        
        # Check for questions that start with common question words
        question_words = [
            "APA", "SIAPA", "BAGAIMANA", "KAPAN", "DIMANA", "KENAPA", "MENGAPA",
            "WHAT", "WHO", "HOW", "WHEN", "WHERE", "WHY", "WHICH"
        ]
        
        # Get the first few words of the line
        first_words = line_upper.split()[:3]  # Check first 3 words
        for word in first_words:
            if word in question_words:
                return True
        
        return False
    
    def _create_fallback_chunks(self, text: str, document_id: str) -> List[DocumentChunk]:
        """Fallback to original chunking strategy if no Q&A pairs found"""
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            
            # If this is not the last chunk, try to break at a sentence boundary
            if end < len(text):
                # Look for sentence endings
                for i in range(end, max(start + self.chunk_size - 100, start), -1):
                    if text[i] in '.!?':
                        end = i + 1
                        break
            
            chunk_text = text[start:end].strip()
            
            if chunk_text:
                chunk = DocumentChunk(
                    id=str(uuid.uuid4()),
                    document_id=document_id,
                    content=chunk_text,
                    metadata={
                        "start_pos": start,
                        "end_pos": end,
                        "chunk_index": len(chunks),
                        "chunk_type": "fallback"
                    }
                )
                chunks.append(chunk)
            
            # Move start position with overlap
            start = end - self.chunk_overlap
            if start >= len(text):
                break
        
        return chunks 