from typing import List, Optional
from pymilvus import Collection, CollectionSchema, FieldSchema, DataType, connections, utility
from src.domain.document import Document, DocumentChunk
from src.ports.document_repository_port import DocumentRepositoryPort
import os
import json

class DocumentMilvusRepository(DocumentRepositoryPort):
    COLLECTION_NAME = "alwan_dd_mini_project_1"
    VECTOR_DIM = 1536  # OpenAI text-embedding-3-small dimension

    def __init__(self):
        # Connection details should be set via env variables
        host = os.getenv("MILVUS_HOST", "localhost")
        port = os.getenv("MILVUS_PORT", "19530")
        db_name = os.getenv("MILVUS_DB_NAME", "default")
        
        print(f"Connecting to Milvus at {host}:{port}")
        
        try:
            connections.connect(host=host, port=port, db_name=db_name)
            print("✅ Successfully connected to Milvus")
            self._ensure_collection()
        except Exception as e:
            print(f"❌ Failed to connect to Milvus: {e}")
            raise Exception(f"Failed to connect to Milvus at {host}:{port}: {e}")

    def _ensure_collection(self):
        """Ensure the collection exists, create if it doesn't"""
        if self.COLLECTION_NAME not in utility.list_collections():
            # Define schema
            fields = [
                FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, max_length=100),
                FieldSchema(name="document_id", dtype=DataType.VARCHAR, max_length=100),
                FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=65535),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.VECTOR_DIM),
                FieldSchema(name="metadata", dtype=DataType.VARCHAR, max_length=65535)
            ]
            schema = CollectionSchema(fields, description="Document chunks collection")
            
            # Create collection
            self.collection = Collection(self.COLLECTION_NAME, schema)
            
            # Create index
            index_params = {
                "metric_type": "IP",
                "index_type": "IVF_FLAT",
                "params": {"nlist": 128}
            }
            self.collection.create_index("embedding", index_params)
        else:
            self.collection = Collection(self.COLLECTION_NAME)
            self.collection.load()

    def upload_document(self, document: Document) -> None:
        """Upload document chunks to collection"""
        try:
            print(f"Uploading document {document.id} with {len(document.chunks)} chunks")
            
            # Process each chunk
            for i, chunk in enumerate(document.chunks):
                if chunk.embedding:
                    data = [
                        [chunk.id],
                        [chunk.document_id],
                        [chunk.content],
                        [chunk.embedding],
                        [json.dumps(chunk.metadata or {})]
                    ]
                    self.collection.insert(data)
                    print(f"Uploaded chunk {i+1}/{len(document.chunks)}")
            
            self.collection.flush()
            print("✅ Document upload completed successfully")
            
        except Exception as e:
            print(f"❌ Error uploading document: {e}")
            raise Exception(f"Failed to upload document: {e}")

    def search_similar_chunks(self, query_embedding: List[float], top_k: int = 5) -> List[DocumentChunk]:
        """Search for similar document chunks"""
        search_params = {"metric_type": "IP", "params": {"nprobe": 10}}
        results = self.collection.search(
            data=[query_embedding],
            anns_field="embedding",
            param=search_params,
            limit=top_k,
            output_fields=["id", "document_id", "content", "metadata"]
        )
        
        chunks = []
        # Handle the search results
        for hits in results:
            for hit in hits:
                metadata = json.loads(hit.entity.get("metadata", "{}"))
                chunk = DocumentChunk(
                    id=hit.entity.get("id"),
                    document_id=hit.entity.get("document_id"),
                    content=hit.entity.get("content"),
                    embedding=None,  # We don't need to return embeddings
                    metadata=metadata
                )
                chunks.append(chunk)
        
        return chunks

    def get_document_by_id(self, document_id: str) -> Optional[Document]:
        """Get document by ID (this would need a separate collection for documents)"""
        # For now, return None as we're focusing on chunks
        # In a full implementation, you'd have a separate documents collection
        return None

    def list_documents(self) -> List[Document]:
        """List all documents by extracting unique document IDs from chunks"""
        # For now, return empty list to avoid errors
        # TODO: Implement proper document listing when Milvus collection is set up
        return []

    def delete_document(self, document_id: str) -> None:
        """Delete document and all its chunks"""
        # Delete all chunks for this document
        self.collection.delete(f'document_id == "{document_id}"')
        self.collection.flush() 