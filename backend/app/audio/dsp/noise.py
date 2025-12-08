"""Noise reduction using spectral subtraction and adaptive filtering."""
import numpy as np
from app.audio.models import AudioFrame
from app.core.logging import logger

# Global noise profile for adaptive noise estimation (per-stream would be better, but keeping it simple)
_noise_profile = None
_noise_profile_frames = 0
_MAX_NOISE_PROFILE_FRAMES = 10  # Estimate noise from first 10 frames


def reduce_noise(frame: AudioFrame, noise_floor_db: float = -35.0, reduction_factor: float = 0.5) -> AudioFrame:
    """
    Apply noise reduction using spectral subtraction with adaptive noise estimation.
    
    Phase 2 implementation: Real spectral subtraction with moving average noise profile.
    Future Phase 3: Replace with ONNX-based RNNoise or similar ML denoiser.
    
    Args:
        frame: Input audio frame
        noise_floor_db: Noise floor threshold in dB
        reduction_factor: How aggressively to reduce noise (0.0-1.0)
        
    Returns:
        New AudioFrame with noise reduction applied
    """
    global _noise_profile, _noise_profile_frames
    
    if len(frame.pcm_data) == 0:
        return frame
    
    # Convert to float for processing (-1.0 to 1.0 range)
    audio_float = frame.pcm_data.astype(np.float32) / np.iinfo(np.int16).max
    
    # Step 1: High-pass filter to remove DC and very low frequency noise (< 80 Hz)
    if len(audio_float) > 2:
        # First-order high-pass filter (removes DC offset and rumble)
        alpha = 0.98  # Higher alpha = stronger filtering
        filtered = np.zeros_like(audio_float)
        filtered[0] = audio_float[0]
        for i in range(1, len(audio_float)):
            filtered[i] = alpha * (filtered[i-1] + audio_float[i] - audio_float[i-1])
        audio_float = filtered
    
    # Step 2: Spectral subtraction (simplified - using frequency-domain-like approach)
    # Use FFT for spectral analysis (even for short frames)
    fft_size = 256  # Small FFT for low latency
    if len(audio_float) >= fft_size:
        # Pad or truncate to fft_size
        if len(audio_float) > fft_size:
            audio_segment = audio_float[:fft_size]
        else:
            audio_segment = np.pad(audio_float, (0, fft_size - len(audio_float)), mode='constant')
        
        # Compute FFT
        fft = np.fft.rfft(audio_segment)
        magnitude = np.abs(fft)
        phase = np.angle(fft)
        
        # Estimate noise profile from quiet frames (first few frames)
        if _noise_profile is None or _noise_profile_frames < _MAX_NOISE_PROFILE_FRAMES:
            rms = np.sqrt(np.mean(audio_float ** 2))
            rms_db = 20 * np.log10(rms + 1e-10)
            
            if rms_db < noise_floor_db:
                # This is likely noise, update noise profile
                if _noise_profile is None:
                    _noise_profile = magnitude.copy()
                else:
                    # Moving average
                    _noise_profile = 0.7 * _noise_profile + 0.3 * magnitude
                _noise_profile_frames += 1
        
        # Spectral subtraction: subtract estimated noise from magnitude
        if _noise_profile is not None:
            # Subtract noise magnitude, with over-subtraction factor
            noise_magnitude = _noise_profile * reduction_factor
            clean_magnitude = np.maximum(magnitude - noise_magnitude, magnitude * 0.1)  # Floor at 10%
            
            # Reconstruct signal
            clean_fft = clean_magnitude * np.exp(1j * phase)
            audio_segment = np.fft.irfft(clean_fft, n=fft_size)
            
            # Restore original length
            if len(audio_float) <= fft_size:
                audio_float = audio_segment[:len(frame.pcm_data)].astype(np.float32)
            else:
                audio_float = np.concatenate([audio_segment, audio_float[fft_size:]])
    
    # Step 3: Adaptive gating - further attenuate very quiet segments
    rms = np.sqrt(np.mean(audio_float ** 2))
    rms_db = 20 * np.log10(rms + 1e-10)
    
    if rms_db < noise_floor_db:
        # Additional attenuation for very quiet parts
        gate_threshold = noise_floor_db - 10  # 10 dB below noise floor
        if rms_db < gate_threshold:
            attenuation = 10 ** ((rms_db - gate_threshold) / 20)
            audio_float = audio_float * max(attenuation, 0.1)  # Minimum 10% to avoid complete silence
    
    # Convert back to int16
    denoised = (np.clip(audio_float, -1.0, 1.0) * np.iinfo(np.int16).max).astype(np.int16)
    
    return AudioFrame(
        pcm_data=denoised,
        sample_rate=frame.sample_rate,
        timestamp=frame.timestamp,
        stream_id=frame.stream_id
    )

