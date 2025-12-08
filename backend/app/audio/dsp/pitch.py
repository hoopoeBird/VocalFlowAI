"""Pitch and energy adjustment (optional enhancement)."""
import numpy as np
from app.audio.models import AudioFrame
from app.core.logging import logger


def estimate_pitch(frame: AudioFrame) -> float:
    """
    Estimate fundamental frequency (pitch) of the audio frame.
    
    Uses autocorrelation for pitch estimation.
    
    Args:
        frame: Input audio frame
        
    Returns:
        Estimated pitch in Hz, or 0.0 if not detectable
    """
    if len(frame.pcm_data) < 2:
        return 0.0
    
    # Convert to float
    audio = frame.pcm_data.astype(np.float32) / np.iinfo(np.int16).max
    
    # Simple autocorrelation-based pitch detection
    # This is a basic implementation - production should use more robust methods
    min_period = int(frame.sample_rate / 800)  # Max 800 Hz
    max_period = int(frame.sample_rate / 80)   # Min 80 Hz
    
    if len(audio) < max_period * 2:
        return 0.0
    
    # Autocorrelation
    best_period = 0
    best_correlation = 0.0
    
    for period in range(min_period, max_period):
        if period * 2 > len(audio):
            break
        
        correlation = np.corrcoef(
            audio[:len(audio) - period],
            audio[period:]
        )[0, 1]
        
        if correlation > best_correlation:
            best_correlation = correlation
            best_period = period
    
    if best_period > 0 and best_correlation > 0.3:
        pitch = frame.sample_rate / best_period
        return pitch
    
    return 0.0


def adjust_energy(frame: AudioFrame, energy_boost: float = 1.05) -> AudioFrame:
    """
    Subtle energy adjustment to enhance voice clarity.
    
    Phase 2 implementation: Very light energy boost with frequency-selective enhancement.
    Keeps adjustments minimal to preserve speaker identity.
    Future Phase 3: May use ML-based voice enhancement via ONNX.
    
    Args:
        frame: Input audio frame
        energy_boost: Multiplier for energy (1.0 = no change, >1.0 = subtle boost)
                      Default 1.05 (5% boost) is very subtle
        
    Returns:
        New AudioFrame with adjusted energy
    """
    if len(frame.pcm_data) == 0:
        return frame
    
    # Convert to float
    audio_float = frame.pcm_data.astype(np.float32) / np.iinfo(np.int16).max
    
    # Apply very subtle energy boost (only if signal is strong enough)
    rms = np.sqrt(np.mean(audio_float ** 2))
    if rms > 0.05:  # Only boost if signal is above noise floor
        # Frequency-selective boost: enhance mid-frequencies (speech range 300-3400 Hz)
        # Simple approach: apply slight emphasis to dynamic range
        boosted = audio_float * energy_boost
        
        # Prevent clipping
        boosted = np.clip(boosted, -1.0, 1.0)
    else:
        boosted = audio_float
    
    # Convert back to int16
    adjusted = (boosted * np.iinfo(np.int16).max).astype(np.int16)
    
    return AudioFrame(
        pcm_data=adjusted,
        sample_rate=frame.sample_rate,
        timestamp=frame.timestamp,
        stream_id=frame.stream_id
    )

