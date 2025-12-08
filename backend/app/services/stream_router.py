"""Stream routing and management between endpoints."""
import asyncio
from typing import Set
from app.core.logging import logger


class StreamRouter:
    """Routes audio streams between different endpoints."""
    
    def __init__(self):
        """Initialize the stream router."""
        self._active_streams: Set[str] = set()
        self._lock = asyncio.Lock()
    
    async def register_stream(self, stream_id: str) -> None:
        """
        Register a new active stream.
        
        Args:
            stream_id: Stream identifier
        """
        async with self._lock:
            self._active_streams.add(stream_id)
            logger.info(f"Registered stream: {stream_id}")
    
    async def unregister_stream(self, stream_id: str) -> None:
        """
        Unregister a stream.
        
        Args:
            stream_id: Stream identifier
        """
        async with self._lock:
            self._active_streams.discard(stream_id)
            logger.info(f"Unregistered stream: {stream_id}")
    
    async def is_stream_active(self, stream_id: str) -> bool:
        """
        Check if a stream is active.
        
        Args:
            stream_id: Stream identifier
            
        Returns:
            True if stream is active
        """
        async with self._lock:
            return stream_id in self._active_streams
    
    async def list_active_streams(self) -> list[str]:
        """
        Get list of all active stream IDs.
        
        Returns:
            List of active stream IDs
        """
        async with self._lock:
            return list(self._active_streams)


# Global stream router instance
stream_router = StreamRouter()

