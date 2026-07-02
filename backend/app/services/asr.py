from faster_whisper import WhisperModel

MODEL_SIZE = "tiny.en"
_model: WhisperModel | None = None


def get_model() -> WhisperModel:
    global _model
    if _model is None:
        print(f"[ASR] Loading Whisper model '{MODEL_SIZE}'...")
        _model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
        print("[ASR] Model loaded.")
    return _model


def transcribe(audio_path: str) -> list[dict]:
    """Run Whisper ASR on audio file. Returns list of subtitle segments."""
    model = get_model()
    segments, _ = model.transcribe(audio_path, beam_size=5, language="en")

    results = []
    for i, segment in enumerate(segments):
        results.append({
            "index": i,
            "start_time": round(segment.start, 2),
            "end_time": round(segment.end, 2),
            "text": segment.text.strip(),
        })
    return results
