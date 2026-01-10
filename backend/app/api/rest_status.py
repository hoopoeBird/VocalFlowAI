"""REST endpoints for health and status."""
from fastapi import APIRouter, HTTPException, UploadFile, File, Request
from datetime import datetime
from app.services.confidence_service import confidence_service
from app.audio.buffers import buffer_manager
from app.core.logging import logger
from app.audio.ingestion import bytes_to_audio_frame
from app.audio.pipeline import process_audio_frame
from app.audio.ml.features import extract_features
from app.audio.ml.confidence import score_confidence
from app.audio.streaming import frame_to_bytes
import numpy as np

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Health check endpoint.

    Returns:
        Status and version information
    """
    from app.services.confidence_service import confidence_service
    from app.audio.buffers import buffer_manager
    import psutil
    import os

    try:
        # Get system info for Railway monitoring
        memory = psutil.virtual_memory()
        active_streams = await buffer_manager.get_stream_count()
        memory_usage = await buffer_manager.get_memory_usage_mb()

        return {
            "status": "ok",
            "version": "0.1.0",
            "environment": "railway" if os.getenv("RAILWAY_ENVIRONMENT") else "local",
            "active_streams": active_streams,
            "memory_usage_mb": round(memory_usage, 2),
            "system_memory_percent": round(memory.percent, 1),
            "ml_enabled": True  # We'll assume it's enabled since we're here
        }
    except Exception as e:
        # Fallback if system monitoring fails
        return {
            "status": "degraded",
            "version": "0.1.0",
            "error": str(e)
        }


@router.get("/streams/{stream_id}/confidence")
async def get_stream_confidence(stream_id: str):
    """
    Get latest confidence score for a stream.
    
    Args:
        stream_id: Stream identifier
        
    Returns:
        Confidence score with timestamp
    """
    result = await confidence_service.get_confidence_with_timestamp(stream_id)
    
    if result is None:
        raise HTTPException(status_code=404, detail=f"Stream {stream_id} not found")
    
    # Format timestamp as ISO 8601
    if result["updated_at"]:
        result["updated_at"] = datetime.fromtimestamp(result["updated_at"]).isoformat() + "Z"
    
    return result


@router.post("/streams/{stream_id}/confidence")
async def process_audio_and_get_confidence(stream_id: str, request: Request, file: UploadFile = File(None)):
    """
    Process audio buffer and return confidence score + processed audio.
    
    Accepts:
      - binary PCM audio (int16, 16kHz, mono) sent as application/octet-stream (recommended for continuous buffers)
      - or multipart/form-data with a file (kept for backward compatibility)
    
    Args:
        stream_id: Stream identifier
        request: FastAPI Request object (used to read streaming body)
        file: Optional uploaded file (multipart)
        
    Returns:
        JSON with confidence score and base64-encoded processed audio
    """
    try:
        content_type = request.headers.get("content-type", "")
        # Read audio bytes either from UploadFile (multipart) or the streamed body
        if file is not None:
            audio_bytes = await file.read()
        elif "multipart/form-data" in content_type:
            # multipart was used but no file provided
            raise HTTPException(status_code=400, detail="No file uploaded in multipart/form-data request")
        else:
            # Read raw/streamed body in chunks (supports chunked transfer / streaming uploads)
            chunks = []
            total = 0
            max_size = 10 * 1024 * 1024  # 10 MB safety cap
            async for chunk in request.stream():
                chunks.append(chunk)
                total += len(chunk)
                if total > max_size:
                    raise HTTPException(status_code=413, detail="Payload too large")
            audio_bytes = b"".join(chunks)

        # Convert to AudioFrame
        frame = bytes_to_audio_frame(audio_bytes, stream_id)
        
        # Process frame through DSP + ML pipeline
        processed_frame = process_audio_frame(frame)
        
        # Extract features
        features = extract_features([processed_frame])
        
        # Compute confidence score
        confidence = score_confidence(
            features,
            phase=3,
            stream_id=stream_id,
            apply_smoothing=True
        )
        
        # Convert processed frame back to bytes
        processed_audio_bytes = frame_to_bytes(processed_frame)
        
        # Convert to base64 for JSON response
        import base64
        processed_audio_b64 = base64.b64encode(processed_audio_bytes).decode('utf-8')
        
        return {
            "stream_id": stream_id,
            "confidence": float(confidence),
            "timestamp": frame.timestamp,
            "processed_audio_b64": processed_audio_b64,
            "audio_size_bytes": len(processed_audio_bytes)
        }
        
    except ValueError as e:
        logger.error(f"Invalid audio data for stream {stream_id}: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid audio data: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing audio for stream {stream_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing audio: {str(e)}")

