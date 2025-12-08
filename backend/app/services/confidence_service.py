"""Service for managing per-stream confidence state."""
import asyncio
from typing import Dict, Optional
from app.audio.models import StreamState
from app.audio.buffers import buffer_manager
from app.core.logging import logger


class ConfidenceService:
    """Manages confidence scores for all active streams."""
    
    def __init__(self):
        """Initialize the confidence service."""
        self._confidence_cache: Dict[str, float] = {}
        self._update_times: Dict[str, float] = {}
        self._lock = asyncio.Lock()
    
    async def update_confidence(self, stream_id: str, confidence: float) -> None:
        """
        Update confidence score for a stream.
        
        Args:
            stream_id: Stream identifier
            confidence: Confidence score (0-100)
        """
        async with self._lock:
            self._confidence_cache[stream_id] = confidence
            import time
            self._update_times[stream_id] = time.time()
            
            # Also update the stream state in buffer manager
            buffer = await buffer_manager.get_buffer(stream_id)
            if buffer:
                buffer.state.update_confidence(confidence)
    
    async def get_confidence(self, stream_id: str) -> Optional[float]:
        """
        Get latest confidence score for a stream.
        
        Args:
            stream_id: Stream identifier
            
        Returns:
            Confidence score or None if not found
        """
        async with self._lock:
            return self._confidence_cache.get(stream_id)
    
    async def get_confidence_with_timestamp(self, stream_id: str) -> Optional[dict]:
        """
        Get confidence score with update timestamp.
        
        Args:
            stream_id: Stream identifier
            
        Returns:
            Dictionary with confidence and updated_at, or None
        """
        async with self._lock:
            if stream_id not in self._confidence_cache:
                return None
            
            return {
                "stream_id": stream_id,
                "confidence": self._confidence_cache[stream_id],
                "updated_at": self._update_times.get(stream_id)
            }
    
    async def remove_stream(self, stream_id: str) -> None:
        """
        Remove confidence data for a stream (on disconnect).
        
        Args:
            stream_id: Stream identifier
        """
        async with self._lock:
            self._confidence_cache.pop(stream_id, None)
            self._update_times.pop(stream_id, None)
            logger.debug(f"Removed confidence data for stream {stream_id}")


# Global confidence service instance
confidence_service = ConfidenceService()

