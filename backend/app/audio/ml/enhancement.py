"""ML-based voice enhancement using ONNX Runtime."""
import numpy as np
from typing import Optional
from app.audio.models import AudioFrame
from app.core.config import settings
from app.core.logging import logger

# Global ONNX session (initialized once, reused for all frames)
_onnx_session: Optional[object] = None
_model_loaded = False


def load_enhancement_model(model_path: Optional[str] = None) -> Optional[object]:
    """
    Load ONNX enhancement model using ONNX Runtime.
    
    Phase 3: Real ONNX Runtime integration.
    Model is loaded once globally and reused for all inference calls.
    
    Args:
        model_path: Path to ONNX model file (if None, uses config value)
        
    Returns:
        ONNX InferenceSession or None if model not found/error
    """
    global _onnx_session, _model_loaded
    
    if _model_loaded and _onnx_session is not None:
        return _onnx_session
    
    if model_path is None:
        model_path = settings.onnx_model_path
    
    if not model_path:
        logger.debug("No ONNX model path configured, ML enhancement disabled")
        return None
    
    try:
        import onnxruntime as ort
        
        # Create ONNX Runtime session
        # Use CPU provider for low latency (can add GPU provider if available)
        providers = ['CPUExecutionProvider']
        
        # Session options for low latency
        sess_options = ort.SessionOptions()
        sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_BASIC
        sess_options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        sess_options.inter_op_num_threads = 1  # Single thread for low latency
        sess_options.intra_op_num_threads = 1
        
        _onnx_session = ort.InferenceSession(
            model_path,
            sess_options=sess_options,
            providers=providers
        )
        
        _model_loaded = True
        logger.info("ONNX model loaded successfully")
        logger.info(f"  Model path: {model_path}")
        logger.info(f"  Input names: {[inp.name for inp in _onnx_session.get_inputs()]}")
        logger.info(f"  Input shapes: {[inp.shape for inp in _onnx_session.get_inputs()]}")
        logger.info(f"  Output names: {[out.name for out in _onnx_session.get_outputs()]}")
        logger.info(f"  Output shapes: {[out.shape for out in _onnx_session.get_outputs()]}")
        
        return _onnx_session
        
    except FileNotFoundError:
        logger.warning(f"ONNX model file not found: {model_path}, ML enhancement disabled")
        _model_loaded = True  # Mark as loaded to avoid repeated attempts
        return None
    except ImportError:
        logger.warning("onnxruntime not installed, ML enhancement disabled. Install with: pip install onnxruntime")
        _model_loaded = True
        return None
    except Exception as e:
        logger.error(f"Error loading ONNX model: {e}", exc_info=True)
        _model_loaded = True
        return None


def preprocess_audio(pcm_data: np.ndarray, sample_rate: int, expected_shape: Optional[tuple] = None) -> np.ndarray:
    """
    Preprocess audio for ONNX model input.
    
    Converts int16 PCM to float32 and normalizes to [-1, 1] range.
    Handles arbitrary frame sizes and reshapes according to model requirements.
    
    Args:
        pcm_data: Input PCM audio (int16)
        sample_rate: Sample rate of the audio
        expected_shape: Expected input shape from model (if known)
        
    Returns:
        Preprocessed audio array (float32, normalized, properly shaped)
    """
    # Convert int16 to float32 and normalize to [-1, 1]
    audio_float = pcm_data.astype(np.float32) / np.iinfo(np.int16).max
    
    # Handle different model input shape requirements
    if expected_shape is not None:
        # Reshape to match expected shape
        total_samples = np.prod(audio_float.shape)
        expected_total = np.prod(expected_shape)
        
        if total_samples != expected_total:
            # Pad or truncate to match expected size
            if total_samples < expected_total:
                audio_float = np.pad(audio_float, (0, expected_total - total_samples), mode='constant')
            else:
                audio_float = audio_float[:expected_total]
        
        audio_float = audio_float.reshape(expected_shape)
    else:
        # Default: ensure at least 2D for batch dimension
        # Most models expect (batch, samples) or (batch, channels, samples)
        if len(audio_float.shape) == 1:
            audio_float = audio_float.reshape(1, -1)  # (1, samples)
    
    return audio_float


