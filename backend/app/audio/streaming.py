"""Helper functions for streaming processed audio output."""
import numpy as np
from app.audio.models import AudioFrame
from app.core.logging import logger


def frame_to_bytes(frame: AudioFrame) -> bytes:
    """
    Convert an AudioFrame to raw PCM bytes.
    
    Args:
        frame: Audio frame to convert
        
    Returns:
        Raw PCM bytes (int16)
    """
    return frame.pcm_data.tobytes()


def frames_to_continuous_audio(frames: list[AudioFrame]) -> np.ndarray:
    """
    Concatenate multiple frames into a continuous audio array.
    
    Args:
        frames: List of audio frames
        
    Returns:
        Concatenated numpy array of PCM samples
    """
    if not frames:
        return np.array([], dtype=np.int16)
    
    # Ensure all frames have same sample rate
    sample_rate = frames[0].sample_rate
    for frame in frames:
        if frame.sample_rate != sample_rate:
            logger.warning(f"Sample rate mismatch: {frame.sample_rate} != {sample_rate}")
    
    # Concatenate all PCM data
    audio_arrays = [frame.pcm_data for frame in frames]
    return np.concatenate(audio_arrays)

