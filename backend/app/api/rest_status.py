"""REST endpoints for health and status."""
from fastapi import APIRouter, HTTPException
from datetime import datetime
from app.services.confidence_service import confidence_service
from app.audio.buffers import buffer_manager
from app.core.logging import logger

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Health check endpoint.
    
    Returns:
        Status and version information
    """
    return {
        "status": "ok",
        "version": "0.1.0"
    }


@router.get("/streams/{stream_id}/confidence")
async def get_stream_confidence(stream_id: str):
    """
    Get latest confidence score for a stream.
    
    Args:
        stream_id: Stream identifier
        
    Returns:
        Confidence score with timestamp
    """
    result = await confidence_service.get_confidence_with_timestamp(stream_id)
    
    if result is None:
        raise HTTPException(status_code=404, detail=f"Stream {stream_id} not found")
    
    # Format timestamp as ISO 8601
    if result["updated_at"]:
        result["updated_at"] = datetime.fromtimestamp(result["updated_at"]).isoformat() + "Z"
    
    return result

