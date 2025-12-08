"""Voice Confidence Booster - Psychoacoustic enhancement for perceived confidence.

This module applies subtle audio enhancements to increase the perceived clarity,
presence, and confidence of the user's voice without altering their identity.

Psychoacoustic Rationale:
- High-frequency boost (2-5 kHz): Enhances clarity and intelligibility by emphasizing
  consonant sounds and speech articulation. This frequency range is critical for
  understanding speech in noisy environments.
  
- Presence lift (500-1500 Hz): Adds warmth and presence to the voice, making it
  sound more authoritative and confident. This range contains important formant
  frequencies that contribute to vocal character.
  
- Dynamic energy enhancement: Applies upward compression to quiet speech, making
  it more audible and confident-sounding without affecting already-strong speech.
  
- Micro-pitch enhancement: Subtle pitch lift for low-confidence speech can make
  the voice sound more energetic and engaged, while preserving natural pitch
  variation for high-confidence speech.
  
All enhancements are designed to be subtle and preserve the speaker's identity
while improving perceived confidence and clarity.
"""
import numpy as np
from typing import Optional
from app.audio.models import AudioFrame
from app.core.config import settings
from app.core.logging import logger

# Try to import scipy for advanced filtering, fallback to numpy if not available
try:
    from scipy import signal
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    logger.debug("scipy not available, using numpy-based filtering")

# Global state for confidence-based processing (per-stream would be better)
_current_confidence: float = 50.0  # Default confidence


def set_confidence(confidence: float) -> None:
    """
    Set current confidence score for confidence-based processing.
    
    Args:
        confidence: Confidence score (0-100)
    """
    global _current_confidence
    _current_confidence = max(0.0, min(100.0, confidence))


def _apply_spectral_shaping(audio_float: np.ndarray, sample_rate: int) -> np.ndarray:
    """
    Apply micro-EQ / spectral shaping for clarity and presence.
    
    Implements:
    - High-end boost (2-5 kHz) for clarity
    - Presence lift (500-1500 Hz) for warmth
    - Soft limiter to prevent harshness
    
    Args:
        audio_float: Audio as float32 normalized [-1, 1]
        sample_rate: Sample rate of audio
        
    Returns:
        Spectrally shaped audio
    """
    if len(audio_float) < 4:
        return audio_float
    
    # Design parametric EQ filters
    # High-end boost: 2-5 kHz (clarity)
    # Use a gentle shelf filter centered around 3.5 kHz
    nyquist = sample_rate / 2.0
    center_freq_high = 3500.0  # Hz
    gain_high = 2.0  # dB boost (subtle)
    Q_high = 0.7  # Quality factor (gentle)
    
    # Presence lift: 500-1500 Hz (warmth)
    center_freq_presence = 1000.0  # Hz
    gain_presence = 1.5  # dB boost (subtle)
    Q_presence = 0.8
    
    # Use frequency-domain filtering for precise spectral shaping
    try:
        # Convert to frequency domain
        fft = np.fft.rfft(audio_float)
        freqs = np.fft.rfftfreq(len(audio_float), 1.0 / sample_rate)
        
        # Calculate boost factors
        high_boost_factor = 10 ** (gain_high / 20.0)  # Convert dB to linear
        presence_boost = 10 ** (gain_presence / 20.0)
        
        # Apply high-end boost (2-5 kHz) - 30% of full boost for subtlety
        high_mask = (freqs >= 2000) & (freqs <= 5000)
        if np.any(high_mask):
            fft[high_mask] *= (1.0 + (high_boost_factor - 1.0) * 0.3)
        
        # Apply presence lift (500-1500 Hz) - 25% of full boost for subtlety
        presence_mask = (freqs >= 500) & (freqs <= 1500)
        if np.any(presence_mask):
            fft[presence_mask] *= (1.0 + (presence_boost - 1.0) * 0.25)
        
        # Convert back to time domain
        audio_float = np.fft.irfft(fft, n=len(audio_float))
        
    except Exception as e:
        logger.debug(f"Spectral shaping filter error: {e}, using simplified approach")
        # Simplified: gentle high-frequency emphasis using simple filter
        # First-order high-shelf approximation
        if len(audio_float) > 1:
            filtered = np.zeros_like(audio_float)
            filtered[0] = audio_float[0]
            for i in range(1, len(audio_float)):
                # Gentle high-frequency emphasis
                filtered[i] = audio_float[i] + 0.05 * (audio_float[i] - audio_float[i-1])
            audio_float = filtered
    
    return audio_float


