#!/usr/bin/env python3
"""
Test client for AI Voice Confidence Backend.

Captures audio from microphone and sends it to the WebSocket endpoint,
displaying real-time confidence scores.
"""
import asyncio
import websockets
import sounddevice as sd
import numpy as np
import json
import sys
import logging
from typing import Optional

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

# Global audio queues (will be initialized in main)
audio_queue: Optional[asyncio.Queue] = None
processed_audio_queue: Optional[asyncio.Queue] = None


def audio_callback(indata, frames, time_info, status):
    """Callback function for audio input stream."""
    if status:
        print(f"Audio status: {status}", file=sys.stderr)
    
    if audio_queue is None:
        return
    
    # Convert float32 to int16
    audio_int16 = (indata[:, 0] * np.iinfo(np.int16).max).astype(np.int16)
    
    # Put audio data in queue
    try:
        audio_queue.put_nowait(audio_int16.tobytes())
    except asyncio.QueueFull:
        pass  # Drop frame if queue is full


async def send_audio(websocket):
    """Send audio frames to the server."""
    try:
        while True:
            # Get audio chunk from queue
            audio_data = await audio_queue.get()
            
            # Send binary audio data
            await websocket.send(audio_data)
            
    except asyncio.CancelledError:
        print("\nStopped sending audio")
    except Exception as e:
        print(f"\nError sending audio: {e}")


