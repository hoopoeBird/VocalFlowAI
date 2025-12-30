# backend/app/audio/dsp/vad.py
import numpy as np

def vad_speech_ratio(
    pcm_i16: np.ndarray,
    state,
    sample_rate: int = 16000,
    frame_ms: int = 20,
    rms_mult: float = 3.0,
    hangover_frames: int = 8,
    noise_alpha: float = 0.02,
) -> float:
    """
    Quick VAD: returns speech ratio in [0..1] for this chunk.
    Uses adaptive noise floor + hangover smoothing.
    `state` is StreamState (expects vad_noise_floor, vad_hangover).
    """
    if pcm_i16 is None or pcm_i16.size == 0:
        return 0.0

    # convert to float32 [-1, 1]
    x = pcm_i16.astype(np.float32) / 32768.0

    hop = int(sample_rate * frame_ms / 1000)
    if hop <= 0:
        return 0.0

    n = x.size // hop
    if n <= 0:
        return 0.0

    x = x[: n * hop].reshape(n, hop)
    rms = np.sqrt(np.mean(x * x, axis=1) + 1e-12)

    thr = max(state.vad_noise_floor * rms_mult, 1e-4)
    raw = rms > thr

    # hangover smoothing
    out = np.zeros_like(raw, dtype=bool)
    for i, is_speech in enumerate(raw):
        if is_speech:
            state.vad_hangover = hangover_frames
            out[i] = True
        else:
            if state.vad_hangover > 0:
                state.vad_hangover -= 1
                out[i] = True

    # update noise floor using non-speech frames
    nonspeech = rms[~out]
    if nonspeech.size > 0:
        state.vad_noise_floor = (1 - noise_alpha) * state.vad_noise_floor + noise_alpha * float(np.median(nonspeech))

    return float(out.mean()) if out.size else 0.0