def _apply_soft_limiter(audio_float: np.ndarray, threshold: float = 0.9) -> np.ndarray:
    """
    Apply soft limiter to prevent harshness and clipping.
    
    Uses smooth compression above threshold instead of hard clipping.
    
    Args:
        audio_float: Audio as float32 normalized [-1, 1]
        threshold: Limiting threshold (0.0-1.0)
        
    Returns:
        Soft-limited audio
    """
    # Soft knee compression above threshold
    ratio = 4.0  # Compression ratio
    knee_width = 0.1  # Soft knee width
    
    abs_audio = np.abs(audio_float)
    
    # Apply soft compression
    compressed = np.where(
        abs_audio > threshold,
        threshold + (abs_audio - threshold) / ratio,
        abs_audio
    )
    
    # Soft knee transition
    knee_start = threshold - knee_width
    knee_end = threshold + knee_width
    
    in_knee = (abs_audio > knee_start) & (abs_audio < knee_end)
    if np.any(in_knee):
        # Smooth transition in knee region
        knee_factor = (abs_audio[in_knee] - knee_start) / (2 * knee_width)
        compressed[in_knee] = knee_start + (compressed[in_knee] - knee_start) * knee_factor
    
    # Restore sign
    return np.sign(audio_float) * compressed


def _apply_dynamic_energy_enhancement(audio_float: np.ndarray, confidence: float) -> np.ndarray:
    """
    Apply dynamic energy enhancement based on RMS and confidence score.
    
    - If RMS < threshold → apply mild upward compression
    - If confidence < 50 → increase energy slightly
    - If confidence > 80 → keep natural
    
    Args:
        audio_float: Audio as float32 normalized [-1, 1]
        confidence: Current confidence score (0-100)
        
    Returns:
        Energy-enhanced audio
    """
    if len(audio_float) == 0:
        return audio_float
    
    # Calculate RMS
    rms = np.sqrt(np.mean(audio_float ** 2))
    rms_threshold = 0.1  # Below this, apply upward compression
    
    # Determine enhancement factor based on RMS and confidence
    enhancement_factor = 1.0
    
    if rms < rms_threshold:
        # Quiet speech: apply upward compression
        # Boost quiet parts more than loud parts
        compression_ratio = 1.5  # Mild upward compression
        enhancement_factor = 1.0 + (rms_threshold - rms) / rms_threshold * (compression_ratio - 1.0)
    
    # Confidence-based adjustment
    if confidence < 50:
        # Low confidence: increase energy slightly
        confidence_boost = 1.0 + (50.0 - confidence) / 50.0 * 0.15  # Up to 15% boost
        enhancement_factor *= confidence_boost
    elif confidence > 80:
        # High confidence: keep natural (minimal adjustment)
        enhancement_factor *= 1.0  # No additional boost
    
    # Apply enhancement with smooth gain ramping
    enhanced = audio_float * enhancement_factor
    
    # Prevent excessive amplification
    max_gain = 2.0  # Maximum 2x gain
    if enhancement_factor > max_gain:
        enhanced = audio_float * max_gain
    
    return enhanced


