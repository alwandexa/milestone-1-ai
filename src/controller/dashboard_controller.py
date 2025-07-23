from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from src.infrastructure.monitoring_service import MonitoringService


router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

# Pydantic models for dashboard responses
class AnalyticsResponse(BaseModel):
    chat_stats: Dict[str, Any]
    question_types: List[Dict[str, Any]]
    product_groups: List[Dict[str, Any]]
    daily_activity: List[Dict[str, Any]]
    document_stats: Dict[str, Any]
    system_events: List[Dict[str, Any]]

class RecentEventsResponse(BaseModel):
    chat_events: List[Dict[str, Any]]
    document_events: List[Dict[str, Any]]
    system_events: List[Dict[str, Any]]



# Global monitoring service instance
_monitoring_service: Optional[MonitoringService] = None

def set_monitoring_service(monitoring_service: MonitoringService):
    """Set the monitoring service dependency"""
    global _monitoring_service
    _monitoring_service = monitoring_service

def get_monitoring_service() -> MonitoringService:
    """Get the monitoring service instance"""
    if _monitoring_service is None:
        raise HTTPException(status_code=500, detail="Monitoring service not initialized")
    return _monitoring_service

@router.get("/analytics", response_model=AnalyticsResponse)
async def get_analytics(days: int = 30):
    """Get comprehensive analytics for the dashboard"""
    try:
        monitoring_service = get_monitoring_service()
        analytics = monitoring_service.get_analytics(days=days)
        return AnalyticsResponse(**analytics)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving analytics: {str(e)}")

@router.get("/recent-events", response_model=RecentEventsResponse)
async def get_recent_events(limit: int = 50):
    """Get recent events for the dashboard"""
    try:
        monitoring_service = get_monitoring_service()
        events = monitoring_service.get_recent_events(limit=limit)
        return RecentEventsResponse(**events)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving recent events: {str(e)}")

@router.get("/health")
async def dashboard_health():
    """Check dashboard health"""
    try:
        monitoring_service = get_monitoring_service()
        # Try to get basic analytics to verify database connection
        analytics = monitoring_service.get_analytics(days=1)
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dashboard health check failed: {str(e)}")

@router.get("/stats/summary")
async def get_summary_stats():
    """Get summary statistics for quick overview"""
    try:
        monitoring_service = get_monitoring_service()
        analytics = monitoring_service.get_analytics(days=30)
        
        return {
            "total_queries": analytics["chat_stats"]["total_queries"],
            "success_rate": analytics["chat_stats"]["success_rate"],
            "avg_response_time": analytics["chat_stats"]["avg_response_time"],
            "total_uploads": analytics["document_stats"]["total_uploads"],
            "top_product_group": analytics["product_groups"][0]["group"] if analytics["product_groups"] else None,
            "top_question_type": analytics["question_types"][0]["type"] if analytics["question_types"] else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving summary stats: {str(e)}")

@router.get("/stats/product-groups")
async def get_product_group_stats():
    """Get detailed product group statistics"""
    try:
        monitoring_service = get_monitoring_service()
        analytics = monitoring_service.get_analytics(days=30)
        
        return {
            "product_groups": analytics["product_groups"],
            "total_queries": analytics["chat_stats"]["total_queries"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving product group stats: {str(e)}")

@router.get("/stats/question-types")
async def get_question_type_stats():
    """Get detailed question type statistics"""
    try:
        monitoring_service = get_monitoring_service()
        analytics = monitoring_service.get_analytics(days=30)
        
        return {
            "question_types": analytics["question_types"],
            "total_queries": analytics["chat_stats"]["total_queries"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving question type stats: {str(e)}")

@router.get("/stats/performance")
async def get_performance_stats():
    """Get performance-related statistics"""
    try:
        monitoring_service = get_monitoring_service()
        analytics = monitoring_service.get_analytics(days=30)
        
        return {
            "response_time": {
                "average": analytics["chat_stats"]["avg_response_time"],
                "unit": "ms"
            },
            "tokens": {
                "average": analytics["chat_stats"]["avg_tokens"],
                "unit": "tokens"
            },
            "confidence": {
                "average": analytics["chat_stats"]["avg_confidence"],
                "unit": "score"
            },
            "success_rate": {
                "percentage": analytics["chat_stats"]["success_rate"],
                "unit": "%"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving performance stats: {str(e)}") 