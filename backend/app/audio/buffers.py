"""Audio buffering and queue management per stream."""
import asyncio
from typing import Dict, Optional
from collections import deque
import numpy as np
from app.audio.models import AudioFrame, StreamState
from app.core.config import settings
from app.core.logging import logger


class StreamBuffer:
    """Manages audio frame buffering for a single stream."""
    
    def __init__(self, stream_id: str, max_frames: int = 500):
        """
        Initialize buffer for a stream.
        
        Args:
            stream_id: Unique identifier for the stream
            max_frames: Maximum number of frames to keep in buffer
                      Increased to 500 to handle real-time streaming better
        """
        self.stream_id = stream_id
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=max_frames)
        self.frame_history: deque = deque(maxlen=max_frames)
        self.state = StreamState(
            stream_id=stream_id,
            created_at=asyncio.get_event_loop().time(),
            last_frame_time=0.0,
            frame_count=0
        )
    
    async def add_frame(self, frame: AudioFrame) -> None:
        """Add a frame to the buffer."""
        try:
            self.queue.put_nowait(frame)
            self.frame_history.append(frame)
            self.state.frame_count += 1
            self.state.last_frame_time = frame.timestamp
        except asyncio.QueueFull:
            logger.warning(f"Buffer full for stream {self.stream_id}, dropping oldest frame")
            try:
                self.queue.get_nowait()  # Remove oldest
                self.queue.put_nowait(frame)  # Add new
            except asyncio.QueueEmpty:
                pass
    
    async def get_frame(self, timeout: Optional[float] = None) -> Optional[AudioFrame]:
        """Get the next frame from the buffer."""
        try:
            return await asyncio.wait_for(self.queue.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None
    
    def get_recent_frames(self, window_seconds: float) -> list[AudioFrame]:
        """
        Get frames from the last N seconds.
        
        Args:
            window_seconds: Time window in seconds
            
        Returns:
            List of frames within the time window
        """
        if not self.frame_history:
            return []
        
        current_time = self.frame_history[-1].timestamp
        cutoff_time = current_time - window_seconds
        
        return [f for f in self.frame_history if f.timestamp >= cutoff_time]


class StreamBufferManager:
    """Manages buffers for all active streams."""
    
    def __init__(self):
        """Initialize the buffer manager."""
        self._buffers: Dict[str, StreamBuffer] = {}
        self._lock = asyncio.Lock()
    
    async def get_or_create_buffer(self, stream_id: str) -> StreamBuffer:
        """Get existing buffer or create a new one for a stream."""
        async with self._lock:
            if stream_id not in self._buffers:
                self._buffers[stream_id] = StreamBuffer(stream_id)
                logger.info(f"Created buffer for stream {stream_id}")
            return self._buffers[stream_id]
    
    async def remove_buffer(self, stream_id: str) -> None:
        """Remove buffer for a stream (on disconnect)."""
        async with self._lock:
            if stream_id in self._buffers:
                del self._buffers[stream_id]
                logger.info(f"Removed buffer for stream {stream_id}")
    
    async def get_buffer(self, stream_id: str) -> Optional[StreamBuffer]:
        """Get buffer for a stream if it exists."""
        async with self._lock:
            return self._buffers.get(stream_id)
    
    async def list_stream_ids(self) -> list[str]:
        """Get list of all active stream IDs."""
        async with self._lock:
            return list(self._buffers.keys())
    
    async def get_stream_count(self) -> int:
        """Get number of active streams."""
        async with self._lock:
            return len(self._buffers)


# Global buffer manager instance
buffer_manager = StreamBufferManager()