def postprocess_audio(enhanced_audio: np.ndarray) -> np.ndarray:
    """
    Postprocess ONNX model output back to PCM int16.
    
    Args:
        enhanced_audio: Model output (float32, normalized)
        
    Returns:
        PCM int16 audio array
    """
    # Flatten if needed
    if len(enhanced_audio.shape) > 1:
        enhanced_audio = enhanced_audio.flatten()
    
    # Clip to valid range and convert to int16
    enhanced_audio = np.clip(enhanced_audio, -1.0, 1.0)
    pcm_int16 = (enhanced_audio * np.iinfo(np.int16).max).astype(np.int16)
    
    return pcm_int16


def enhance_voice_ml(frame: AudioFrame) -> AudioFrame:
    """
    Apply ML-based voice enhancement using ONNX Runtime.
    
    Real ONNX Runtime inference with automatic fallback to original audio.
    Handles arbitrary frame sizes and model input shapes.
    Low latency target: <10ms per inference.
    
    Args:
        frame: Input audio frame (PCM int16)
        
    Returns:
        Enhanced audio frame (or original if ML fails/disabled)
    """
    global _onnx_session
    
    # Load model if not already loaded
    if _onnx_session is None and not _model_loaded:
        _onnx_session = load_enhancement_model()
    
    # If no model available, return original frame (silent fallback)
    if _onnx_session is None:
        return frame
    
    try:
        import time
        inference_start = time.time()
        
        # Get model input/output specifications
        model_input = _onnx_session.get_inputs()[0]
        model_output = _onnx_session.get_outputs()[0]
        input_name = model_input.name
        output_name = model_output.name
        
        # Get expected input shape (handle dynamic dimensions)
        expected_shape = None
        if model_input.shape:
            # Replace dynamic dimensions (-1, None) with actual frame size
            expected_shape = list(model_input.shape)
            for i, dim in enumerate(expected_shape):
                if dim in (-1, None) or (isinstance(dim, str) and '?' in str(dim)):
                    # Use actual frame length for dynamic dimension
                    expected_shape[i] = len(frame.pcm_data)
                elif isinstance(dim, int) and dim > 0:
                    expected_shape[i] = dim
            expected_shape = tuple(expected_shape)
        
        # Preprocess audio: int16 → float32 normalized → model shape
        input_audio = preprocess_audio(frame.pcm_data, frame.sample_rate, expected_shape)
        
        # Run ONNX inference
        outputs = _onnx_session.run(
            [output_name],
            {input_name: input_audio}
        )
        
        # Postprocess output: float32 normalized → int16 PCM
        enhanced_pcm = postprocess_audio(outputs[0])
        
        # Ensure output length matches input (handle model output size variations)
        original_length = len(frame.pcm_data)
        if len(enhanced_pcm) != original_length:
            # Resize to match input exactly
            if len(enhanced_pcm) > original_length:
                enhanced_pcm = enhanced_pcm[:original_length]
            else:
                # Pad with zeros if output is shorter
                enhanced_pcm = np.pad(
                    enhanced_pcm,
                    (0, original_length - len(enhanced_pcm)),
                    mode='constant'
                )
        
        # Check inference latency
        inference_time = (time.time() - inference_start) * 1000  # ms
        if inference_time > 10.0:
            logger.warning(f"ML inference took {inference_time:.2f}ms (target: <10ms)")
        else:
            logger.debug(f"ML inference: {inference_time:.2f}ms")
        
        return AudioFrame(
            pcm_data=enhanced_pcm,
            sample_rate=frame.sample_rate,
            timestamp=frame.timestamp,
            stream_id=frame.stream_id
        )
        
    except Exception as e:
        logger.error("ONNX inference failed — using fallback")
        logger.debug(f"ONNX inference error details: {e}", exc_info=True)
        # Automatic fallback: return original frame unchanged
        return frame
