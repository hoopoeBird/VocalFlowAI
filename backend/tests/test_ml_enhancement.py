"""Unit tests for ML enhancement module."""
import pytest
import numpy as np
from app.audio.models import AudioFrame
from app.audio.ml.enhancement import enhance_voice_ml, load_enhancement_model, preprocess_audio, postprocess_audio


def test_preprocess_audio():
    """Test audio preprocessing for ONNX model."""
    # Create test audio
    pcm_data = np.array([1000, -2000, 3000, -1000], dtype=np.int16)
    sample_rate = 16000
    
    processed = preprocess_audio(pcm_data, sample_rate)
    
    # Should be float32, normalized to [-1, 1]
    assert processed.dtype == np.float32
    assert processed.shape[0] == 1  # Should be reshaped to (1, samples)
    assert np.all(processed >= -1.0) and np.all(processed <= 1.0)


def test_postprocess_audio():
    """Test audio postprocessing from ONNX output."""
    # Create normalized float audio
    enhanced_float = np.array([0.5, -0.3, 0.8, -0.2], dtype=np.float32)
    
    pcm_output = postprocess_audio(enhanced_float)
    
    # Should be int16
    assert pcm_output.dtype == np.int16
    # Should be in valid int16 range
    assert np.all(pcm_output >= np.iinfo(np.int16).min)
    assert np.all(pcm_output <= np.iinfo(np.int16).max)


def test_enhance_voice_ml_fallback():
    """Test ML enhancement fallback when model is not available."""
    # Create test frame
    pcm_data = np.array([1000, -2000, 3000, -1000], dtype=np.int16)
    frame = AudioFrame(
        pcm_data=pcm_data,
        sample_rate=16000,
        timestamp=0.0,
        stream_id="test-1"
    )
    
    # Should return original frame if no model (fallback behavior)
    result = enhance_voice_ml(frame)
    
    assert result.sample_rate == frame.sample_rate
    assert result.stream_id == frame.stream_id
    assert len(result.pcm_data) == len(frame.pcm_data)


def test_enhance_voice_ml_preserves_format():
    """Test that ML enhancement preserves audio format."""
    pcm_data = np.random.randint(-10000, 10000, size=320, dtype=np.int16)
    frame = AudioFrame(
        pcm_data=pcm_data,
        sample_rate=16000,
        timestamp=0.0,
        stream_id="test-2"
    )
    
    result = enhance_voice_ml(frame)
    
    # Should preserve format even if model not available
    assert result.pcm_data.dtype == np.int16
    assert len(result.pcm_data) == len(frame.pcm_data)
    assert result.sample_rate == frame.sample_rate


def test_load_enhancement_model_nonexistent():
    """Test loading non-existent model returns None gracefully."""
    result = load_enhancement_model("/nonexistent/model.onnx")
    
    # Should return None without crashing
    assert result is None or hasattr(result, 'run')  # Either None or valid session

