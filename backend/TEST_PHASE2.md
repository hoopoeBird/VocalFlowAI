# Testing Phase 2: DSP Pipeline + Processed Audio Output

## Quick Test

### Step 1: Make sure server is running

```bash
# Check if server is running
curl http://localhost:8000/health

# If not running, start it:
cd /home/hayk/Desktop/VocalFlowAI/backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Step 2: Run the test client

```bash
cd /home/hayk/Desktop/VocalFlowAI/backend
python test_client.py
```

### Step 3: Speak into your microphone

- You'll see confidence scores updating in real-time
- Processed audio is being received (but not played back by default)
- Press `Ctrl+C` to stop

## What to Expect

### Console Output

```
======================================================================
AI Voice Confidence Backend - Test Client
======================================================================
Sample Rate: 16000 Hz
Channels: 1 (Mono)
Chunk Size: 320 samples (20 ms)
Server: ws://localhost:8000/ws/audio
======================================================================

Starting audio capture...
Speak into your microphone to see confidence scores!
Press Ctrl+C to stop

Audio stream started ✓

Connected to server ✓

Receiving confidence scores and processed audio...
(Processed audio is being received but not played back)
Confidence scores (updating in real-time):

[████████████████████████████████████████░░░░░░░░░░░░] Confidence:  72.5% | Stream: ws-abc12345
```

### What's Happening

1. **Audio Capture**: Your microphone input is captured at 16kHz, mono
2. **DSP Processing**: Each frame goes through:
   - Noise reduction (spectral subtraction)
   - Gain normalization (AGC)
   - Optional energy adjustment
3. **Dual Output**: Server sends back:
   - **JSON messages**: Confidence scores (every 100ms)
   - **Binary messages**: Processed audio frames (every 20ms)

## Advanced Testing: Save Processed Audio

To verify the DSP is actually improving the audio:

### Option 1: Enable saving in test_client.py

Edit `test_client.py` and change:
```python
save_audio = False  # Change to True
```

Then run:
```bash
python test_client.py
```

Speak for a few seconds, then press `Ctrl+C`. You'll get:
- `processed_audio.wav` - The processed audio from the server

### Option 2: Compare Original vs Processed

1. Record original audio with a tool like `arecord`:
```bash
arecord -r 16000 -f S16_LE -c 1 original.wav
```

2. Run test client with `save_audio = True` and speak the same thing

3. Compare the files:
   - Original should have more noise
   - Processed should have:
     - Reduced background noise
     - More consistent volume (gain normalization)
     - Clearer speech

## Testing DSP Features

### Test Noise Reduction

1. Speak in a quiet environment → Note confidence score
2. Add background noise (fan, keyboard typing) → Confidence may drop
3. The processed audio should have less noise than input

### Test Gain Normalization

1. Speak quietly → Confidence should be lower
2. Speak normally → Confidence should increase
3. Speak loudly → Should not clip, gain should normalize

### Test Real-time Processing

- Confidence updates every 100ms (configurable)
- Processed audio sent every 20ms (real-time)
- Total latency should be < 20ms per frame

## Troubleshooting

### No confidence scores appearing

- Check microphone is working: `python3 -c "import sounddevice as sd; print(sd.query_devices())"`
- Speak louder or closer to microphone
- Check server logs for errors

### Low confidence scores

- Normal for quiet speech or background noise
- Speak clearly and at normal volume
- Confidence algorithm considers: loudness, pitch stability, silence ratio

### Processed audio not being received

- Check server logs: Look for "Error sending response"
- Verify WebSocket connection is established
- Check that DSP modules are enabled in config

## Verify DSP is Working

### Check Server Logs

The server should show:
- "New WebSocket connection: ws-xxxxx"
- Processing times (should be < 20ms)
- No errors in DSP pipeline

### Monitor Processing

Watch for warnings like:
```
Frame processing took 25.3ms (target: 20ms)
```
This indicates the pipeline is working but may need optimization.

## Expected Results

✅ **Working correctly if:**
- Confidence scores update in real-time
- Scores increase when you speak clearly
- No errors in server logs
- Processing time < 20ms (no warnings)

✅ **DSP is working if:**
- Processed audio file is created (when saving enabled)
- Audio quality improves (less noise, better volume)
- No audio dropouts or artifacts

## Next Steps

Once testing is successful:
- Phase 2 is complete! ✅
- Ready for Phase 3: ML/ONNX integration
- Can integrate with desktop client for virtual microphone

