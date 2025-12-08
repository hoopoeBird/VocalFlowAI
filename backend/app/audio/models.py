"""Audio data models and structures."""
from dataclasses import dataclass
from typing import Optional
import numpy as np
import time


@dataclass
class AudioFrame:
    """Represents a single audio frame with metadata."""
    pcm_data: np.ndarray  # int16 PCM samples
    sample_rate: int
    timestamp: float  # Unix timestamp when frame was received
    stream_id: str
    
    def __post_init__(self):
        """Validate frame data."""
        if self.pcm_data.dtype != np.int16:
            raise ValueError(f"Expected int16 PCM, got {self.pcm_data.dtype}")
        if len(self.pcm_data.shape) != 1:
            raise ValueError(f"Expected mono (1D array), got shape {self.pcm_data.shape}")


@dataclass
class StreamState:
    """Tracks state for an active audio stream."""
    stream_id: str
    created_at: float
    last_frame_time: float
    frame_count: int
    latest_confidence: Optional[float] = None
    confidence_updated_at: Optional[float] = None
    
    def update_confidence(self, confidence: float) -> None:
        """Update the confidence score for this stream."""
        self.latest_confidence = confidence
        self.confidence_updated_at = time.time()

