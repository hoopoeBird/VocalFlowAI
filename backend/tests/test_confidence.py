"""Unit tests for confidence scoring."""
import pytest
from app.audio.ml.confidence import score_confidence_phase1, score_confidence_phase2, score_confidence


def test_confidence_phase1_simple():
    """Test Phase 1 confidence scoring with simple RMS-based logic."""
    # High RMS should give high confidence
    features_high = {"rms_mean": 8000.0}
    confidence_high = score_confidence_phase1(features_high)
    assert 0 <= confidence_high <= 100
    assert confidence_high > 50  # Should be reasonably high
    
    # Low RMS should give low confidence
    features_low = {"rms_mean": 500.0}
    confidence_low = score_confidence_phase1(features_low)
    assert 0 <= confidence_low <= 100
    assert confidence_low < confidence_high
    
    # Zero RMS should give zero confidence
    features_zero = {"rms_mean": 0.0}
    confidence_zero = score_confidence_phase1(features_zero)
    assert confidence_zero == 0.0


def test_confidence_phase2_comprehensive():
    """Test Phase 2 confidence scoring with multiple features."""
    # Good quality features
    features_good = {
        "rms_mean": 7000.0,
        "rms_variance": 100000.0,
        "pitch_mean": 200.0,
        "pitch_variance": 50.0,
        "silence_ratio": 0.1,  # Low silence = good
        "speech_rate": 6.0
    }
    confidence_good = score_confidence_phase2(features_good)
    assert 0 <= confidence_good <= 100
    assert confidence_good > 50  # Should be reasonably high
    
    # Poor quality features
    features_poor = {
        "rms_mean": 500.0,
        "rms_variance": 5000000.0,  # High variance = unstable
        "pitch_mean": 0.0,  # No pitch detected
        "pitch_variance": 0.0,
        "silence_ratio": 0.9,  # High silence = bad
        "speech_rate": 0.5
    }
    confidence_poor = score_confidence_phase2(features_poor)
    assert 0 <= confidence_poor <= 100
    assert confidence_poor < confidence_good
    
    # Edge case: all zeros
    features_empty = {
        "rms_mean": 0.0,
        "rms_variance": 0.0,
        "pitch_mean": 0.0,
        "pitch_variance": 0.0,
        "silence_ratio": 1.0,
        "speech_rate": 0.0
    }
    confidence_empty = score_confidence_phase2(features_empty)
    assert 0 <= confidence_empty <= 100


def test_confidence_main_function():
    """Test main confidence scoring function with phase selection."""
    features = {
        "rms_mean": 6000.0,
        "rms_variance": 200000.0,
        "pitch_mean": 180.0,
        "pitch_variance": 100.0,
        "silence_ratio": 0.2,
        "speech_rate": 5.0
    }
    
    # Phase 1
    conf1 = score_confidence(features, phase=1)
    assert 0 <= conf1 <= 100
    
    # Phase 2
    conf2 = score_confidence(features, phase=2)
    assert 0 <= conf2 <= 100
    
    # Phase 3 (should fall back to Phase 2)
    conf3 = score_confidence(features, phase=3)
    assert 0 <= conf3 <= 100


def test_confidence_bounds():
    """Test that confidence scores are always in valid range."""
    # Test various feature combinations
    test_cases = [
        {"rms_mean": 0.0, "rms_variance": 0.0, "pitch_mean": 0.0, 
         "pitch_variance": 0.0, "silence_ratio": 1.0, "speech_rate": 0.0},
        {"rms_mean": 10000.0, "rms_variance": 0.0, "pitch_mean": 300.0,
         "pitch_variance": 10.0, "silence_ratio": 0.0, "speech_rate": 10.0},
        {"rms_mean": 5000.0, "rms_variance": 1000000.0, "pitch_mean": 150.0,
         "pitch_variance": 500.0, "silence_ratio": 0.5, "speech_rate": 3.0},
    ]
    
    for features in test_cases:
        conf = score_confidence_phase2(features)
        assert 0.0 <= conf <= 100.0, f"Confidence {conf} out of bounds for features {features}"

