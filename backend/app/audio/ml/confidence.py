"""Confidence scoring logic for voice quality."""
from typing import Dict
import numpy as np
from app.core.config import settings
from app.core.logging import logger

# Global state for confidence smoothing (exponential moving average)
_confidence_history: Dict[str, float] = {}


def score_confidence_phase1(features: Dict[str, float]) -> float:
    """
    Phase 1: Simple rule-based confidence scoring using RMS.
    
    This is the MVP implementation - very basic scoring based on loudness.
    
    Args:
        features: Dictionary of extracted features
        
    Returns:
        Confidence score from 0-100
    """
    rms_mean = features.get("rms_mean", 0.0)
    
    # Simple linear mapping: RMS 0-10000 maps to confidence 0-100
    # This is a basic heuristic - adjust thresholds based on testing
    confidence = min(100.0, max(0.0, (rms_mean / 10000.0) * 100.0))
    
    return confidence


def score_confidence_phase2(features: Dict[str, float]) -> float:
    """
    Phase 2: Improved rule-based confidence scoring.
    
    Uses multiple features: RMS, pitch stability, silence ratio, speech rate.
    
    Args:
        features: Dictionary of extracted features
        
    Returns:
        Confidence score from 0-100
    """
    rms_mean = features.get("rms_mean", 0.0)
    rms_variance = features.get("rms_variance", 0.0)
    pitch_mean = features.get("pitch_mean", 0.0)
    pitch_variance = features.get("pitch_variance", 0.0)
    silence_ratio = features.get("silence_ratio", 1.0)
    speech_rate = features.get("speech_rate", 0.0)
    
    # Component scores (0-1 range)
    
    # 1. Loudness score (normalized RMS)
    loudness_score = min(1.0, rms_mean / 8000.0)  # Good loudness around 8000
    
    # 2. Stability score (lower variance = more stable = higher confidence)
    # Normalize variance (lower is better)
    rms_stability = 1.0 / (1.0 + rms_variance / 1000000.0)
    
    # 3. Pitch presence score (has detectable pitch = good)
    pitch_presence = 1.0 if pitch_mean > 0 else 0.3
    
    # 4. Pitch stability (lower variance = more stable)
    pitch_stability = 1.0 / (1.0 + pitch_variance / 1000.0) if pitch_mean > 0 else 0.5
    
    # 5. Speech activity score (lower silence = more speech = better)
    speech_activity = 1.0 - silence_ratio
    
    # 6. Speech rate score (moderate rate is good, too fast/slow is less confident)
    # Normalize speech rate (assume good range is 2-10 transitions/sec)
    if speech_rate > 0:
        rate_score = 1.0 - abs(speech_rate - 6.0) / 10.0
        rate_score = max(0.0, min(1.0, rate_score))
    else:
        rate_score = 0.3
    
    # Weighted combination
    confidence = (
        loudness_score * 0.25 +
        rms_stability * 0.15 +
        pitch_presence * 0.15 +
        pitch_stability * 0.15 +
        speech_activity * 0.20 +
        rate_score * 0.10
    )
    
    # Convert to 0-100 scale
    confidence = confidence * 100.0
    confidence = max(0.0, min(100.0, confidence))
    
    return confidence


