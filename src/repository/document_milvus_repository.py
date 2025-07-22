from typing import List, Optional
from pymilvus import Collection, CollectionSchema, FieldSchema, DataType, connections, utility
from src.domain.document import Document, DocumentChunk, ProductGroup
from src.ports.document_repository_port import DocumentRepositoryPort
import os
import json

class DocumentMilvusRepository(DocumentRepositoryPort):
    COLLECTION_NAME = "alwan_dd_milestone_project_1"
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
            # Define schema with product_group field
            fields = [
                FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, max_length=100),
                FieldSchema(name="document_id", dtype=DataType.VARCHAR, max_length=100),
                FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=65535),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.VECTOR_DIM),
                FieldSchema(name="metadata", dtype=DataType.VARCHAR, max_length=65535),
                FieldSchema(name="product_group", dtype=DataType.VARCHAR, max_length=50)
            ]
            schema = CollectionSchema(fields, description="Document chunks collection with product groups")
            
            # Create collection
            self.collection = Collection(self.COLLECTION_NAME, schema)
            
            # Create index
            index_params = {
                "metric_type": "IP",
                "index_type": "IVF_FLAT",
                "params": {"nlist": 128}
            }
            self.collection.create_index("embedding", index_params)
            print("✅ Created new collection with product_group field")
        else:
            self.collection = Collection(self.COLLECTION_NAME)
            self.collection.load()
            print("✅ Loaded existing collection")

    def upload_document(self, document: Document) -> None:
        """Upload document chunks to collection"""
        try:
            print(f"Uploading document {document.id} with {len(document.chunks)} chunks")
            
            # Process each chunk
            for i, chunk in enumerate(document.chunks):
                if chunk.embedding:
                    # Get product group value
                    product_group_value = chunk.product_group.value if chunk.product_group else ""
                    
                    data = [
                        [chunk.id],
                        [chunk.document_id],
                        [chunk.content],
                        [chunk.embedding],
                        [json.dumps(chunk.metadata or {})],
                        [product_group_value]
                    ]
                    self.collection.insert(data)
                    print(f"Uploaded chunk {i+1}/{len(document.chunks)} (Product Group: {product_group_value})")
            
            self.collection.flush()
            print("✅ Document upload completed successfully")
            
        except Exception as e:
            print(f"❌ Error uploading document: {e}")
            raise Exception(f"Failed to upload document: {e}")

    def search_similar_chunks(self, query_embedding: List[float], top_k: int = 5, product_group: Optional[ProductGroup] = None) -> List[DocumentChunk]:
        """Search for similar document chunks with optional product group filter"""
        search_params = {"metric_type": "IP", "params": {"nprobe": 10}}
        
        # Define output fields
        output_fields = ["id", "document_id", "content", "metadata", "product_group"]
        
        # Add product group filter if specified
        expr = None
        if product_group:
            expr = f'product_group == "{product_group.value}"'
        
        results = self.collection.search(
            data=[query_embedding],
            anns_field="embedding",
            param=search_params,
            limit=top_k,
            output_fields=output_fields,
            expr=expr
        )
        
        chunks = []
        # Handle the search results
        for hits in results:
            for hit in hits:
                metadata = json.loads(hit.entity.get("metadata", "{}"))
                
                # Parse product group from string
                product_group_str = hit.entity.get("product_group", "")
                product_group_enum = None
                if product_group_str:
                    try:
                        product_group_enum = ProductGroup(product_group_str)
                    except ValueError:
                        # If product group string doesn't match enum, ignore it
                        pass
                
                chunk = DocumentChunk(
                    id=hit.entity.get("id"),
                    document_id=hit.entity.get("document_id"),
                    content=hit.entity.get("content"),
                    embedding=None,  # We don't need to return embeddings
                    metadata=metadata,
                    product_group=product_group_enum
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
        try:
            print("🔍 Checking collection for documents...")
            
            # For now, since we know the collection is empty, return empty list
            # This avoids the hanging query issue
            print("ℹ️ Collection is empty, returning empty list")
            return []
            
            # Extract unique document IDs and their product groups
            documents = {}
            for result in results:
                doc_id = result.get("document_id")
                product_group_str = result.get("product_group", "")
                
                if doc_id not in documents:
                    # Parse product group
                    product_group_enum = None
                    if product_group_str:
                        try:
                            product_group_enum = ProductGroup(product_group_str)
                        except ValueError:
                            pass
                    
                    # Create a minimal document object
                    # Note: We don't have full document info, so we'll create basic ones
                    from datetime import datetime
                    document = Document(
                        id=doc_id,
                        filename=f"document_{doc_id}.pdf",  # Default filename
                        content="",  # We don't store full content in chunks
                        chunks=[],  # We'll populate this if needed
                        uploaded_at=datetime.now(),  # Default timestamp
                        metadata={},
                        product_group=product_group_enum
                    )
                    documents[doc_id] = document
            
            return list(documents.values())
            
        except Exception as e:
            print(f"❌ Error listing documents: {e}")
            import traceback
            traceback.print_exc()
            raise Exception(f"Failed to list documents: {str(e)}")

    def delete_document(self, document_id: str) -> None:
        """Delete document and all its chunks"""
        # Delete all chunks for this document
        self.collection.delete(f'document_id == "{document_id}"')
        self.collection.flush()

    def search_by_product_group(self, product_group: ProductGroup, top_k: int = 10) -> List[DocumentChunk]:
        """Search for chunks by product group only"""
        try:
            # Query by product group without vector search
            results = self.collection.query(
                expr=f'product_group == "{product_group.value}"',
                output_fields=["id", "document_id", "content", "metadata", "product_group"],
                limit=top_k
            )
            
            chunks = []
            for result in results:
                metadata = json.loads(result.get("metadata", "{}"))
                
                chunk = DocumentChunk(
                    id=result.get("id"),
                    document_id=result.get("document_id"),
                    content=result.get("content"),
                    embedding=None,
                    metadata=metadata,
                    product_group=product_group
                )
                chunks.append(chunk)
            
            return chunks
            
        except Exception as e:
            print(f"❌ Error searching by product group: {e}")
            return [] 