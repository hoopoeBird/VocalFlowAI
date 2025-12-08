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

## Troubleshooting

### No Audio Input

If you get errors about audio devices:
1. Check that your microphone is connected and working
2. List available audio devices: `python -c "import sounddevice as sd; print(sd.query_devices())"`
3. You may need to specify a device in the test client

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

