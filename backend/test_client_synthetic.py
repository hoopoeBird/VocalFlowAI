#!/usr/bin/env python3
"""
Synthetic Test Client - Tests the backend without requiring a microphone.

Generates synthetic audio frames (silence and white noise) and sends them
to the WebSocket endpoint to verify the backend processes them and returns
confidence scores.
"""
import asyncio
import websockets
import numpy as np
import json
import sys
import logging

# Setup basic logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# Audio configuration (must match server settings)
SAMPLE_RATE = 16000  # Hz
CHANNELS = 1  # Mono
DTYPE = np.int16
CHUNK_DURATION_MS = 20  # milliseconds per chunk
CHUNK_SIZE = int(SAMPLE_RATE * CHUNK_DURATION_MS / 1000)  # samples per chunk

# Server configuration
SERVER_URL = "ws://localhost:8000/ws/audio"

# Test parameters
SILENCE_FRAMES = 20  # Send 20 frames of silence
NOISE_FRAMES = 40    # Then 40 frames of white noise
PAUSE_MS = 50        # ms to pause between frames


def generate_silence_frame(chunk_size):
    """Generate a frame of silence."""
    return np.zeros(chunk_size, dtype=np.int16)


def generate_noise_frame(chunk_size, amplitude=5000):
    """Generate a frame of white noise."""
    return np.random.randint(-amplitude, amplitude, chunk_size, dtype=np.int16)


async def test_backend():
    """Main test function."""
    print("=" * 70)
    print("AI Voice Confidence Backend - Synthetic Test Client")
    print("=" * 70)
    print(f"Sample Rate: {SAMPLE_RATE} Hz")
    print(f"Channels: {CHANNELS} (Mono)")
    print(f"Chunk Size: {CHUNK_SIZE} samples ({CHUNK_DURATION_MS} ms)")
    print(f"Server: {SERVER_URL}")
    print("=" * 70)
    print("\nGenerating synthetic audio frames...")
    print(f"  - {SILENCE_FRAMES} frames of silence")
    print(f"  - {NOISE_FRAMES} frames of white noise")
    print("=" * 70 + "\n")

    try:
        # Connect to WebSocket
        async with websockets.connect(SERVER_URL, ping_interval=None) as websocket:
            print("✓ Connected to server\n")
            print("Frame #  | Type      | Confidence | Stream ID")
            print("-" * 60)

            frame_count = 0
            confidence_updates = []
            last_stream_id = None

            # Send silence frames
            for i in range(SILENCE_FRAMES):
                frame = generate_silence_frame(CHUNK_SIZE)
                await websocket.send(frame.tobytes())
                frame_count += 1

                # Try to receive confidence update if available
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=0.1)
                    
                    if isinstance(message, str):
                        data = json.loads(message)
                        confidence = data.get("confidence", 0)
                        stream_id = data.get("stream_id", "unknown")
                        last_stream_id = stream_id
                        confidence_updates.append(confidence)
                        
                        print(f"{frame_count:7d}  | Silence   | {confidence:10.1f} | {stream_id[:12]}")
                        
                        # Receive the accompanying binary audio frame
                        audio_frame = await asyncio.wait_for(websocket.recv(), timeout=0.1)
                    elif isinstance(message, bytes):
                        # Binary audio frame without confidence
                        pass
                except asyncio.TimeoutError:
                    pass

                # Small delay between frames to simulate real-time
                await asyncio.sleep(PAUSE_MS / 1000.0)

            print()

            # Send noise frames
            for i in range(NOISE_FRAMES):
                frame = generate_noise_frame(CHUNK_SIZE, amplitude=8000)
                await websocket.send(frame.tobytes())
                frame_count += 1

                # Try to receive confidence update if available
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=0.1)
                    
                    if isinstance(message, str):
                        data = json.loads(message)
                        confidence = data.get("confidence", 0)
                        stream_id = data.get("stream_id", "unknown")
                        last_stream_id = stream_id
                        confidence_updates.append(confidence)
                        
                        print(f"{frame_count:7d}  | Noise     | {confidence:10.1f} | {stream_id[:12]}")
                        
                        # Receive the accompanying binary audio frame
                        audio_frame = await asyncio.wait_for(websocket.recv(), timeout=0.1)
                    elif isinstance(message, bytes):
                        # Binary audio frame without confidence
                        pass
                except asyncio.TimeoutError:
                    pass

                # Small delay between frames to simulate real-time
                await asyncio.sleep(PAUSE_MS / 1000.0)

            print("\n" + "=" * 70)
            print("TEST RESULTS")
            print("=" * 70)
            print(f"Total frames sent: {frame_count}")
            print(f"Confidence updates received: {len(confidence_updates)}")
            if confidence_updates:
                print(f"Confidence scores: min={min(confidence_updates):.1f}%, "
                      f"max={max(confidence_updates):.1f}%, "
                      f"avg={np.mean(confidence_updates):.1f}%")
                print(f"Last stream ID: {last_stream_id}")
            print("=" * 70)
            print("\n✓ Test completed successfully!")

    except ConnectionRefusedError:
        print("\n✗ ERROR: Could not connect to server at", SERVER_URL)
        print("  Make sure the backend is running:")
        print("    cd backend && python -m uvicorn app.main:app --reload")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(test_backend())
    except KeyboardInterrupt:
        print("\n\nExiting...")
