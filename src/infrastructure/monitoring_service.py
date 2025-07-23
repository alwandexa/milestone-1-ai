import sqlite3
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
import uuid
import logging

logger = logging.getLogger(__name__)

class QuestionType(Enum):
    """Types of questions users ask"""
    PRODUCT_INFO = "product_info"
    TECHNICAL_SPECS = "technical_specs"
    USAGE_INSTRUCTIONS = "usage_instructions"
    TROUBLESHOOTING = "troubleshooting"
    COMPARISON = "comparison"
    PRICING = "pricing"
    AVAILABILITY = "availability"
    SAFETY = "safety"
    MAINTENANCE = "maintenance"
    GENERAL = "general"

class AgentStatus(Enum):
    """Agent execution status"""
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"

@dataclass
class MonitoringEvent:
    """Base monitoring event"""
    event_id: str
    timestamp: datetime
    session_id: Optional[str]
    user_id: Optional[str]
    event_type: str
    metadata: Dict[str, Any]

@dataclass
class ChatEvent(MonitoringEvent):
    """Chat interaction event"""
    query: str
    response: str
    question_type: QuestionType
    product_group: Optional[str]
    response_time_ms: int
    token_count: int
    confidence_score: float
    agent_status: AgentStatus
    sources_count: int
    chain_of_thought: Optional[List[Dict[str, Any]]]
    input_validation: Optional[Dict[str, Any]]
    response_validation: Optional[Dict[str, Any]]
    multimodal: bool
    extracted_text: Optional[str]

@dataclass
class DocumentEvent(MonitoringEvent):
    """Document upload/processing event"""
    filename: str
    file_size: int
    chunk_count: int
    product_group: Optional[str]
    processing_time_ms: int

@dataclass
class SystemEvent(MonitoringEvent):
    """System-level events"""
    component: str
    operation: str
    status: str
    error_message: Optional[str]

