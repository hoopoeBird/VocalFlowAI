#!/usr/bin/env python3
"""
Test client for the POST /streams/{stream_id}/confidence endpoint.

Generates synthetic audio files (silence, tone, and noise) and tests
the audio processing endpoint, verifying that confidence scores are
returned and processed audio is correctly encoded.
"""
import requests
import base64
import numpy as np
import wave
import sys
import json
import time
from pathlib import Path

# Configuration
SERVER_URL = "http://localhost:8000"
SAMPLE_RATE = 16000
DURATION = 1  # seconds


def generate_silence(filename, duration=1):
    """Generate a silence audio file."""
    samples = np.zeros(int(SAMPLE_RATE * duration), dtype=np.int16)
    
    with wave.open(filename, "w") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(SAMPLE_RATE)
        wav_file.writeframes(samples.tobytes())
    
    return filename


def generate_tone(filename, frequency=1000, duration=1):
    """Generate a sine wave tone."""
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration))
    samples = (np.sin(2 * np.pi * frequency * t) * 10000).astype(np.int16)
    
    with wave.open(filename, "w") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(SAMPLE_RATE)
        wav_file.writeframes(samples.tobytes())
    
    return filename


def generate_noise(filename, duration=1, amplitude=8000):
    """Generate white noise."""
    samples = np.random.randint(-amplitude, amplitude, int(SAMPLE_RATE * duration), dtype=np.int16)
    
    with wave.open(filename, "w") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(SAMPLE_RATE)
        wav_file.writeframes(samples.tobytes())
    
    return filename


