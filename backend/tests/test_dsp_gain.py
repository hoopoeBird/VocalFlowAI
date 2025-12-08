"""Unit tests for gain normalization."""
import pytest
import numpy as np
from app.audio.models import AudioFrame
from app.audio.dsp.gain import normalize_gain


def test_normalize_gain_quiet_audio():
    """Test that quiet audio gets amplified."""
    # Create quiet audio (low amplitude)
    quiet_audio = np.array([100, 200, -150, 50], dtype=np.int16)
    frame = AudioFrame(
        pcm_data=quiet_audio,
        sample_rate=16000,
        timestamp=0.0,
        stream_id="test-1"
    )
    
    result = normalize_gain(frame, target_rms=5000.0)
    
    # Result should have higher amplitude
    assert np.abs(result.pcm_data).max() > np.abs(quiet_audio).max()
    assert result.sample_rate == frame.sample_rate
    assert result.stream_id == frame.stream_id


def test_normalize_gain_loud_audio():
    """Test that very loud audio doesn't clip."""
    # Create loud audio (high amplitude)
    loud_audio = np.array([20000, 25000, -22000, 18000], dtype=np.int16)
    frame = AudioFrame(
        pcm_data=loud_audio,
        sample_rate=16000,
        timestamp=0.0,
        stream_id="test-2"
    )
    
    result = normalize_gain(frame, target_rms=5000.0)
    
    # Result should not exceed int16 limits
    assert np.abs(result.pcm_data).max() <= np.iinfo(np.int16).max
    assert result.sample_rate == frame.sample_rate


def test_normalize_gain_empty_frame():
    """Test that empty frame is handled gracefully."""
    empty_audio = np.array([], dtype=np.int16)
    frame = AudioFrame(
        pcm_data=empty_audio,
        sample_rate=16000,
        timestamp=0.0,
        stream_id="test-3"
    )
    
    result = normalize_gain(frame)
    
    # Should return frame unchanged
    assert len(result.pcm_data) == 0
    assert result.stream_id == frame.stream_id


def test_normalize_gain_zero_audio():
    """Test that zero/silent audio is handled."""
    zero_audio = np.array([0, 0, 0, 0], dtype=np.int16)
    frame = AudioFrame(
        pcm_data=zero_audio,
        sample_rate=16000,
        timestamp=0.0,
        stream_id="test-4"
    )
    
    result = normalize_gain(frame)
    
    # Should return frame unchanged (RMS too low)
    assert np.array_equal(result.pcm_data, zero_audio)