def _apply_micro_pitch_enhancement(audio_float: np.ndarray, sample_rate: int, confidence: float) -> np.ndarray:
    """
    Apply subtle micro-pitch enhancement for low-confidence speech.
    
    Adds +1-3% pitch lift when confidence is low, zero when confidence is normal/high.
    Uses time-domain pitch shifting via resampling.
    
    Args:
        audio_float: Audio as float32 normalized [-1, 1]
        sample_rate: Sample rate of audio
        confidence: Current confidence score (0-100)
        
    Returns:
        Pitch-enhanced audio (same length)
    """
    if len(audio_float) < 2 or confidence >= 50:
        # No pitch adjustment for normal/high confidence
        return audio_float
    
    # Calculate pitch lift amount (1-3% based on confidence)
    # Lower confidence = more pitch lift
    pitch_lift_percent = (50.0 - confidence) / 50.0 * 0.03  # 0% to 3%
    pitch_lift_percent = max(0.01, min(0.03, pitch_lift_percent))  # Clamp to 1-3%
    
    if pitch_lift_percent < 0.005:  # Too small to matter
        return audio_float
    
    try:
        # Time-domain pitch shifting via resampling
        # To raise pitch by X%, we resample at (1 + X) rate, then decimate back
        target_samples = int(len(audio_float) / (1.0 + pitch_lift_percent))
        
        if target_samples < 2:
            return audio_float
        
        # Resample to achieve pitch shift
        indices_original = np.arange(len(audio_float))
        indices_target = np.linspace(0, len(audio_float) - 1, target_samples)
        
        # Interpolate
        pitch_shifted = np.interp(indices_target, indices_original, audio_float)
        
        # Resample back to original length (maintains pitch shift)
        indices_final = np.linspace(0, len(pitch_shifted) - 1, len(audio_float))
        final_audio = np.interp(indices_final, np.arange(len(pitch_shifted)), pitch_shifted)
        
        return final_audio.astype(np.float32)
        
    except Exception as e:
        logger.debug(f"Micro-pitch enhancement error: {e}, returning original")
        return audio_float


def boost_confidence(frame: AudioFrame, confidence: Optional[float] = None) -> AudioFrame:
    """
    Apply voice confidence boosting to audio frame.
    
    Enhances clarity, presence, and perceived confidence without altering identity.
    Uses psychoacoustic principles to make voice sound more authoritative and clear.
    
    Processing steps:
    1. Spectral shaping (EQ: high-end boost + presence lift)
    2. Dynamic energy enhancement (based on RMS and confidence)
    3. Micro-pitch enhancement (subtle pitch lift for low confidence)
    4. Soft limiter (prevents harshness)
    
    Args:
        frame: Input audio frame (PCM int16)
        confidence: Current confidence score (0-100). If None, uses global value.
        
    Returns:
        Confidence-boosted audio frame (PCM int16, same length)
    """
    global _current_confidence
    
    if len(frame.pcm_data) == 0:
        return frame
    
    # Use provided confidence or global value
    if confidence is None:
        confidence = _current_confidence
    
    try:
        # Convert int16 to float32 normalized [-1, 1]
        audio_float = frame.pcm_data.astype(np.float32) / np.iinfo(np.int16).max
        
        # Step 1: Spectral shaping (micro-EQ)
        audio_float = _apply_spectral_shaping(audio_float, frame.sample_rate)
        
        # Step 2: Dynamic energy enhancement
        audio_float = _apply_dynamic_energy_enhancement(audio_float, confidence)
        
        # Step 3: Micro-pitch enhancement (subtle, only for low confidence)
        audio_float = _apply_micro_pitch_enhancement(audio_float, frame.sample_rate, confidence)
        
        # Step 4: Soft limiter (prevent harshness)
        audio_float = _apply_soft_limiter(audio_float, threshold=0.9)
        
        # Convert back to int16 PCM
        boosted_pcm = (np.clip(audio_float, -1.0, 1.0) * np.iinfo(np.int16).max).astype(np.int16)
        
        # Ensure same length
        if len(boosted_pcm) != len(frame.pcm_data):
            if len(boosted_pcm) > len(frame.pcm_data):
                boosted_pcm = boosted_pcm[:len(frame.pcm_data)]
            else:
                boosted_pcm = np.pad(boosted_pcm, (0, len(frame.pcm_data) - len(boosted_pcm)), mode='constant')
        
        return AudioFrame(
            pcm_data=boosted_pcm,
            sample_rate=frame.sample_rate,
            timestamp=frame.timestamp,
            stream_id=frame.stream_id
        )
        
    except Exception as e:
        logger.error(f"Confidence boost processing failed for stream {frame.stream_id}: {e}", exc_info=True)
        # Fallback to original frame
        return frame