def test_endpoint(stream_id, audio_file, description="", stream_chunks=False):
    """
    Test the POST /streams/{stream_id}/confidence endpoint.

    If stream_chunks=True, the audio will be sent in small chunks to emulate a real-time continuous buffer.
    """
    print(f"\n{'=' * 70}")
    print(f"Testing: {description}")
    print(f"{'=' * 70}")
    print(f"Stream ID: {stream_id}")
    print(f"Audio file: {audio_file}")
    print(f"Server: {SERVER_URL}")
    
    try:
        # Read raw PCM frames from the WAV file
        with wave.open(audio_file, "rb") as w:
            frames = w.readframes(w.getnframes())
        
        headers = {'Content-Type': 'application/octet-stream'}
        if stream_chunks:
            # Send chunked/streamed upload to emulate continuous real-time audio
            chunk_size = 2048
            def gen():
                for i in range(0, len(frames), chunk_size):
                    yield frames[i:i+chunk_size]
                    time.sleep(0.01)  # small delay to simulate real-time
            headers['Transfer-Encoding'] = 'chunked'
            response = requests.post(
                f"{SERVER_URL}/streams/{stream_id}/confidence",
                data=gen(),
                headers=headers,
                timeout=30
            )
        else:
            # Send the entire raw PCM buffer in one request
            response = requests.post(
                f"{SERVER_URL}/streams/{stream_id}/confidence",
                data=frames,
                headers=headers,
                timeout=10
            )
        
        # Check response status
        if response.status_code != 200:
            print(f"\n✗ ERROR: HTTP {response.status_code}")
            print(f"Response: {response.text}")
            return False
        
        # Parse response
        data = response.json()
        
        # Validate response structure
        required_fields = ["stream_id", "confidence", "processed_audio_b64", "audio_size_bytes", "timestamp"]
        missing_fields = [f for f in required_fields if f not in data]
        
        if missing_fields:
            print(f"\n✗ ERROR: Missing fields in response: {missing_fields}")
            return False
        
        # Display results
        print(f"\n✓ Response received")
        print(f"  Stream ID: {data['stream_id']}")
        print(f"  Confidence: {data['confidence']:.1f}%")
        print(f"  Audio size: {data['audio_size_bytes']} bytes")
        print(f"  Timestamp: {data['timestamp']}")
        
        # Verify confidence is in valid range
        if not (0 <= data['confidence'] <= 100):
            print(f"✗ WARNING: Confidence out of range: {data['confidence']}")
        else:
            print(f"✓ Confidence in valid range [0-100]")
        
        # Decode processed audio
        try:
            processed_audio = base64.b64decode(data['processed_audio_b64'])
            print(f"✓ Processed audio decoded: {len(processed_audio)} bytes")
            
            # Verify audio size matches
            if len(processed_audio) != data['audio_size_bytes']:
                print(f"✗ WARNING: Decoded size {len(processed_audio)} doesn't match reported {data['audio_size_bytes']}")
            else:
                print(f"✓ Audio size matches")
            
            # Save processed audio
            output_file = f"processed_{stream_id}.wav"
            with open(output_file, "wb") as f:
                f.write(processed_audio)
            print(f"✓ Saved processed audio to: {output_file}")
            
        except Exception as e:
            print(f"✗ ERROR decoding audio: {e}")
            return False
        
        print(f"\n✓ Test PASSED")
        return True
        
    except requests.exceptions.ConnectionError:
        print(f"\n✗ ERROR: Could not connect to server at {SERVER_URL}")
        print(f"   Make sure the backend is running:")
        print(f"   cd backend && python -m uvicorn app.main:app --reload")
        return False
    except requests.exceptions.Timeout:
        print(f"\n✗ ERROR: Request timeout")
        return False
    except Exception as e:
        print(f"\n✗ ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all endpoint tests."""
    print("\n" + "=" * 70)
    print("AI Voice Confidence Backend - Endpoint Test Client")
    print("=" * 70)
    print(f"Server: {SERVER_URL}")
    print(f"Sample Rate: {SAMPLE_RATE} Hz")
    print(f"Test Duration: {DURATION} second(s)")
    print("=" * 70)
    
    # Check server health first
    print("\n[1/4] Checking server health...")
    try:
        health = requests.get(f"{SERVER_URL}/health", timeout=5)
        if health.status_code == 200:
            health_data = health.json()
            print(f"✓ Server is healthy")
            print(f"  Status: {health_data.get('status')}")
            print(f"  Version: {health_data.get('version')}")
        else:
            print(f"✗ Server returned status {health.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"✗ Could not connect to server at {SERVER_URL}")
        print(f"  Make sure backend is running:")
        print(f"  cd backend && python -m uvicorn app.main:app --reload")
        return False
    
    # Generate test files
    print("\n[2/4] Generating test audio files...")
    test_files = [
        ("test_silence.wav", lambda: generate_silence("test_silence.wav", DURATION)),
        ("test_tone.wav", lambda: generate_tone("test_tone.wav", frequency=1000, duration=DURATION)),
        ("test_noise.wav", lambda: generate_noise("test_noise.wav", duration=DURATION))
    ]
    
    for filename, generator in test_files:
        generator()
        size = Path(filename).stat().st_size
        print(f"✓ Generated {filename} ({size} bytes)")
    
    # Run tests
    print("\n[3/4] Running endpoint tests...")
    
    tests = [
        ("silence-test", "test_silence.wav", "Silence (no audio)", False),
        ("tone-test", "test_tone.wav", "1000 Hz Sine Wave Tone", False),
        ("noise-test", "test_noise.wav", "White Noise", False),
        ("streaming-tone", "test_tone.wav", "Streamed 1000 Hz Tone (chunked upload)", True),
    ]
    
    results = []
    for stream_id, audio_file, description, stream_chunks in tests:
        passed = test_endpoint(stream_id, audio_file, description, stream_chunks=stream_chunks)
        results.append((description, passed))
    
    # Summary
    print("\n[4/4] Test Summary")
    print("=" * 70)
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    for description, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {description}")
    
    print(f"\nTotal: {passed_count}/{total_count} tests passed")
    print("=" * 70)
    
    # Cleanup
    print("\nCleaning up generated files...")
    for filename, _, _ in tests:
        try:
            Path(filename).unlink()
            print(f"✓ Deleted {filename}")
        except:
            pass
    
    if passed_count == total_count:
        print("\n✓ All tests PASSED!")
        return True
    else:
        print(f"\n✗ {total_count - passed_count} test(s) FAILED")
        return False


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nExiting...")
        sys.exit(1)
