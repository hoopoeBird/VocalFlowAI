"""RNNoise-based noise reduction using python-rnnoise or fallback implementation."""
import numpy as np
from typing import Optional
from app.audio.models import AudioFrame
from app.core.config import settings
from app.core.logging import logger

# Global RNNoise processor (initialized once, reused for all frames)
_rnnoise_processor: Optional[object] = None
_rnnoise_available = False
_rnnoise_initialized = False

# RNNoise frame size: 480 samples at 48kHz = 10ms
# For 16kHz, we need to handle frame size conversion
RNNOISE_FRAME_SIZE_48K = 480  # RNNoise native frame size
RNNOISE_SAMPLE_RATE = 48000   # RNNoise native sample rate


def _init_rnnoise() -> bool:
    """
    Initialize RNNoise processor.
    
    Tries multiple RNNoise package options:
    1. python-rnnoise package
    2. rnnoise-python package
    3. Direct C library bindings (if available)
    
    Falls back gracefully if none available.
    
    Returns:
        True if RNNoise is available and initialized, False otherwise
    """
    global _rnnoise_processor, _rnnoise_available, _rnnoise_initialized
    
    if _rnnoise_initialized:
        return _rnnoise_available
    
    _rnnoise_initialized = True
    
    # Try option 1: python-rnnoise
    try:
        import rnnoise
        _rnnoise_processor = rnnoise.RNNoise()
        _rnnoise_available = True
        logger.info("RNNoise loaded successfully (using python-rnnoise)")
        return True
    except ImportError:
        pass
    except Exception as e:
        logger.debug(f"python-rnnoise import failed: {e}")
    
    # Try option 2: rnnoise-python (alternative package name)
    try:
        from rnnoise_python import RNNoise
        _rnnoise_processor = RNNoise()
        _rnnoise_available = True
        logger.info("RNNoise loaded successfully (using rnnoise-python)")
        return True
    except ImportError:
        pass
    except Exception as e:
        logger.debug(f"rnnoise-python import failed: {e}")
    
    # Try option 3: Direct C library via ctypes (if library available)
    try:
        import ctypes
        import os
        
        # Common library paths
        lib_paths = [
            '/usr/lib/librnnoise.so',
            '/usr/local/lib/librnnoise.so',
            'librnnoise.so',
            'librnnoise.dylib',  # macOS
        ]
        
        rnnoise_lib = None
        for lib_path in lib_paths:
            if os.path.exists(lib_path) or lib_path.startswith('lib'):
                try:
                    rnnoise_lib = ctypes.CDLL(lib_path)
                    break
                except OSError:
                    continue
        
        if rnnoise_lib:
            # Define function signatures (simplified - would need full API)
            # This is a placeholder for direct C library integration
            logger.debug("RNNoise C library found but full integration not implemented")
            _rnnoise_available = False
            return False
    except Exception as e:
        logger.debug(f"RNNoise C library check failed: {e}")
    
    # No RNNoise available - use fallback
    logger.info("RNNoise not available, will use fallback noise reduction")
    _rnnoise_available = False
    return False


def _resample_16k_to_48k(audio_16k: np.ndarray) -> np.ndarray:
    """
    Resample audio from 16kHz to 48kHz using linear interpolation.
    
    Simple upsampling for RNNoise (which expects 48kHz).
    
    Args:
        audio_16k: Audio at 16kHz
        
    Returns:
        Audio at 48kHz
    """
    # Upsample by factor of 3 (16k * 3 = 48k)
    # Simple linear interpolation
    indices_16k = np.arange(len(audio_16k))
    indices_48k = np.linspace(0, len(audio_16k) - 1, len(audio_16k) * 3)
    audio_48k = np.interp(indices_48k, indices_16k, audio_16k)
    return audio_48k.astype(np.float32)


def _resample_48k_to_16k(audio_48k: np.ndarray) -> np.ndarray:
    """
    Resample audio from 48kHz to 16kHz using decimation.
    
    Args:
        audio_48k: Audio at 48kHz
        
    Returns:
        Audio at 16kHz
    """
    # Downsample by factor of 3 (48k / 3 = 16k)
    # Simple decimation (take every 3rd sample)
    audio_16k = audio_48k[::3]
    return audio_16k.astype(np.float32)


