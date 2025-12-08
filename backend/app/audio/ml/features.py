"""Feature extraction from audio frames for confidence scoring."""
import numpy as np
from typing import List, Dict
from app.audio.models import AudioFrame
from app.audio.dsp.pitch import estimate_pitch
from app.audio.dsp.pacing import calculate_silence_ratio, estimate_speech_rate
from app.core.logging import logger


def extract_rms(frame: AudioFrame) -> float:
    """
    Extract RMS (Root Mean Square) loudness from a frame.
    
    Args:
        frame: Input audio frame
        
    Returns:
        RMS value (0.0 to ~32767.0 for int16)
    """
    if len(frame.pcm_data) == 0:
        return 0.0
    
    rms = np.sqrt(np.mean(frame.pcm_data.astype(np.float32) ** 2))
    return float(rms)


def extract_features(frames: List[AudioFrame]) -> Dict[str, float]:
    """
    Extract aggregated features from a window of frames.
    
    This function extracts features needed for confidence scoring:
    - RMS loudness (mean and variance)
    - Pitch estimate and stability
    - Silence ratio
    - Speech rate
    
    Args:
        frames: List of audio frames to analyze
        
    Returns:
        Dictionary of feature values
    """
    if not frames:
        return {
            "rms_mean": 0.0,
            "rms_variance": 0.0,
            "pitch_mean": 0.0,
            "pitch_variance": 0.0,
            "silence_ratio": 1.0,
            "speech_rate": 0.0
        }
    
    # Calculate time window
    if len(frames) > 1:
        window_seconds = frames[-1].timestamp - frames[0].timestamp
    else:
        window_seconds = len(frames[0].pcm_data) / frames[0].sample_rate
    
    # Extract RMS values
    rms_values = [extract_rms(frame) for frame in frames if len(frame.pcm_data) > 0]
    rms_mean = np.mean(rms_values) if rms_values else 0.0
    rms_variance = np.var(rms_values) if len(rms_values) > 1 else 0.0
    
    # Extract pitch estimates
    pitch_values = []
    for frame in frames:
        pitch = estimate_pitch(frame)
        if pitch > 0:
            pitch_values.append(pitch)
    
    pitch_mean = np.mean(pitch_values) if pitch_values else 0.0
    pitch_variance = np.var(pitch_values) if len(pitch_values) > 1 else 0.0
    
    # Calculate silence ratio
    silence_ratio = calculate_silence_ratio(frames)
    
    # Estimate speech rate
    speech_rate = estimate_speech_rate(frames, max(window_seconds, 0.1))
    
    return {
        "rms_mean": float(rms_mean),
        "rms_variance": float(rms_variance),
        "pitch_mean": float(pitch_mean),
        "pitch_variance": float(pitch_variance),
        "silence_ratio": float(silence_ratio),
        "speech_rate": float(speech_rate)
    }


def extract_spectral_centroid(frame: AudioFrame) -> float:
    """
    Extract spectral centroid from audio frame.
    
    Spectral centroid indicates the "brightness" of the sound.
    Higher values indicate brighter/more high-frequency content.
    
    Args:
        frame: Input audio frame
        
    Returns:
        Spectral centroid in Hz
    """
    if len(frame.pcm_data) < 2:
        return 0.0
    
    # Convert to float and normalize
    audio = frame.pcm_data.astype(np.float32) / np.iinfo(np.int16).max
    
    # Compute FFT
    fft_size = min(256, len(audio))
    if len(audio) > fft_size:
        audio = audio[:fft_size]
    elif len(audio) < fft_size:
        audio = np.pad(audio, (0, fft_size - len(audio)), mode='constant')
    
    fft = np.fft.rfft(audio)
    magnitude = np.abs(fft)
    
    # Frequency bins
    freqs = np.fft.rfftfreq(fft_size, 1.0 / frame.sample_rate)
    
    # Calculate weighted average frequency
    if np.sum(magnitude) > 0:
        centroid = np.sum(freqs * magnitude) / np.sum(magnitude)
        return float(centroid)
    
    return 0.0


