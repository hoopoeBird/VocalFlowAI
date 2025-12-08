# AI Voice Confidence Backend

Real-time voice confidence scoring and audio processing backend for VocalFlowAI.

## Overview

This backend receives audio from web clients via WebSocket, processes it through a DSP pipeline, and computes real-time confidence scores (0-100) based on audio features.

## Features

- **WebSocket Audio Ingestion**: Receive raw PCM audio frames from clients
- **DSP Pipeline**: Gain normalization, noise reduction, pitch/energy adjustment
- **Confidence Scoring**: Real-time voice confidence scoring (Phase 1: RMS-based, Phase 2: Multi-feature rule-based, Phase 3: ML model - future)
- **REST API**: Health check and stream status endpoints
- **Low Latency**: Target <20ms per-frame processing time

## Installation

```bash
cd backend
pip install -r requirements.txt
```

## Running

```bash
uvicorn app.main:app --reload
```

The server will start on `http://localhost:8000` by default.

## API Endpoints

### WebSocket: `/ws/audio`

- **Client → Server**: Binary PCM int16 audio frames (mono, 16 kHz default)
- **Server → Client**: JSON messages with confidence scores:
  ```json
  {
    "confidence": 73.5,
    "timestamp": 1234567890.123,
    "stream_id": "ws-abc12345"
  }
  ```

### REST: `/health`

- **Method**: GET
- **Response**:
  ```json
  {
    "status": "ok",
    "version": "0.1.0"
  }
  ```

### REST: `/streams/{stream_id}/confidence`

- **Method**: GET
- **Response**:
  ```json
  {
    "stream_id": "ws-abc12345",
    "confidence": 81.2,
    "updated_at": "2025-12-07T16:32:10Z"
  }
  ```

## Configuration

Configuration is managed via environment variables (see `app/core/config.py`):

- `SAMPLE_RATE`: Audio sample rate (default: 16000)
- `FRAME_SIZE_MS`: Frame size in milliseconds (default: 20)
- `ENABLE_GAIN_NORMALIZATION`: Enable gain normalization (default: true)
- `ENABLE_NOISE_REDUCTION`: Enable noise reduction (default: true)
- `ENABLE_PITCH_ADJUSTMENT`: Enable pitch/energy adjustment (default: false)
- `CONFIDENCE_WINDOW_SECONDS`: Time window for feature aggregation (default: 0.5)
- `CONFIDENCE_UPDATE_INTERVAL_MS`: Confidence update frequency (default: 100)

## Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI entrypoint
│   ├── api/
│   │   ├── ws_audio.py      # WebSocket endpoint
│   │   └── rest_status.py   # REST endpoints
│   ├── core/
│   │   ├── config.py        # Configuration
│   │   └── logging.py        # Logging setup
│   ├── audio/
│   │   ├── models.py        # AudioFrame, StreamState
│   │   ├── buffers.py       # Stream buffering
│   │   ├── ingestion.py     # Audio ingestion helpers
│   │   ├── pipeline.py      # Main processing pipeline
│   │   ├── streaming.py     # Output streaming helpers
│   │   ├── dsp/
│   │   │   ├── gain.py      # Gain normalization
│   │   │   ├── noise.py     # Noise reduction
│   │   │   ├── pitch.py     # Pitch estimation/adjustment
│   │   │   └── pacing.py    # Silence/pacing metrics
│   │   └── ml/
│   │       ├── features.py  # Feature extraction
│   │       ├── confidence.py # Confidence scoring
│   │       └── enhancement.py # ML enhancement (future)
│   └── services/
│       ├── confidence_service.py # Confidence state management
│       └── stream_router.py     # Stream routing
└── tests/
    ├── test_dsp_gain.py     # DSP tests
    └── test_confidence.py   # Confidence scoring tests
```

## Testing

```bash
pytest tests/
```

## Development Phases

- **Phase 1 (MVP)**: WebSocket endpoint, simple gain normalization, RMS-based confidence
- **Phase 2**: Noise reduction, pitch features, improved multi-feature confidence scoring
- **Phase 3 (Future)**: ML model integration via ONNX Runtime for enhanced confidence scoring and voice enhancement

## License

See project root for license information.

