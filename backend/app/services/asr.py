import os
import tempfile
import soundfile as sf
from pywhispercpp.model import Model

MODEL_SIZE = "tiny.en"
_model: Model | None = None


def get_model() -> Model:
    global _model
    if _model is None:
        print(f"[ASR] Loading Whisper model '{MODEL_SIZE}'...")
        _model = Model(MODEL_SIZE, print_realtime=False, print_progress=False)
        print("[ASR] Model loaded.")
    return _model


def transcribe(audio_path: str) -> list[dict]:
    """Run Whisper ASR on audio file. Returns list of subtitle segments.

    Converts audio to WAV via soundfile first, avoiding the need for ffmpeg
    in pywhispercpp's audio loading.
    """
    model = get_model()

    # Read with soundfile (no ffmpeg needed) and save as WAV
    audio, sample_rate = sf.read(audio_path, dtype="float32")
    if audio.ndim > 1:
        audio = audio.mean(axis=1)  # stereo → mono

    # Save as temp WAV for pywhispercpp (it can load WAV without ffmpeg)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        wav_path = f.name
    sf.write(wav_path, audio, sample_rate)

    try:
        segments = model.transcribe(wav_path, language="en")
        results = []
        for i, segment in enumerate(segments):
            results.append({
                "index": i,
                "start_time": round(segment.t0 * 0.01, 2),  # ms → seconds
                "end_time": round(segment.t1 * 0.01, 2),
                "text": segment.text.strip(),
            })
        return results
    finally:
        os.unlink(wav_path)
