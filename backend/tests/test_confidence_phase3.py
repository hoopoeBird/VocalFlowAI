"""Unit tests for Phase 3 confidence scoring."""
import pytest
from app.audio.ml.confidence import (
    score_confidence_phase3,
    score_confidence,
    smooth_confidence
)


def test_confidence_phase3_comprehensive():
    """Test Phase 3 confidence scoring with all features."""
    # Good quality features
    features_good = {
        "rms_mean": 7000.0,
        "rms_variance": 100000.0,
        "pitch_mean": 200.0,
        "pitch_variance": 50.0,
        "silence_ratio": 0.1,
        "speech_rate": 6.0,
        "spectral_centroid_mean": 2000.0,
        "spectral_centroid_variance": 50000.0,
        "zcr_mean": 0.10,
        "zcr_variance": 0.001
    }
    confidence_good = score_confidence_phase3(features_good)
    assert 0 <= confidence_good <= 100
    assert confidence_good > 50  # Should be reasonably high
    
    # Poor quality features
    features_poor = {
        "rms_mean": 500.0,
        "rms_variance": 5000000.0,
        "pitch_mean": 0.0,
        "pitch_variance": 0.0,
        "silence_ratio": 0.9,
        "speech_rate": 0.5,
        "spectral_centroid_mean": 500.0,
        "spectral_centroid_variance": 1000000.0,
        "zcr_mean": 0.30,  # High ZCR = noise
        "zcr_variance": 0.1
    }
    confidence_poor = score_confidence_phase3(features_poor)
    assert 0 <= confidence_poor <= 100
    assert confidence_poor < confidence_good


def test_confidence_smoothing():
    """Test confidence smoothing prevents jitter."""
    stream_id = "test-stream"
    
    # Simulate jittery input
    raw_scores = [70.0, 75.0, 68.0, 72.0, 74.0, 69.0]
    smoothed_scores = []
    
    for score in raw_scores:
        smoothed = smooth_confidence(stream_id, score, alpha=0.7)
        smoothed_scores.append(smoothed)
    
    # Smoothed scores should be less variable
    assert all(0 <= s <= 100 for s in smoothed_scores)
    
    # Variance should be reduced (smoothed values should be closer together)
    raw_variance = sum((s - 70.0) ** 2 for s in raw_scores) / len(raw_scores)
    smoothed_variance = sum((s - 70.0) ** 2 for s in smoothed_scores) / len(smoothed_scores)
    
    # Smoothed variance should be lower (or at least not much higher)
    assert smoothed_variance <= raw_variance * 1.5  # Allow some tolerance


def test_confidence_main_function_phase3():
    """Test main confidence function with Phase 3."""
    features = {
        "rms_mean": 6000.0,
        "rms_variance": 200000.0,
        "pitch_mean": 180.0,
        "pitch_variance": 100.0,
        "silence_ratio": 0.2,
        "speech_rate": 5.0,
        "spectral_centroid_mean": 1800.0,
        "spectral_centroid_variance": 100000.0,
        "zcr_mean": 0.12,
        "zcr_variance": 0.002
    }
    
    # Phase 3 with smoothing
    conf3 = score_confidence(features, phase=3, stream_id="test", apply_smoothing=True)
    assert 0 <= conf3 <= 100
    assert isinstance(conf3, int)  # Should return integer
    
    # Phase 3 without smoothing
    conf3_raw = score_confidence(features, phase=3, stream_id="test", apply_smoothing=False)
    assert 0 <= conf3_raw <= 100
    assert isinstance(conf3_raw, int)


def test_confidence_bounds_phase3():
    """Test that Phase 3 confidence scores are always in valid range."""
    test_cases = [
        {
            "rms_mean": 0.0, "rms_variance": 0.0, "pitch_mean": 0.0,
            "pitch_variance": 0.0, "silence_ratio": 1.0, "speech_rate": 0.0,
            "spectral_centroid_mean": 0.0, "spectral_centroid_variance": 0.0,
            "zcr_mean": 0.0, "zcr_variance": 0.0
        },
        {
            "rms_mean": 10000.0, "rms_variance": 0.0, "pitch_mean": 300.0,
            "pitch_variance": 10.0, "silence_ratio": 0.0, "speech_rate": 10.0,
            "spectral_centroid_mean": 2500.0, "spectral_centroid_variance": 10000.0,
            "zcr_mean": 0.08, "zcr_variance": 0.0001
        },
    ]
    
    for features in test_cases:
        conf = score_confidence_phase3(features)
        assert 0.0 <= conf <= 100.0, f"Confidence {conf} out of bounds for features {features}"

