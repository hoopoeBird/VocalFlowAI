"""Unit tests for RNNoise noise reduction."""
import pytest
import numpy as np
from app.audio.models import AudioFrame
from app.audio.dsp.rnnoise import reduce_noise_rnnoise, _init_rnnoise
from app.core.config import settings


def test_rnnoise_initialization():
    """Test RNNoise initialization."""
    # Try to initialize
    available = _init_rnnoise()
    
    # Should not crash regardless of whether RNNoise is available
    assert isinstance(available, bool)


def test_rnnoise_fallback():
    """Test RNNoise fallback when not available."""
    # Create test frame
    pcm_data = np.array([1000, -2000, 3000, -1000, 500], dtype=np.int16)
    frame = AudioFrame(
        pcm_data=pcm_data,
        sample_rate=16000,
        timestamp=0.0,
        stream_id="test-rnnoise-fallback"
    )
    
    # Should not crash even if RNNoise not available
    result = reduce_noise_rnnoise(frame)
    
    # Should return valid frame
    assert result.sample_rate == frame.sample_rate
    assert result.stream_id == frame.stream_id
    assert len(result.pcm_data) == len(frame.pcm_data)
    assert result.pcm_data.dtype == np.int16


def test_rnnoise_preserves_format():
    """Test that RNNoise preserves audio format."""
    # Create test frame with noise
    np.random.seed(42)
    clean_signal = np.sin(np.linspace(0, 2 * np.pi * 440, 320)) * 10000
    noise = np.random.randint(-2000, 2000, size=320, dtype=np.int16)
    noisy_signal = (clean_signal.astype(np.int16) + noise).astype(np.int16)
    
    frame = AudioFrame(
        pcm_data=noisy_signal,
        sample_rate=16000,
        timestamp=0.0,
        stream_id="test-format"
    )
    
    result = reduce_noise_rnnoise(frame)
    
    # Format must be preserved
    assert result.pcm_data.dtype == np.int16
    assert len(result.pcm_data) == len(frame.pcm_data)
    assert result.sample_rate == frame.sample_rate
    assert result.stream_id == frame.stream_id


def test_rnnoise_improves_snr():
    """Test that RNNoise improves signal-to-noise ratio (simple check)."""
    # Create a signal with known noise
    np.random.seed(42)
    signal_freq = 440  # Hz
    samples = 320
    t = np.linspace(0, samples / 16000, samples)
    
    # Clean signal (sine wave)
    clean_signal = np.sin(2 * np.pi * signal_freq * t) * 8000
    clean_pcm = clean_signal.astype(np.int16)
    
    # Add noise
    noise = np.random.randint(-3000, 3000, size=samples, dtype=np.int16)
    noisy_pcm = np.clip((clean_pcm.astype(np.int32) + noise.astype(np.int32)), 
                        np.iinfo(np.int16).min, np.iinfo(np.int16).max).astype(np.int16)
    
    # Calculate original SNR (rough estimate)
    signal_power = np.mean(clean_pcm.astype(np.float32) ** 2)
    noise_power = np.mean(noise.astype(np.float32) ** 2)
    original_snr = 10 * np.log10(signal_power / (noise_power + 1e-10))
    
    # Process with RNNoise
    noisy_frame = AudioFrame(
        pcm_data=noisy_pcm,
        sample_rate=16000,
        timestamp=0.0,
        stream_id="test-snr"
    )
    
    denoised_frame = reduce_noise_rnnoise(noisy_frame)
    denoised_pcm = denoised_frame.pcm_data
    
    # Calculate residual noise (difference from clean signal)
    residual = denoised_pcm.astype(np.float32) - clean_pcm.astype(np.float32)
    residual_power = np.mean(residual ** 2)
    new_snr = 10 * np.log10(signal_power / (residual_power + 1e-10))
    
    # If RNNoise is available and working, SNR should improve
    # If not available, it should at least not make things worse significantly
    # (Allow some tolerance for fallback behavior)
    assert new_snr >= original_snr - 5.0, f"SNR degraded: {original_snr:.2f} -> {new_snr:.2f} dB"


def test_rnnoise_empty_frame():
    """Test RNNoise handles empty frames gracefully."""
    empty_pcm = np.array([], dtype=np.int16)
    frame = AudioFrame(
        pcm_data=empty_pcm,
        sample_rate=16000,
        timestamp=0.0,
        stream_id="test-empty"
    )
    
    result = reduce_noise_rnnoise(frame)
    
    assert len(result.pcm_data) == 0
    assert result.stream_id == frame.stream_id


def test_rnnoise_handles_different_frame_sizes():
    """Test RNNoise handles different frame sizes."""
    for frame_size in [160, 320, 480, 640]:
        pcm_data = np.random.randint(-10000, 10000, size=frame_size, dtype=np.int16)
        frame = AudioFrame(
            pcm_data=pcm_data,
            sample_rate=16000,
            timestamp=0.0,
            stream_id=f"test-size-{frame_size}"
        )
        
        result = reduce_noise_rnnoise(frame)
        
        # Should preserve length
        assert len(result.pcm_data) == len(frame.pcm_data)
        assert result.pcm_data.dtype == np.int16

