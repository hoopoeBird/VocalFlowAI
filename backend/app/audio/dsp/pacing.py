"""Pacing, silence, and pause detection metrics."""
import numpy as np
from typing import List
from app.audio.models import AudioFrame
from app.core.logging import logger


def calculate_silence_ratio(frames: List[AudioFrame], silence_threshold_db: float = -30.0) -> float:
    """
    Calculate the ratio of silence in a window of frames.
    
    Args:
        frames: List of audio frames to analyze
        silence_threshold_db: RMS level below which audio is considered silence
        
    Returns:
        Ratio of silence (0.0 = no silence, 1.0 = all silence)
    """
    if not frames:
        return 1.0
    
    total_samples = 0
    silent_samples = 0
    
    for frame in frames:
        if len(frame.pcm_data) == 0:
            continue
        
        # Calculate RMS in dB
        rms = np.sqrt(np.mean(frame.pcm_data.astype(np.float32) ** 2))
        rms_db = 20 * np.log10(rms / np.iinfo(np.int16).max + 1e-10)
        
        frame_samples = len(frame.pcm_data)
        total_samples += frame_samples
        
        if rms_db < silence_threshold_db:
            silent_samples += frame_samples
    
    if total_samples == 0:
        return 1.0
    
    return silent_samples / total_samples


def estimate_speech_rate(frames: List[AudioFrame], window_seconds: float) -> float:
    """
    Estimate speech rate (rough approximation based on energy variations).
    
    Args:
        frames: List of audio frames to analyze
        window_seconds: Time window in seconds
        
    Returns:
        Estimated speech rate (arbitrary units, higher = more active speech)
    """
    if not frames or window_seconds <= 0:
        return 0.0
    
    # Calculate energy variations (indicator of speech activity)
    energies = []
    for frame in frames:
        if len(frame.pcm_data) > 0:
            rms = np.sqrt(np.mean(frame.pcm_data.astype(np.float32) ** 2))
            energies.append(rms)
    
    if len(energies) < 2:
        return 0.0
    
    # Count energy transitions (rough proxy for speech rate)
    threshold = np.mean(energies)
    transitions = sum(1 for i in range(1, len(energies)) 
                     if (energies[i-1] < threshold) != (energies[i] < threshold))
    
    # Normalize by time window
    speech_rate = transitions / window_seconds
    
    return speech_rate

