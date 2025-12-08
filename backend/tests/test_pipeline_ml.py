"""Unit tests for pipeline with ML integration."""
import pytest
import numpy as np
from app.audio.models import AudioFrame
from app.audio.pipeline import process_audio_frame
from app.core.config import settings


def test_pipeline_without_ml():
    """Test pipeline works when ML is disabled."""
    # Disable ML
    original_ml_setting = settings.enable_ml_enhancement
    settings.enable_ml_enhancement = False
    
    try:
        pcm_data = np.random.randint(-10000, 10000, size=320, dtype=np.int16)
        frame = AudioFrame(
            pcm_data=pcm_data,
            sample_rate=16000,
            timestamp=0.0,
            stream_id="test-no-ml"
        )
        
        result = process_audio_frame(frame)
        
        # Should process successfully
        assert result.pcm_data.dtype == np.int16
        assert len(result.pcm_data) == len(frame.pcm_data)
        assert result.stream_id == frame.stream_id
        
    finally:
        # Restore original setting
        settings.enable_ml_enhancement = original_ml_setting


def test_pipeline_with_ml_disabled_fallback():
    """Test pipeline gracefully handles ML when model not available."""
    # Enable ML but model won't be available (fallback)
    original_ml_setting = settings.enable_ml_enhancement
    original_model_path = settings.onnx_model_path
    
    settings.enable_ml_enhancement = True
    settings.onnx_model_path = "/nonexistent/model.onnx"
    
    try:
        pcm_data = np.random.randint(-10000, 10000, size=320, dtype=np.int16)
        frame = AudioFrame(
            pcm_data=pcm_data,
            sample_rate=16000,
            timestamp=0.0,
            stream_id="test-ml-fallback"
        )
        
        # Should not crash, should fallback to DSP-only
        result = process_audio_frame(frame)
        
        assert result.pcm_data.dtype == np.int16
        assert len(result.pcm_data) == len(frame.pcm_data)
        
    finally:
        # Restore original settings
        settings.enable_ml_enhancement = original_ml_setting
        settings.onnx_model_path = original_model_path


def test_pipeline_preserves_format():
    """Test that pipeline always preserves audio format."""
    pcm_data = np.random.randint(-10000, 10000, size=320, dtype=np.int16)
    frame = AudioFrame(
        pcm_data=pcm_data,
        sample_rate=16000,
        timestamp=0.0,
        stream_id="test-format"
    )
    
    result = process_audio_frame(frame)
    
    # Format must be preserved
    assert result.pcm_data.dtype == np.int16
    assert len(result.pcm_data) == len(frame.pcm_data)
    assert result.sample_rate == frame.sample_rate
    assert result.stream_id == frame.stream_id

