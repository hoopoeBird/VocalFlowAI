"""FastAPI application entrypoint."""
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from app.api import ws_audio, rest_status
from app.core.config import settings
from app.core.logging import setup_logging

# Setup logging
setup_logging()

# Create FastAPI app
app = FastAPI(
    title="AI Voice Confidence Backend",
    description="Real-time voice confidence scoring and audio processing backend",
    version="0.1.0"
)

# CORS middleware (allow frontend connections)
# Note: For WebSocket, CORS doesn't apply, but this helps with REST API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=False,  # Must be False when using "*" origins
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(rest_status.router)

# WebSocket endpoint
@app.websocket("/ws/audio")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for audio streaming."""
    # ws_audio.websocket_audio_endpoint already calls websocket.accept()
    await ws_audio.websocket_audio_endpoint(websocket)


@app.on_event("startup")
async def startup_event():
    """Initialize on startup."""
    from app.core.logging import logger
    from app.audio.ml.enhancement import load_enhancement_model
    import os

    # Log Railway deployment info
    port = os.getenv("PORT", settings.port)
    logger.info(f"Starting AI Voice Confidence Backend on {settings.host}:{port}")
    logger.info(f"Environment: Railway={bool(os.getenv('RAILWAY_ENVIRONMENT'))}, PORT={port}")
    logger.info(f"Sample rate: {settings.sample_rate} Hz, Frame size: {settings.frame_size_ms} ms")

    # Phase 3: Initialize ML enhancement model if enabled
    if settings.enable_ml_enhancement:
        logger.info("ML enhancement enabled, loading ONNX model...")
        try:
            model = load_enhancement_model()
            if model is not None:
                logger.info("✓ ML enhancement model loaded successfully")
            else:
                logger.warning("⚠ ML enhancement enabled but model not available, will use DSP-only processing")
        except Exception as e:
            logger.error(f"⚠ Failed to load ML enhancement model: {e}, falling back to DSP-only processing")
            # Disable ML enhancement if loading fails
            settings.enable_ml_enhancement = False
    else:
        logger.info("ML enhancement disabled (set ENABLE_ML_ENHANCEMENT=true to enable)")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    from app.core.logging import logger
    logger.info("Shutting down AI Voice Confidence Backend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True
    )

