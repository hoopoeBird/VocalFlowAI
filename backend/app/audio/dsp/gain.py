"""Gain normalization and automatic gain control (AGC)."""
import numpy as np
from app.audio.models import AudioFrame
from app.core.logging import logger
_current_gain = None
_agc_smoothing = 0.1  # Чем меньше — тем медленнее изменение gain (меньше "дыхания")
# AGC state for smooth gain adjustments (per-stream would be better, but keeping it simple)
_agc_target_rms = 6000.0  # Target RMS level for confident speech
_agc_smoothing = 0.85  # Smoothing factor for gain changes (0.0-1.0, higher = smoother)
_current_gain = 1.0  # Current gain factor

def normalize_gain(
    frame: AudioFrame,
    target_rms: float = 0.2,      # Изменено: теперь цель для float [-1,1]
    max_gain: float = 4.0,
    min_gain: float = 0.1
) -> AudioFrame:
    """
    Normalize audio gain (AGC) — работает независимо от входного формата (int16 или float32/64).
    """
    global _current_gain, _agc_smoothing

    if len(frame.pcm_data) == 0:
        return frame

    # Определяем, в каком формате данные
    is_int16 = np.issubdtype(frame.pcm_data.dtype, np.integer)

    if is_int16:
        # int16 → приводим к float [-1.0, 1.0]
        pcm_float = frame.pcm_data.astype(np.float32) / 32768.0
    else:
        # Уже float — предполагаем [-1, 1]
        pcm_float = frame.pcm_data.astype(np.float32)
        # На всякий случай клиппим
        pcm_float = np.clip(pcm_float, -1.0, 1.0)

    # RMS в float диапазоне
    current_rms = np.sqrt(np.mean(pcm_float ** 2))

    if current_rms < 0.01:  # Очень тихо — не усиливаем шум
        return frame

    desired_gain = target_rms / current_rms
    desired_gain = np.clip(desired_gain, min_gain, max_gain)

    # Сглаживание
    if _current_gain is None:
        _current_gain = desired_gain

    _current_gain = _agc_smoothing * _current_gain + (1.0 - _agc_smoothing) * desired_gain

    # Применяем gain
    normalized_float = pcm_float * _current_gain

    # Soft limiter
    threshold = 0.9
    peak = np.max(np.abs(normalized_float))
    if peak > threshold:
        compression_ratio = 0.7
        over = np.abs(normalized_float) - threshold
        normalized_float = np.where(
            np.abs(normalized_float) > threshold,
            np.sign(normalized_float) * (threshold + over * compression_ratio),
            normalized_float
        )

    # Клиппинг
    normalized_float = np.clip(normalized_float, -1.0, 1.0)

    # Возвращаем в int16 для совместимости с остальным кодом
    normalized_int16 = (normalized_float * 32767.0).astype(np.int16)

    return AudioFrame(
        pcm_data=normalized_int16,
        sample_rate=frame.sample_rate,
        timestamp=frame.timestamp,
        stream_id=frame.stream_id
    )