async def receive_messages(websocket, save_processed_audio=False):
    """
    Receive and handle messages from the server.
    
    Protocol: Server sends messages in order:
    - JSON messages (str): Confidence scores (when it's time for update)
    - Binary messages (bytes): Processed audio frames (always, after JSON if present)
    
    After receiving JSON confidence, the next message MUST be binary audio.
    
    Args:
        websocket: WebSocket connection
        save_processed_audio: If True, save processed audio to file
    """
    import wave
    
    global processed_audio_queue
    
    processed_audio_frames = []
    last_confidence = 0.0
    last_stream_id = "unknown"
    
    # Open WAV file for saving processed audio if requested
    wav_file = None
    if save_processed_audio:
        output_file = "processed_audio.wav"
        wav_file = wave.open(output_file, 'wb')
        wav_file.setnchannels(CHANNELS)
        wav_file.setsampwidth(2)  # 16-bit = 2 bytes
        wav_file.setframerate(SAMPLE_RATE)
        print(f"\nSaving processed audio to: {output_file}")
    
    frame_count = 0
    confidence_count = 0
    
    try:
        while True:
            # Receive message (could be JSON or binary)
            message = await websocket.recv()
            
            # Protocol handling:
            # - If JSON (str): Confidence update, next message is binary audio
            # - If Binary (bytes): Processed audio frame (most common case)
            
            if isinstance(message, str):
                # JSON message (confidence) - FastAPI sends JSON as text
                try:
                    data = json.loads(message)
                    if "confidence" in data:
                        confidence_count += 1
                        confidence = data.get("confidence", 0)
                        stream_id = data.get("stream_id", "unknown")
                        timestamp = data.get("timestamp", 0)
                        
                        last_confidence = confidence
                        last_stream_id = stream_id
                        
                        # Display confidence with visual bar
                        bar_length = 50
                        filled = int(bar_length * confidence / 100)
                        bar = "█" * filled + "░" * (bar_length - filled)
                        
                        print(f"\r[{bar}] Confidence: {confidence:5.1f}% | Stream: {stream_id[:12]} | Frames: {frame_count}", end="", flush=True)
                        
                        # After JSON confidence, the next message MUST be binary audio
                        # Wait for the binary audio frame
                        audio_message = await websocket.recv()
                        if isinstance(audio_message, bytes):
                            frame_count += 1
                            # Process the audio frame
                            audio_array = np.frombuffer(audio_message, dtype=np.int16)
                            
                            # Add to playback queue
                            if processed_audio_queue:
                                try:
                                    processed_audio_queue.put_nowait(audio_array)
                                except asyncio.QueueFull:
                                    pass  # Drop frame if queue is full
                            
                            # Save to WAV file if requested
                            if wav_file:
                                wav_file.writeframes(audio_message)
                            
                            processed_audio_frames.append(audio_message)
                except json.JSONDecodeError:
                    # Not valid JSON, skip
                    pass
            
            elif isinstance(message, bytes):
                # Binary message: could be JSON encoded as bytes OR processed audio
                # Try to decode as JSON first (unlikely with FastAPI, but handle it)
                try:
                    message_str = message.decode('utf-8')
                    data = json.loads(message_str)
                    if "confidence" in data:
                        # JSON confidence sent as bytes (rare case)
                        confidence_count += 1
                        confidence = data.get("confidence", 0)
                        stream_id = data.get("stream_id", "unknown")
                        
                        last_confidence = confidence
                        last_stream_id = stream_id
                        
                        bar_length = 50
                        filled = int(bar_length * confidence / 100)
                        bar = "█" * filled + "░" * (bar_length - filled)
                        
                        print(f"\r[{bar}] Confidence: {confidence:5.1f}% | Stream: {stream_id[:12]} | Frames: {frame_count}", end="", flush=True)
                        
                        # Wait for binary audio after JSON
                        audio_message = await websocket.recv()
                        if isinstance(audio_message, bytes):
                            frame_count += 1
                            audio_array = np.frombuffer(audio_message, dtype=np.int16)
                            
                            if processed_audio_queue:
                                try:
                                    processed_audio_queue.put_nowait(audio_array)
                                except asyncio.QueueFull:
                                    pass
                            
                            if wav_file:
                                wav_file.writeframes(audio_message)
                            
                            processed_audio_frames.append(audio_message)
                except (UnicodeDecodeError, json.JSONDecodeError):
                    # Not JSON, it's a processed audio frame (binary PCM) - most common case
                    frame_count += 1
                    audio_array = np.frombuffer(message, dtype=np.int16)
                    
                    # Add to playback queue for real-time playback
                    if processed_audio_queue:
                        try:
                            processed_audio_queue.put_nowait(audio_array)
                        except asyncio.QueueFull:
                            pass  # Drop frame if queue is full (prevent latency buildup)
                    
                    # Save to WAV file if requested
                    if wav_file:
                        wav_file.writeframes(message)
                    
                    processed_audio_frames.append(message)
            
    except asyncio.CancelledError:
        print("\nStopped receiving messages")
    except websockets.exceptions.ConnectionClosed:
        print("\nConnection closed by server")
    except Exception as e:
        print(f"\nError receiving messages: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if wav_file:
            wav_file.close()
            print(f"\nSaved {len(processed_audio_frames)} processed audio frames to processed_audio.wav")
        
        # Print summary
        print(f"\nSummary: Received {frame_count} audio frames, {confidence_count} confidence updates")


def audio_output_callback(outdata, frames, time_info, status):
    """
    Callback function for audio output stream.
    Plays processed audio frames from the queue.
    """
    global processed_audio_queue
    
    if status:
        print(f"Audio output status: {status}", file=sys.stderr)
    
    if processed_audio_queue is None:
        outdata.fill(0)
        return
    
    # Try to get audio from queue
    try:
        audio_array = processed_audio_queue.get_nowait()
        
        # Ensure we have the right size
        if len(audio_array) >= frames:
            # Take first 'frames' samples
            outdata[:, 0] = audio_array[:frames].astype(np.float32) / np.iinfo(np.int16).max
        else:
            # Pad with zeros if frame is smaller
            outdata[:, 0] = np.pad(
                audio_array.astype(np.float32) / np.iinfo(np.int16).max,
                (0, frames - len(audio_array)),
                mode='constant'
            )
    except asyncio.QueueEmpty:
        # No audio available, output silence
        outdata.fill(0)


async def main():
    """Main function to run the test client."""
    global audio_queue, processed_audio_queue
    
    # Create audio queues
    audio_queue = asyncio.Queue(maxsize=100)  # Buffer for input audio
    processed_audio_queue = asyncio.Queue(maxsize=200)  # Buffer for processed audio playback
    
    print("=" * 70)
    print("AI Voice Confidence Backend - Test Client")
    print("=" * 70)
    print(f"Sample Rate: {SAMPLE_RATE} Hz")
    print(f"Channels: {CHANNELS} (Mono)")
    print(f"Chunk Size: {CHUNK_SIZE} samples ({CHUNK_DURATION_MS} ms)")
    print(f"Server: {SERVER_URL}")
    print("=" * 70)
    print("\nStarting audio capture...")
    print("Speak into your microphone to see confidence scores!")
    print("Press Ctrl+C to stop\n")
    
    # Start audio input stream
    stream = sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype=np.float32,
        blocksize=CHUNK_SIZE,
        callback=audio_callback
    )
    
    # Start audio input stream
    input_stream = sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype=np.float32,
        blocksize=CHUNK_SIZE,
        callback=audio_callback
    )
    
    # Start audio output stream for playing processed audio
    output_stream = sd.OutputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype=np.float32,
        blocksize=CHUNK_SIZE,
        callback=audio_output_callback
    )
    
    try:
        input_stream.start()
        output_stream.start()
        print("Audio input/output streams started ✓\n")
        
        # Connect to WebSocket
        async with websockets.connect(SERVER_URL, ping_interval=None) as websocket:
            print("Connected to server ✓\n")
            print("Receiving confidence scores and processed audio...")
            print("🎵 Processed audio is being played back in real-time!")
            print("Confidence scores (updating in real-time):\n")
            
            # Option to save processed audio (set to True to enable)
            # When enabled, processed audio will be saved to processed_audio.wav
            save_audio = True  # Set to True to save processed audio to WAV file
            
            # Run send and receive concurrently
            send_task = asyncio.create_task(send_audio(websocket))
            receive_task = asyncio.create_task(receive_messages(websocket, save_processed_audio=save_audio))
            
            try:
                await asyncio.gather(send_task, receive_task)
            except KeyboardInterrupt:
                print("\n\nStopping...")
                send_task.cancel()
                receive_task.cancel()
                await asyncio.gather(send_task, receive_task, return_exceptions=True)
    
    except KeyboardInterrupt:
        print("\n\nStopped by user")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
    finally:
        input_stream.stop()
        input_stream.close()
        output_stream.stop()
        output_stream.close()
        print("\nAudio streams stopped")
        print("Test client closed")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nExiting...")