def extract_zero_crossing_rate(frame: AudioFrame) -> float:
    """
    Extract zero-crossing rate (ZCR) from audio frame.
    
    ZCR indicates how often the signal crosses zero.
    Higher ZCR typically indicates noise or unvoiced speech.
    Lower ZCR indicates voiced speech or silence.
    
    Args:
        frame: Input audio frame
        
    Returns:
        Zero-crossing rate (0.0 to 1.0)
    """
    if len(frame.pcm_data) < 2:
        return 0.0
    
    # Convert to float
    audio = frame.pcm_data.astype(np.float32)
    
    # Count zero crossings
    signs = np.sign(audio)
    zero_crossings = np.sum(np.abs(np.diff(signs))) / 2.0
    
    # Normalize by frame length
    zcr = zero_crossings / len(audio)
    
    return float(zcr)


def extract_features(frames: List[AudioFrame]) -> Dict[str, float]:
    """
    Extract aggregated features from a window of frames.
    
    Phase 3: Enhanced feature extraction with spectral features.
    
    Features extracted:
    - RMS loudness (mean and variance)
    - Pitch estimate and stability
    - Silence ratio
    - Speech rate
    - Spectral centroid (brightness)
    - Zero-crossing rate (voicing indicator)
    
    Args:
        frames: List of audio frames to analyze
        
    Returns:
        Dictionary of feature values
    """
    if not frames:
        return {
            "rms_mean": 0.0,
            "rms_variance": 0.0,
            "pitch_mean": 0.0,
            "pitch_variance": 0.0,
            "silence_ratio": 1.0,
            "speech_rate": 0.0,
            "spectral_centroid_mean": 0.0,
            "spectral_centroid_variance": 0.0,
            "zcr_mean": 0.0,
            "zcr_variance": 0.0
        }
    
    # Calculate time window
    if len(frames) > 1:
        window_seconds = frames[-1].timestamp - frames[0].timestamp
    else:
        window_seconds = len(frames[0].pcm_data) / frames[0].sample_rate
    
    # Extract RMS values
    rms_values = [extract_rms(frame) for frame in frames if len(frame.pcm_data) > 0]
    rms_mean = np.mean(rms_values) if rms_values else 0.0
    rms_variance = np.var(rms_values) if len(rms_values) > 1 else 0.0
    
    # Extract pitch estimates
    pitch_values = []
    for frame in frames:
        pitch = estimate_pitch(frame)
        if pitch > 0:
            pitch_values.append(pitch)
    
    pitch_mean = np.mean(pitch_values) if pitch_values else 0.0
    pitch_variance = np.var(pitch_values) if len(pitch_values) > 1 else 0.0
    
    # Calculate silence ratio
    silence_ratio = calculate_silence_ratio(frames)
    
    # Estimate speech rate
    speech_rate = estimate_speech_rate(frames, max(window_seconds, 0.1))
    
    # Extract spectral features (Phase 3)
    spectral_centroids = [extract_spectral_centroid(frame) for frame in frames if len(frame.pcm_data) > 0]
    spectral_centroid_mean = np.mean(spectral_centroids) if spectral_centroids else 0.0
    spectral_centroid_variance = np.var(spectral_centroids) if len(spectral_centroids) > 1 else 0.0
    
    zcr_values = [extract_zero_crossing_rate(frame) for frame in frames if len(frame.pcm_data) > 0]
    zcr_mean = np.mean(zcr_values) if zcr_values else 0.0
    zcr_variance = np.var(zcr_values) if len(zcr_values) > 1 else 0.0
    
    return {
        "rms_mean": float(rms_mean),
        "rms_variance": float(rms_variance),
        "pitch_mean": float(pitch_mean),
        "pitch_variance": float(pitch_variance),
        "silence_ratio": float(silence_ratio),
        "speech_rate": float(speech_rate),
        "spectral_centroid_mean": float(spectral_centroid_mean),
        "spectral_centroid_variance": float(spectral_centroid_variance),
        "zcr_mean": float(zcr_mean),
        "zcr_variance": float(zcr_variance)
    }

