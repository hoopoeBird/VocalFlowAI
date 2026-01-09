# Testing the AI Voice Confidence Backend

## Quick Start

### 1. Start the Server

Make sure the server is running:

```bash
cd backend
uvicorn app.main:app --reload
```

The server should be accessible at `http://localhost:8000`

### 2. Run the Test Client

In a new terminal, run the test client:

```bash
cd backend
python test_client.py
```

Or if you made it executable:

```bash
./test_client.py
```

### 3. Speak into Your Microphone

Once the test client is running:
- Speak into your microphone
- Watch the real-time confidence scores update
- The confidence bar will show values from 0-100%
- Press `Ctrl+C` to stop

## What You'll See

The test client displays:
- A visual progress bar showing confidence level
- Numerical confidence score (0-100%)
- Stream ID for the current session

Example output:
```
[████████████████████████████████████████████████░░░░] Confidence:  85.3% | Stream: ws-abc12345
```

### Alternative: Endpoint Test Client (REST API - No Microphone Required)

For testing without a microphone, use the endpoint test client:

```bash
cd backend
python test_client_endpoint.py
```

This test client:
- **Generates 3 test audio files** (silence, 1000 Hz tone, white noise)
- **Tests the POST `/streams/{stream_id}/confidence` endpoint** with each audio file
- **Validates** confidence scores, response format, and base64 audio decoding
- **Saves processed audio** for inspection
- **Reports pass/fail** for each test

#### Expected Output

```
======================================================================
AI Voice Confidence Backend - Endpoint Test Client
======================================================================

[1/4] Checking server health...
✓ Server is healthy
  Status: ok
  Version: 0.1.0

[2/4] Generating test audio files...
✓ Generated test_silence.wav (32044 bytes)
✓ Generated test_tone.wav (32044 bytes)
✓ Generated test_noise.wav (32044 bytes)

[3/4] Running endpoint tests...

======================================================================
Testing: Silence (no audio)
======================================================================
✓ Response received
  Stream ID: silence-test
  Confidence: 25.3%
  Audio size: 640 bytes
✓ Confidence in valid range [0-100]
✓ Processed audio decoded: 640 bytes
✓ Saved processed audio to: processed_silence-test.wav
✓ Test PASSED

======================================================================
Testing: 1000 Hz Sine Wave Tone
======================================================================
✓ Response received
  Stream ID: tone-test
  Confidence: 72.1%
  Audio size: 640 bytes
✓ Confidence in valid range [0-100]
✓ Processed audio decoded: 640 bytes
✓ Saved processed audio to: processed_tone-test.wav
✓ Test PASSED

======================================================================
Testing: White Noise
======================================================================
✓ Response received
  Stream ID: noise-test
  Confidence: 65.8%
  Audio size: 640 bytes
✓ Confidence in valid range [0-100]
✓ Processed audio decoded: 640 bytes
✓ Saved processed audio to: processed_noise-test.wav
✓ Test PASSED

[4/4] Test Summary
======================================================================
✓ PASS: Silence (no audio)
✓ PASS: 1000 Hz Sine Wave Tone
✓ PASS: White Noise

Total: 3/3 tests passed
======================================================================

✓ All tests PASSED!
```

## Troubleshooting

### No Audio Input

If you get errors about audio devices:
1. Check that your microphone is connected and working
2. List available audio devices: `python -c "import sounddevice as sd; print(sd.query_devices())"`
3. You may need to specify a device in the test client
4. Try the endpoint test client instead: `python test_client_endpoint.py`

### Connection Errors

If you can't connect to the server:
1. Make sure the server is running: `curl http://localhost:8000/health`
2. Check that port 8000 is not blocked
3. Verify the server URL in `test_client.py` matches your setup

### Low Confidence Scores

If confidence scores are always low:
- Speak louder and more clearly
- Check microphone input level
- Make sure you're in a quiet environment
- The confidence algorithm improves with more audio data

## Alternative: Manual Testing with curl

You can also test the REST endpoints:

```bash
# Health check
curl http://localhost:8000/health

# Get confidence for a stream (replace STREAM_ID with actual ID from WebSocket)
curl http://localhost:8000/streams/STREAM_ID/confidence
```

## Audio Processing Endpoint (REST API)

Process audio buffers and get confidence scores + processed audio via HTTP POST:

```bash
# Send audio file for processing and get confidence + processed audio
curl -X POST \
  -F "file=@audio.wav" \
  http://localhost:8000/streams/my-stream-id/confidence
```

### Response Format

```json
{
  "stream_id": "my-stream-id",
  "confidence": 85.3,
  "timestamp": 1234567890.123,
  "processed_audio_b64": "AAAAAAAAAAAAAAAAAAAw...",
  "audio_size_bytes": 640
}
```

### Parameters

- **stream_id** (path): Unique identifier for this processing session
- **file** (form): Binary audio file (PCM int16, 16kHz, mono)

### Return Values

- **confidence**: Confidence score from 0-100%
- **processed_audio_b64**: Base64-encoded processed audio (can be decoded back to binary)
- **audio_size_bytes**: Size of the processed audio in bytes
- **timestamp**: Frame timestamp

### Python Example

```python
import requests
import base64

# Send audio file
with open("audio.wav", "rb") as f:
    response = requests.post(
        "http://localhost:8000/streams/my-stream/confidence",
        files={"file": f}
    )

data = response.json()
confidence = data["confidence"]
processed_audio = base64.b64decode(data["processed_audio_b64"])

print(f"Confidence: {confidence}%")
print(f"Processed audio size: {data['audio_size_bytes']} bytes")

# Save processed audio
with open("processed_audio.wav", "wb") as f:
    f.write(processed_audio)
```

### JavaScript Example

```javascript
const formData = new FormData();
formData.append('file', audioBlob);

const response = await fetch('http://localhost:8000/streams/my-stream/confidence', {
  method: 'POST',
  body: formData
});

const data = await response.json();
console.log(`Confidence: ${data.confidence}%`);

// Decode base64 audio
const binaryString = atob(data.processed_audio_b64);
const bytes = new Uint8Array(binaryString.length);
for (let i = 0; i < binaryString.length; i++) {
  bytes[i] = binaryString.charCodeAt(i);
}
```

## WebSocket Testing with wscat (Optional)

If you have `wscat` installed:

```bash
# Install wscat: npm install -g wscat

# Connect to WebSocket
wscat -c ws://localhost:8000/ws/audio

# Send binary audio data (you'll need to format it as PCM int16)
```

## Understanding Confidence Scores

- **0-30%**: Very quiet, mostly silence, or poor audio quality
- **30-60%**: Moderate confidence, some speech detected
- **60-80%**: Good confidence, clear speech
- **80-100%**: High confidence, strong and clear voice

The confidence score is based on:
- Audio loudness (RMS)
- Pitch stability
- Silence ratio
- Speech rate
- Audio stability

