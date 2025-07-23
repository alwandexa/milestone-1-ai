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
        
        # Calculate additional metrics
        total_queries = analytics["chat_stats"]["total_queries"]
        product_groups = analytics["product_groups"]
        
        # Calculate percentages and rankings
        for group in product_groups:
            group["percentage"] = round((group["count"] / max(total_queries, 1)) * 100, 2)
        
        # Sort by count descending
        product_groups.sort(key=lambda x: x["count"], reverse=True)
        
        return {
            "product_groups": product_groups,
            "total_queries": total_queries,
            "total_product_group_queries": sum(group["count"] for group in product_groups),
            "unclassified_queries": total_queries - sum(group["count"] for group in product_groups),
            "top_product_group": product_groups[0] if product_groups else None,
            "product_group_coverage": round((sum(group["count"] for group in product_groups) / max(total_queries, 1)) * 100, 2)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving product group stats: {str(e)}")

@router.get("/stats/product-groups/detailed")
async def get_detailed_product_group_analytics():
    """Get detailed product group analytics with trends and insights"""
    try:
        monitoring_service = get_monitoring_service()
        
        # Get analytics for different time periods
        analytics_7d = monitoring_service.get_analytics(days=7)
        analytics_30d = monitoring_service.get_analytics(days=30)
        
        # Calculate trends
        recent_groups = {pg["group"]: pg["count"] for pg in analytics_7d["product_groups"]}
        historical_groups = {pg["group"]: pg["count"] for pg in analytics_30d["product_groups"]}
        
        # Calculate growth rates
        growth_rates = {}
        for group in set(recent_groups.keys()) | set(historical_groups.keys()):
            recent_count = recent_groups.get(group, 0)
            historical_count = historical_groups.get(group, 0)
            
            if historical_count > 0:
                growth_rate = ((recent_count - historical_count) / historical_count) * 100
            else:
                growth_rate = 100 if recent_count > 0 else 0
            
            growth_rates[group] = round(growth_rate, 2)
        
        # Get top growing and declining groups
        growing_groups = sorted([(group, rate) for group, rate in growth_rates.items() if rate > 0], 
                              key=lambda x: x[1], reverse=True)[:5]
        declining_groups = sorted([(group, rate) for group, rate in growth_rates.items() if rate < 0], 
                                key=lambda x: x[1])[:5]
        
        return {
            "current_period": {
                "product_groups": analytics_7d["product_groups"],
                "total_queries": analytics_7d["chat_stats"]["total_queries"],
                "coverage": round((sum(pg["count"] for pg in analytics_7d["product_groups"]) / max(analytics_7d["chat_stats"]["total_queries"], 1)) * 100, 2)
            },
            "historical_period": {
                "product_groups": analytics_30d["product_groups"],
                "total_queries": analytics_30d["chat_stats"]["total_queries"],
                "coverage": round((sum(pg["count"] for pg in analytics_30d["product_groups"]) / max(analytics_30d["chat_stats"]["total_queries"], 1)) * 100, 2)
            },
            "trends": {
                "growth_rates": growth_rates,
                "top_growing": [{"group": group, "growth_rate": rate} for group, rate in growing_groups],
                "top_declining": [{"group": group, "growth_rate": rate} for group, rate in declining_groups]
            },
            "insights": {
                "most_popular": analytics_7d["product_groups"][0] if analytics_7d["product_groups"] else None,
                "least_popular": analytics_7d["product_groups"][-1] if analytics_7d["product_groups"] else None,
                "unclassified_percentage": round((analytics_7d["chat_stats"]["total_queries"] - sum(pg["count"] for pg in analytics_7d["product_groups"])) / max(analytics_7d["chat_stats"]["total_queries"], 1) * 100, 2)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving detailed product group analytics: {str(e)}")

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