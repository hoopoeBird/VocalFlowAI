"""Gain normalization and automatic gain control (AGC)."""
import numpy as np
from app.audio.models import AudioFrame
from app.core.logging import logger

# AGC state for smooth gain adjustments (per-stream would be better, but keeping it simple)
_agc_target_rms = 6000.0  # Target RMS level for confident speech
_agc_smoothing = 0.85  # Smoothing factor for gain changes (0.0-1.0, higher = smoother)
_current_gain = 1.0  # Current gain factor


def normalize_gain(frame: AudioFrame, target_rms: float = 6000.0, max_gain: float = 4.0, min_gain: float = 0.1) -> AudioFrame:
    """
    Normalize audio gain using automatic gain control (AGC).
    
    Phase 2 implementation: Real-time AGC with smooth gain transitions.
    Keeps loudness in a "confident" range, avoiding very quiet speech and clipping.
    
    Args:
        frame: Input audio frame
        target_rms: Target RMS level (default 6000.0 for int16 range, ~18% of max)
        max_gain: Maximum gain factor to prevent excessive amplification
        min_gain: Minimum gain factor to prevent over-attenuation
        
    Returns:
        New AudioFrame with normalized gain
    """
    global _current_gain
    
    if len(frame.pcm_data) == 0:
        return frame
    
    # Calculate current RMS
    current_rms = np.sqrt(np.mean(frame.pcm_data.astype(np.float32) ** 2))
    
    # Avoid division by zero or very quiet signals
    if current_rms < 10.0:  # Very quiet, don't amplify noise
        return frame
    
    # Calculate desired gain factor
    desired_gain = target_rms / current_rms
    
    # Limit gain range
    desired_gain = np.clip(desired_gain, min_gain, max_gain)
    
    # Smooth gain transitions to avoid artifacts (exponential moving average)
    _current_gain = _agc_smoothing * _current_gain + (1.0 - _agc_smoothing) * desired_gain
    
    # Apply gain
    normalized = (frame.pcm_data.astype(np.float32) * _current_gain).astype(np.int16)
    
    # Prevent clipping with soft limiter
    max_val = np.iinfo(np.int16).max
    min_val = np.iinfo(np.int16).min
    
    # Soft clipping: compress peaks instead of hard clipping
    peak = np.max(np.abs(normalized))
    if peak > max_val * 0.9:  # If approaching clipping
        # Soft compression for peaks above 90% of max
        compression_ratio = 0.7  # Compress by 30%
        threshold = max_val * 0.9
        normalized = np.where(
            np.abs(normalized) > threshold,
            np.sign(normalized) * (threshold + (np.abs(normalized) - threshold) * compression_ratio),
            normalized
        )
    
    # Final hard clip as safety
    normalized = np.clip(normalized, min_val, max_val)
    
    return AudioFrame(
        pcm_data=normalized,
        sample_rate=frame.sample_rate,
        timestamp=frame.timestamp,
        stream_id=frame.stream_id
    )

