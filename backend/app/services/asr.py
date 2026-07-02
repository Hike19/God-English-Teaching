import os
import tempfile
import numpy as np
import soundfile as sf
from pywhispercpp.model import Model

MODEL_SIZE = "tiny.en"
TARGET_SR = 16000
_model: Model | None = None


def get_model() -> Model:
    global _model
    if _model is None:
        print(f"[ASR] Loading Whisper model '{MODEL_SIZE}'...")
        _model = Model(MODEL_SIZE, print_realtime=False, print_progress=False)
        print("[ASR] Model loaded.")
    return _model


def _resample(audio: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
    """Simple resampling using linear interpolation."""
    if orig_sr == target_sr:
        return audio
    duration = len(audio) / orig_sr
    new_len = int(duration * target_sr)
    old_indices = np.linspace(0, len(audio) - 1, len(audio))
    new_indices = np.linspace(0, len(audio) - 1, new_len)
    return np.interp(new_indices, old_indices, audio).astype(np.float32)


def transcribe(audio_path: str) -> list[dict]:
    """Run Whisper ASR on audio file. Returns list of subtitle segments."""
    model = get_model()

    # Read audio with soundfile
    audio, sample_rate = sf.read(audio_path, dtype="float32")
    if audio.ndim > 1:
        audio = audio.mean(axis=1)

    # Resample to 16000 Hz
    audio = _resample(audio, sample_rate, TARGET_SR)

    # Save as temp WAV at 16kHz
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        wav_path = f.name
    sf.write(wav_path, audio, TARGET_SR)

    try:
        segments = model.transcribe(wav_path, language="en")
        results = []
        for i, segment in enumerate(segments):
            results.append({
                "index": i,
                "start_time": round(segment.t0 * 0.01, 2),
                "end_time": round(segment.t1 * 0.01, 2),
                "text": segment.text.strip(),
            })
        return results
    finally:
        os.unlink(wav_path)