def score_confidence_phase3(features: Dict[str, float]) -> float:
    """
    Phase 3: Advanced rule-based confidence scoring with spectral features.
    
    Uses comprehensive feature set:
    - RMS loudness and stability
    - Pitch presence and stability
    - Silence ratio
    - Speech rate
    - Spectral centroid (brightness)
    - Zero-crossing rate (voicing indicator)
    
    Args:
        features: Dictionary of extracted features
        
    Returns:
        Confidence score from 0-100
    """
    rms_mean = features.get("rms_mean", 0.0)
    rms_variance = features.get("rms_variance", 0.0)
    pitch_mean = features.get("pitch_mean", 0.0)
    pitch_variance = features.get("pitch_variance", 0.0)
    silence_ratio = features.get("silence_ratio", 1.0)
    speech_rate = features.get("speech_rate", 0.0)
    spectral_centroid_mean = features.get("spectral_centroid_mean", 0.0)
    spectral_centroid_variance = features.get("spectral_centroid_variance", 0.0)
    zcr_mean = features.get("zcr_mean", 0.0)
    zcr_variance = features.get("zcr_variance", 0.0)
    
    # Component scores (0-1 range)
    
    # 1. Loudness score (normalized RMS)
    loudness_score = min(1.0, rms_mean / 8000.0)
    
    # 2. RMS stability (lower variance = more stable)
    rms_stability = 1.0 / (1.0 + rms_variance / 1000000.0)
    
    # 3. Pitch presence (has detectable pitch = good)
    pitch_presence = 1.0 if pitch_mean > 0 else 0.3
    
    # 4. Pitch stability (lower variance = more stable)
    pitch_stability = 1.0 / (1.0 + pitch_variance / 1000.0) if pitch_mean > 0 else 0.5
    
    # 5. Speech activity (lower silence = more speech)
    speech_activity = 1.0 - silence_ratio
    
    # 6. Speech rate (moderate rate is good)
    if speech_rate > 0:
        rate_score = 1.0 - abs(speech_rate - 6.0) / 10.0
        rate_score = max(0.0, min(1.0, rate_score))
    else:
        rate_score = 0.3
    
    # 7. Spectral centroid (brightness) - Phase 3 feature
    # Good speech typically has centroid in 1000-3000 Hz range
    if spectral_centroid_mean > 0:
        # Normalize: ideal around 2000 Hz
        centroid_score = 1.0 - abs(spectral_centroid_mean - 2000.0) / 3000.0
        centroid_score = max(0.0, min(1.0, centroid_score))
    else:
        centroid_score = 0.5
    
    # 8. Spectral stability (lower variance = more stable)
    spectral_stability = 1.0 / (1.0 + spectral_centroid_variance / 500000.0)
    
    # 9. Zero-crossing rate (ZCR) - Phase 3 feature
    # Lower ZCR indicates voiced speech (good), higher indicates noise/unvoiced
    # Good speech typically has ZCR in 0.05-0.15 range
    if zcr_mean > 0:
        zcr_score = 1.0 - abs(zcr_mean - 0.10) / 0.20  # Ideal around 0.10
        zcr_score = max(0.0, min(1.0, zcr_score))
    else:
        zcr_score = 0.5
    
    # 10. ZCR stability
    zcr_stability = 1.0 / (1.0 + zcr_variance / 0.01)
    
    # Weighted combination (Phase 3: more sophisticated weighting)
    confidence = (
        loudness_score * 0.20 +           # Reduced from 0.25
        rms_stability * 0.12 +             # Reduced from 0.15
        pitch_presence * 0.12 +            # Reduced from 0.15
        pitch_stability * 0.12 +           # Reduced from 0.15
        speech_activity * 0.15 +           # Reduced from 0.20
        rate_score * 0.08 +                # Reduced from 0.10
        centroid_score * 0.08 +           # New: Phase 3
        spectral_stability * 0.05 +        # New: Phase 3
        zcr_score * 0.05 +                 # New: Phase 3
        zcr_stability * 0.03               # New: Phase 3
    )
    
    # Convert to 0-100 scale
    confidence = confidence * 100.0
    confidence = max(0.0, min(100.0, confidence))
    
    return confidence


def smooth_confidence(stream_id: str, raw_confidence: float, alpha: float = None) -> float:
    """
    Apply exponential moving average smoothing to confidence scores.
    
    Prevents jittery confidence values by smoothing across frames.
    
    Args:
        stream_id: Stream identifier (for per-stream smoothing)
        raw_confidence: Raw confidence score (0-100)
        alpha: Smoothing factor (0.0-1.0, higher = less smoothing)
               If None, uses config value
        
    Returns:
        Smoothed confidence score (0-100, integer)
    """
    global _confidence_history
    
    if alpha is None:
        alpha = settings.confidence_smoothing_alpha
    
    # Clamp alpha to valid range
    alpha = max(0.0, min(1.0, alpha))
    
    # Get previous confidence for this stream
    previous_confidence = _confidence_history.get(stream_id, raw_confidence)
    
    # Exponential moving average
    smoothed = alpha * raw_confidence + (1.0 - alpha) * previous_confidence
    
    # Update history
    _confidence_history[stream_id] = smoothed
    
    # Return as integer for stability
    return int(round(smoothed))


def score_confidence(features: Dict[str, float], phase: int = 3, stream_id: str = "default", apply_smoothing: bool = True) -> int:
    """
    Main confidence scoring function with Phase 3 enhancements.
    
    Args:
        features: Dictionary of extracted features
        phase: Implementation phase (1 = simple, 2 = improved, 3 = advanced)
        stream_id: Stream identifier for smoothing (optional)
        apply_smoothing: Whether to apply exponential smoothing
        
    Returns:
        Confidence score from 0-100 (integer)
    """
    if phase == 1:
        raw_confidence = score_confidence_phase1(features)
    elif phase == 2:
        raw_confidence = score_confidence_phase2(features)
    else:
        # Phase 3: Advanced scoring with spectral features
        raw_confidence = score_confidence_phase3(features)
    
    # Apply smoothing if requested
    if apply_smoothing:
        return smooth_confidence(stream_id, raw_confidence)
    else:
        return int(round(raw_confidence))