class MonitoringService:
    """Service for monitoring and analytics"""
    
    def __init__(self, db_path: str = "monitoring.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize the monitoring database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chat_events (
                    event_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    session_id TEXT,
                    user_id TEXT,
                    query TEXT NOT NULL,
                    response TEXT NOT NULL,
                    question_type TEXT NOT NULL,
                    product_group TEXT,
                    response_time_ms INTEGER NOT NULL,
                    token_count INTEGER NOT NULL,
                    confidence_score REAL NOT NULL,
                    agent_status TEXT NOT NULL,
                    sources_count INTEGER NOT NULL,
                    chain_of_thought TEXT,
                    input_validation TEXT,
                    response_validation TEXT,
                    multimodal BOOLEAN NOT NULL,
                    extracted_text TEXT,
                    metadata TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS document_events (
                    event_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    session_id TEXT,
                    user_id TEXT,
                    filename TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    chunk_count INTEGER NOT NULL,
                    product_group TEXT,
                    processing_time_ms INTEGER NOT NULL,
                    metadata TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS system_events (
                    event_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    session_id TEXT,
                    user_id TEXT,
                    component TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    status TEXT NOT NULL,
                    error_message TEXT,
                    metadata TEXT
                )
            """)
            
            # Create indexes for better performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_timestamp ON chat_events(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_product_group ON chat_events(product_group)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_question_type ON chat_events(question_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_agent_status ON chat_events(agent_status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_doc_timestamp ON document_events(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_system_timestamp ON system_events(timestamp)")
            
            conn.commit()
    
    def _get_question_type(self, query: str) -> QuestionType:
        """Determine question type based on query content"""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ['spec', 'specification', 'technical', 'parameter']):
            return QuestionType.TECHNICAL_SPECS
        elif any(word in query_lower for word in ['use', 'how to', 'instruction', 'manual']):
            return QuestionType.USAGE_INSTRUCTIONS
        elif any(word in query_lower for word in ['problem', 'error', 'issue', 'trouble', 'fix']):
            return QuestionType.TROUBLESHOOTING
        elif any(word in query_lower for word in ['compare', 'difference', 'vs', 'versus']):
            return QuestionType.COMPARISON
        elif any(word in query_lower for word in ['price', 'cost', 'expensive', 'cheap']):
            return QuestionType.PRICING
        elif any(word in query_lower for word in ['available', 'stock', 'inventory']):
            return QuestionType.AVAILABILITY
        elif any(word in query_lower for word in ['safe', 'safety', 'risk', 'danger']):
            return QuestionType.SAFETY
        elif any(word in query_lower for word in ['maintain', 'maintenance', 'service']):
            return QuestionType.MAINTENANCE
        elif any(word in query_lower for word in ['what is', 'tell me about', 'describe']):
            return QuestionType.PRODUCT_INFO
        else:
            return QuestionType.GENERAL
    
    def _get_agent_status(self, confidence_score: float, response: str) -> AgentStatus:
        """Determine agent status based on confidence and response"""
        if confidence_score >= 0.7 and response.strip():
            return AgentStatus.SUCCESS
        elif confidence_score >= 0.4 and response.strip():
            return AgentStatus.PARTIAL
        elif not response.strip():
            return AgentStatus.FAILED
        else:
            return AgentStatus.FAILED
    
    def log_chat_event(self, 
                      query: str,
                      response: str,
                      session_id: Optional[str] = None,
                      user_id: Optional[str] = None,
                      product_group: Optional[str] = None,
                      response_time_ms: int = 0,
                      token_count: int = 0,
                      confidence_score: float = 0.0,
                      sources_count: int = 0,
                      chain_of_thought: Optional[List[Dict[str, Any]]] = None,
                      input_validation: Optional[Dict[str, Any]] = None,
                      response_validation: Optional[Dict[str, Any]] = None,
                      multimodal: bool = False,
                      extracted_text: Optional[str] = None,
                      metadata: Optional[Dict[str, Any]] = None):
        """Log a chat interaction event"""
        
        event = ChatEvent(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            session_id=session_id,
            user_id=user_id,
            event_type="chat",
            query=query,
            response=response,
            question_type=self._get_question_type(query),
            product_group=product_group,
            response_time_ms=response_time_ms,
            token_count=token_count,
            confidence_score=confidence_score,
            agent_status=self._get_agent_status(confidence_score, response),
            sources_count=sources_count,
            chain_of_thought=chain_of_thought,
            input_validation=input_validation,
            response_validation=response_validation,
            multimodal=multimodal,
            extracted_text=extracted_text,
            metadata=metadata or {}
        )
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO chat_events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event.event_id,
                event.timestamp.isoformat(),
                event.session_id,
                event.user_id,
                event.query,
                event.response,
                event.question_type.value,
                event.product_group,
                event.response_time_ms,
                event.token_count,
                event.confidence_score,
                event.agent_status.value,
                event.sources_count,
                json.dumps(event.chain_of_thought) if event.chain_of_thought else None,
                json.dumps(event.input_validation) if event.input_validation else None,
                json.dumps(event.response_validation) if event.response_validation else None,
                event.multimodal,
                event.extracted_text,
                json.dumps(event.metadata)
            ))
            conn.commit()
        
        logger.info(f"Logged chat event: {event.event_id}")
        return event
    
    def log_document_event(self,
                          filename: str,
                          file_size: int,
                          chunk_count: int,
                          processing_time_ms: int,
                          session_id: Optional[str] = None,
                          user_id: Optional[str] = None,
                          product_group: Optional[str] = None,
                          metadata: Optional[Dict[str, Any]] = None):
        """Log a document upload/processing event"""
        
        event = DocumentEvent(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            session_id=session_id,
            user_id=user_id,
            event_type="document",
            filename=filename,
            file_size=file_size,
            chunk_count=chunk_count,
            product_group=product_group,
            processing_time_ms=processing_time_ms,
            metadata=metadata or {}
        )
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO document_events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event.event_id,
                event.timestamp.isoformat(),
                event.session_id,
                event.user_id,
                event.filename,
                event.file_size,
                event.chunk_count,
                event.product_group,
                event.processing_time_ms,
                json.dumps(event.metadata)
            ))
            conn.commit()
        
        logger.info(f"Logged document event: {event.event_id}")
        return event
    
    def log_system_event(self,
                        component: str,
                        operation: str,
                        status: str,
                        session_id: Optional[str] = None,
                        user_id: Optional[str] = None,
                        error_message: Optional[str] = None,
                        metadata: Optional[Dict[str, Any]] = None):
        """Log a system-level event"""
        
        event = SystemEvent(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            session_id=session_id,
            user_id=user_id,
            event_type="system",
            component=component,
            operation=operation,
            status=status,
            error_message=error_message,
            metadata=metadata or {}
        )
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO system_events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event.event_id,
                event.timestamp.isoformat(),
                event.session_id,
                event.user_id,
                event.component,
                event.operation,
                event.status,
                event.error_message,
                json.dumps(event.metadata)
            ))
            conn.commit()
        
        logger.info(f"Logged system event: {event.event_id}")
        return event
    
    def get_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Get comprehensive analytics for the dashboard"""
        since_date = datetime.now() - timedelta(days=days)
        
        with sqlite3.connect(self.db_path) as conn:
            # Chat analytics
            chat_stats = conn.execute("""
                SELECT 
                    COUNT(*) as total_queries,
                    AVG(response_time_ms) as avg_response_time,
                    AVG(token_count) as avg_tokens,
                    AVG(confidence_score) as avg_confidence,
                    COUNT(CASE WHEN agent_status = 'success' THEN 1 END) as successful_queries,
                    COUNT(CASE WHEN agent_status = 'failed' THEN 1 END) as failed_queries,
                    COUNT(CASE WHEN multimodal = 1 THEN 1 END) as multimodal_queries
                FROM chat_events 
                WHERE timestamp >= ?
            """, (since_date.isoformat(),)).fetchone()
            
            # Question type distribution
            question_types = conn.execute("""
                SELECT question_type, COUNT(*) as count
                FROM chat_events 
                WHERE timestamp >= ?
                GROUP BY question_type
                ORDER BY count DESC
            """, (since_date.isoformat(),)).fetchall()
            
            # Product group distribution
            product_groups = conn.execute("""
                SELECT product_group, COUNT(*) as count
                FROM chat_events 
                WHERE timestamp >= ? AND product_group IS NOT NULL
                GROUP BY product_group
                ORDER BY count DESC
            """, (since_date.isoformat(),)).fetchall()
            
            # Daily activity
            daily_activity = conn.execute("""
                SELECT DATE(timestamp) as date, COUNT(*) as count
                FROM chat_events 
                WHERE timestamp >= ?
                GROUP BY DATE(timestamp)
                ORDER BY date
            """, (since_date.isoformat(),)).fetchall()
            
            # Document upload stats
            doc_stats = conn.execute("""
                SELECT 
                    COUNT(*) as total_uploads,
                    AVG(file_size) as avg_file_size,
                    AVG(chunk_count) as avg_chunks,
                    AVG(processing_time_ms) as avg_processing_time
                FROM document_events 
                WHERE timestamp >= ?
            """, (since_date.isoformat(),)).fetchone()
            
            # System events
            system_events = conn.execute("""
                SELECT component, operation, status, COUNT(*) as count
                FROM system_events 
                WHERE timestamp >= ?
                GROUP BY component, operation, status
                ORDER BY count DESC
            """, (since_date.isoformat(),)).fetchall()
        
        return {
            "chat_stats": {
                "total_queries": chat_stats[0] or 0,
                "avg_response_time": round(chat_stats[1] or 0, 2),
                "avg_tokens": round(chat_stats[2] or 0, 2),
                "avg_confidence": round(chat_stats[3] or 0, 3),
                "success_rate": round((chat_stats[4] or 0) / max(chat_stats[0] or 1, 1) * 100, 2),
                "failed_queries": chat_stats[5] or 0,
                "multimodal_queries": chat_stats[6] or 0
            },
            "question_types": [{"type": qt[0], "count": qt[1]} for qt in question_types],
            "product_groups": [{"group": pg[0], "count": pg[1]} for pg in product_groups],
            "daily_activity": [{"date": da[0], "count": da[1]} for da in daily_activity],
            "document_stats": {
                "total_uploads": doc_stats[0] or 0,
                "avg_file_size": round(doc_stats[1] or 0, 2),
                "avg_chunks": round(doc_stats[2] or 0, 2),
                "avg_processing_time": round(doc_stats[3] or 0, 2)
            },
            "system_events": [{"component": se[0], "operation": se[1], "status": se[2], "count": se[3]} for se in system_events]
        }
    
    def get_recent_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent events for the dashboard"""
        with sqlite3.connect(self.db_path) as conn:
            # Get recent chat events
            chat_events = conn.execute("""
                SELECT timestamp, query, response, question_type, product_group, 
                       response_time_ms, confidence_score, agent_status
                FROM chat_events 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (limit,)).fetchall()
            
            # Get recent document events
            doc_events = conn.execute("""
                SELECT timestamp, filename, file_size, chunk_count, product_group, processing_time_ms
                FROM document_events 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (limit,)).fetchall()
            
            # Get recent system events
            sys_events = conn.execute("""
                SELECT timestamp, component, operation, status, error_message
                FROM system_events 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (limit,)).fetchall()
        
        return {
            "chat_events": [
                {
                    "timestamp": ce[0],
                    "query": ce[1][:100] + "..." if len(ce[1]) > 100 else ce[1],
                    "response": ce[2][:100] + "..." if len(ce[2]) > 100 else ce[2],
                    "question_type": ce[3],
                    "product_group": ce[4],
                    "response_time_ms": ce[5],
                    "confidence_score": ce[6],
                    "agent_status": ce[7]
                } for ce in chat_events
            ],
            "document_events": [
                {
                    "timestamp": de[0],
                    "filename": de[1],
                    "file_size": de[2],
                    "chunk_count": de[3],
                    "product_group": de[4],
                    "processing_time_ms": de[5]
                } for de in doc_events
            ],
            "system_events": [
                {
                    "timestamp": se[0],
                    "component": se[1],
                    "operation": se[2],
                    "status": se[3],
                    "error_message": se[4]
                } for se in sys_events
            ]
        } 