def _process_with_rnnoise(audio_float: np.ndarray, sample_rate: int) -> np.ndarray:
    """
    Process audio with RNNoise library.
    
    Args:
        audio_float: Audio as float32 normalized [-1, 1]
        sample_rate: Sample rate of input audio
        
    Returns:
        Denoised audio as float32 normalized [-1, 1]
    """
    global _rnnoise_processor
    
    if _rnnoise_processor is None:
        return audio_float
    
    try:
        # RNNoise expects 48kHz, so resample if needed
        if sample_rate != RNNOISE_SAMPLE_RATE:
            # Resample to 48kHz
            audio_48k = _resample_16k_to_48k(audio_float)
        else:
            audio_48k = audio_float
        
        # Process in RNNoise frame chunks (480 samples at 48kHz)
        denoised_48k = np.zeros_like(audio_48k)
        
        for i in range(0, len(audio_48k), RNNOISE_FRAME_SIZE_48K):
            chunk = audio_48k[i:i + RNNOISE_FRAME_SIZE_48K]
            
            # Pad if last chunk is shorter
            if len(chunk) < RNNOISE_FRAME_SIZE_48K:
                chunk = np.pad(chunk, (0, RNNOISE_FRAME_SIZE_48K - len(chunk)), mode='constant')
            
            # Process with RNNoise
            denoised_chunk = _rnnoise_processor.process(chunk)
            
            # Copy result (handle length mismatch)
            end_idx = min(i + RNNOISE_FRAME_SIZE_48K, len(denoised_48k))
            denoised_48k[i:end_idx] = denoised_chunk[:end_idx - i]
        
        # Resample back to original sample rate
        if sample_rate != RNNOISE_SAMPLE_RATE:
            denoised = _resample_48k_to_16k(denoised_48k)
        else:
            denoised = denoised_48k
        
        # Ensure same length as input
        if len(denoised) != len(audio_float):
            if len(denoised) > len(audio_float):
                denoised = denoised[:len(audio_float)]
            else:
                denoised = np.pad(denoised, (0, len(audio_float) - len(denoised)), mode='constant')
        
        return denoised
        
    except Exception as e:
        logger.error(f"RNNoise processing error: {e}", exc_info=True)
        return audio_float  # Return original on error


def reduce_noise_rnnoise(frame: AudioFrame) -> AudioFrame:
    """
    Apply RNNoise-based noise reduction to audio frame.
    
    Uses python-rnnoise if available, otherwise falls back to original frame.
    Handles sample rate conversion (16kHz → 48kHz → 16kHz) if needed.
    
    Args:
        frame: Input audio frame (PCM int16)
        
    Returns:
        Denoised audio frame (PCM int16, same length)
    """
    global _rnnoise_processor, _rnnoise_available
    
    # Initialize RNNoise if not done
    if not _rnnoise_initialized:
        _init_rnnoise()
    
    # If RNNoise not available, return original frame (silent fallback)
    if not _rnnoise_available or _rnnoise_processor is None:
        return frame
    
    if len(frame.pcm_data) == 0:
        return frame
    
    try:
        # Convert int16 to float32 normalized [-1, 1]
        audio_float = frame.pcm_data.astype(np.float32) / np.iinfo(np.int16).max
        
        # Process with RNNoise
        denoised_float = _process_with_rnnoise(audio_float, frame.sample_rate)
        
        # Convert back to int16 PCM
        denoised_pcm = (np.clip(denoised_float, -1.0, 1.0) * np.iinfo(np.int16).max).astype(np.int16)
        
        # Ensure same length
        if len(denoised_pcm) != len(frame.pcm_data):
            if len(denoised_pcm) > len(frame.pcm_data):
                denoised_pcm = denoised_pcm[:len(frame.pcm_data)]
            else:
                denoised_pcm = np.pad(denoised_pcm, (0, len(frame.pcm_data) - len(denoised_pcm)), mode='constant')
        
        return AudioFrame(
            pcm_data=denoised_pcm,
            sample_rate=frame.sample_rate,
            timestamp=frame.timestamp,
            stream_id=frame.stream_id
        )
        
    except Exception as e:
        logger.error(f"RNNoise processing failed for stream {frame.stream_id}: {e}", exc_info=True)
        # Fallback to original frame
        return frame

