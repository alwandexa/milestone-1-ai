import PyPDF2
import io
import fitz  # PyMuPDF for better image extraction
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime
from src.domain.document import Document, DocumentChunk, ProductGroup
from src.infrastructure.openai_service import OpenAIService
import re

class DocumentProcessor:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200, openai_service: Optional[OpenAIService] = None):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.openai_service = openai_service

    def process_pdf(self, file_content: bytes, filename: str, product_group: Optional[ProductGroup] = None) -> Document:
        """Process PDF file and create document with chunks"""
        # Extract text and images from PDF
        text_content = self._extract_content_from_pdf(file_content)
        
        # Create chunks with better strategy
        chunks = self._create_smart_chunks(text_content, filename, product_group)
        
        # Create document
        document = Document(
            id=str(uuid.uuid4()),
            filename=filename,
            content=text_content,
            chunks=chunks,
            uploaded_at=datetime.now(),
            product_group=product_group
        )
        
        return document

    def _extract_content_from_pdf(self, file_content: bytes) -> str:
        """Extract text and image content from PDF bytes"""
        try:
            # Use PyMuPDF for better image extraction
            pdf_document = fitz.open(stream=file_content, filetype="pdf")
            full_text = ""
            
            for page_num in range(len(pdf_document)):
                page = pdf_document[page_num]
                
                # Extract text from the page
                page_text = page.get_text()
                if page_text.strip():
                    full_text += f"\n--- Page {page_num + 1} ---\n{page_text}\n"
                
                # Extract images from the page
                image_list = page.get_images()
                for img_index, img in enumerate(image_list):
                    try:
                        # Get image data
                        xref = img[0]
                        pix = fitz.Pixmap(pdf_document, xref)
                        
                        if pix.n - pix.alpha < 4:  # GRAY or RGB
                            img_data = pix.tobytes("png")
                            
                            # Use OpenAI to extract text from image if service is available
                            if self.openai_service:
                                try:
                                    print(f"Extracting text from image {img_index + 1} on page {page_num + 1}...")
                                    image_text = self.openai_service.extract_text_from_image(img_data)
                                    if image_text.strip():
                                        full_text += f"\n--- Image {img_index + 1} on page {page_num + 1} ---\n{image_text}\n"
                                        print(f"✓ Successfully extracted text from image {img_index + 1} on page {page_num + 1}")
                                    else:
                                        full_text += f"\n--- Image {img_index + 1} on page {page_num + 1} (no text found) ---\n"
                                        print(f"⚠ No text found in image {img_index + 1} on page {page_num + 1}")
                                except Exception as e:
                                    print(f"✗ Error extracting text from image {img_index + 1} on page {page_num + 1}: {e}")
                                    full_text += f"\n--- Image {img_index + 1} on page {page_num + 1} (extraction failed: {str(e)}) ---\n"
                            else:
                                print(f"⚠ OpenAI service not available for image {img_index + 1} on page {page_num + 1}")
                                full_text += f"\n--- Image {img_index + 1} on page {page_num + 1} (text extraction not available) ---\n"
                        else:
                            print(f"⚠ Skipping image {img_index + 1} on page {page_num + 1} (unsupported format)")
                        
                        pix = None  # Free memory
                        
                    except Exception as e:
                        print(f"✗ Error processing image {img_index} on page {page_num + 1}: {e}")
                        continue
            
            pdf_document.close()
            return full_text.strip()
            
        except Exception as e:
            # Fallback to PyPDF2 if PyMuPDF fails
            try:
                pdf_file = io.BytesIO(file_content)
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                
                return text.strip()
            except Exception as fallback_e:
                raise Exception(f"Error extracting content from PDF: {e}. Fallback also failed: {fallback_e}")

    def _create_smart_chunks(self, text: str, document_id: str, product_group: Optional[ProductGroup] = None) -> List[DocumentChunk]:
        """Create chunks using smart sentence-aware chunking"""
        chunks = []
        
        # Clean and normalize text
        text = self._normalize_text(text)
        
        # Split into sentences first
        sentences = self._split_into_sentences(text)
        
        # Group sentences into chunks
        current_chunk = []
        current_length = 0
        
        for sentence in sentences:
            sentence_length = len(sentence)
            
            # If adding this sentence would exceed chunk size and we already have content
            if current_length + sentence_length > self.chunk_size and current_chunk:
                # Create chunk from current sentences
                chunk_content = " ".join(current_chunk)
                chunk = self._create_chunk(chunk_content, document_id, product_group, len(chunks))
                chunks.append(chunk)
                
                # Start new chunk with overlap
                overlap_sentences = self._get_overlap_sentences(current_chunk)
                current_chunk = overlap_sentences
                current_length = sum(len(s) for s in overlap_sentences)
            
            # Add sentence to current chunk
            current_chunk.append(sentence)
            current_length += sentence_length
        
        # Don't forget the last chunk
        if current_chunk:
            chunk_content = " ".join(current_chunk)
            chunk = self._create_chunk(chunk_content, document_id, product_group, len(chunks))
            chunks.append(chunk)
        
        return chunks

    def _normalize_text(self, text: str) -> str:
        """Normalize text by removing extra whitespace and normalizing line breaks"""
        # Replace multiple whitespace with single space
        text = re.sub(r'\s+', ' ', text)
        # Remove extra line breaks but keep paragraph breaks
        text = re.sub(r'\n\s*\n', '\n\n', text)
        # Normalize sentence endings
        text = re.sub(r'([.!?])\s*([A-Z])', r'\1 \2', text)
        return text.strip()

    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences using intelligent sentence boundary detection"""
        # Common abbreviations that shouldn't end sentences
        abbreviations = [
            'Dr.', 'Mr.', 'Mrs.', 'Ms.', 'Prof.', 'Sr.', 'Jr.', 'Inc.', 'Ltd.', 'Co.',
            'vs.', 'etc.', 'i.e.', 'e.g.', 'U.S.', 'U.K.', 'Ph.D.', 'M.D.', 'B.A.', 'M.A.',
            'A.M.', 'P.M.', 'a.m.', 'p.m.', 'No.', 'no.', 'Vol.', 'vol.', 'Fig.', 'fig.',
            'Jan.', 'Feb.', 'Mar.', 'Apr.', 'Jun.', 'Jul.', 'Aug.', 'Sep.', 'Sept.', 'Oct.', 'Nov.', 'Dec.'
        ]
        
        # First, temporarily replace abbreviations to prevent false splits
        temp_text = text
        abbr_map = {}
        
        for i, abbr in enumerate(abbreviations):
            # Create a unique placeholder
            placeholder = f"__ABBR_{i}__"
            temp_text = temp_text.replace(abbr, placeholder)
            abbr_map[placeholder] = abbr
        
        # Split by sentence boundaries
        sentence_pattern = r'(?<=[.!?])\s+(?=[A-Z])'
        sentences = re.split(sentence_pattern, temp_text)
        
        # Restore abbreviations and clean up sentences
        cleaned_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence and len(sentence) > 10:  # Filter out very short fragments
                # Restore abbreviations
                for placeholder, abbr in abbr_map.items():
                    sentence = sentence.replace(placeholder, abbr)
                cleaned_sentences.append(sentence)
        
        return cleaned_sentences

    def _get_overlap_sentences(self, sentences: List[str]) -> List[str]:
        """Get the last few sentences for overlap"""
        overlap_size = min(len(sentences), max(1, len(sentences) // 3))
        return sentences[-overlap_size:]

    def _create_chunk(self, content: str, document_id: str, product_group: Optional[ProductGroup] = None, chunk_index: int = 0) -> DocumentChunk:
        """Create a document chunk with minimal metadata"""
        return DocumentChunk(
            id=str(uuid.uuid4()),
            document_id=document_id,
            content=content,
            metadata={
                "chunk_index": chunk_index,
                "chunk_type": "text",
                "product_group": product_group.value if product_group else None
            },
            product_group=product_group
        )

    def _create_fallback_chunks(self, text: str, document_id: str, product_group: Optional[ProductGroup] = None) -> List[DocumentChunk]:
        """Fallback chunking strategy if smart chunking fails"""
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            
            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence endings within the last 200 characters
                for i in range(end, max(start + self.chunk_size - 200, start), -1):
                    if text[i] in '.!?':
                        end = i + 1
                        break
            
            chunk_text = text[start:end].strip()
            
            if chunk_text:
                chunk = self._create_chunk(chunk_text, document_id, product_group, len(chunks))
                chunks.append(chunk)
            
            # Move start position with overlap
            start = end - self.chunk_overlap
            if start >= len(text):
                break
        
        return chunks 