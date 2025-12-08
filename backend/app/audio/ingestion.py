"""Helper functions for ingesting and converting incoming audio data."""
import numpy as np
import time
from typing import Optional
from app.audio.models import AudioFrame
from app.core.config import settings
from app.core.logging import logger


def bytes_to_audio_frame(
    data: bytes,
    stream_id: str,
    sample_rate: Optional[int] = None
) -> AudioFrame:
    """
    Convert raw PCM bytes to an AudioFrame.
    
    Args:
        data: Raw PCM int16 bytes
        stream_id: Unique identifier for the stream
        sample_rate: Sample rate (defaults to config value)
        
    Returns:
        AudioFrame object
    """
    if sample_rate is None:
        sample_rate = settings.sample_rate
    
    # Convert bytes to int16 numpy array
    pcm_array = np.frombuffer(data, dtype=np.int16)
    
    # Ensure mono (flatten if needed)
    if len(pcm_array.shape) > 1:
        pcm_array = pcm_array.flatten()
    
    return AudioFrame(
        pcm_data=pcm_array,
        sample_rate=sample_rate,
        timestamp=time.time(),
        stream_id=stream_id
    )


def validate_audio_data(data: bytes, expected_size: Optional[int] = None) -> bool:
    """
    Validate incoming audio data.
    
    Args:
        data: Raw audio bytes
        expected_size: Expected size in bytes (optional)
        
    Returns:
        True if valid, False otherwise
    """
    if len(data) == 0:
        logger.warning("Received empty audio data")
        return False
    
    # Check if size is multiple of 2 (int16 = 2 bytes)
    if len(data) % 2 != 0:
        logger.warning(f"Audio data size {len(data)} is not multiple of 2 bytes")
        return False
    
    if expected_size and len(data) != expected_size:
        logger.warning(f"Audio data size {len(data)} != expected {expected_size}")
        return False
    
    return True

