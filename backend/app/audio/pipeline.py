"""Main audio processing pipeline orchestrator."""
import time
from typing import Optional
from app.audio.models import AudioFrame
from app.audio.dsp.gain import normalize_gain
from app.audio.dsp.noise import reduce_noise
from app.audio.dsp.rnnoise import reduce_noise_rnnoise
from app.audio.dsp.confidence_boost import boost_confidence, set_confidence
from app.audio.dsp.pitch import adjust_energy
from app.audio.ml.enhancement import enhance_voice_ml
from app.core.config import settings
from app.core.logging import logger

from app.audio.models import AudioFrame, StreamState   # NEW
from app.audio.dsp.vad import vad_speech_ratio         # NEW


def process_audio_frame(frame: AudioFrame, confidence: Optional[float] = None,stream_state: Optional[StreamState] = None ) -> AudioFrame:
    """
    Process a single audio frame through the DSP and ML pipeline.
    
    Phase 2: Synchronous, low-latency processing pipeline.
    Target latency: < 20ms per frame.
    
    The pipeline applies processing steps in order:
    1. RNNoise noise reduction (if enabled, Phase 3 - advanced denoising)
    2. Basic noise reduction (if RNNoise disabled, fallback DSP denoising)
    3. Gain normalization (AGC for consistent loudness)
    4. Confidence boost (if enabled, Phase 3 - psychoacoustic enhancement)
    5. Pitch/energy adjustment (optional, subtle enhancement)
    6. ONNX ML enhancement (Phase 3 - real-time inference)
    
    Args:
        frame: Input audio frame
        
    Returns:
        Processed audio frame with same format (PCM int16, same length)
    """
    start_time = time.time()
    processed = frame
    
    try:
        # Step 1: RNNoise noise reduction (Phase 3 - advanced denoising)
        if settings.enable_rnnoise:
            processed = reduce_noise_rnnoise(processed)
        # Step 1b: Basic noise reduction (fallback if RNNoise disabled)
        elif settings.enable_noise_reduction:
            processed = reduce_noise(processed)
        
        # Step 2: Gain normalization (AGC for consistent loudness)
        if settings.enable_gain_normalization:
            processed = normalize_gain(processed)
        
        # Step 3: Confidence boost (Phase 3 - psychoacoustic enhancement)
        # Uses confidence score for adaptive enhancement
        if settings.enable_confidence_boost:
            # boost_confidence() has built-in fallback
            # Pass confidence if available, otherwise uses global state
            processed = boost_confidence(processed, confidence=confidence)
        
        # Step 4: Pitch/energy adjustment (optional, subtle)
        if settings.enable_pitch_adjustment:
            processed = adjust_energy(processed, energy_boost=1.05)
        
        # Step 5: ONNX ML enhancement (Phase 3) - Apply after DSP cleaning
        # ML works on cleaned, normalized audio for optimal results
        if settings.enable_ml_enhancement:
            # enhance_voice_ml() has built-in fallback, so no try/except needed here
            # It will return original frame if inference fails
            processed = enhance_voice_ml(processed)
        
        # Verify output format matches input
        if len(processed.pcm_data) != len(frame.pcm_data):
            logger.warning(f"Frame length mismatch: {len(frame.pcm_data)} -> {len(processed.pcm_data)}")
            # Return original if length changed (shouldn't happen)
            return frame
        
        # Log processing time if it exceeds threshold
        processing_time = (time.time() - start_time) * 1000  # Convert to ms
        if processing_time > settings.processing_timeout_ms:
            logger.warning(f"Frame processing took {processing_time:.2f}ms (target: {settings.processing_timeout_ms}ms)")
        
    except Exception as e:
        logger.error(f"Error processing frame for stream {frame.stream_id}: {e}", exc_info=True)
        # Return original frame on error to maintain stream continuity
        return frame
    
    return processed

