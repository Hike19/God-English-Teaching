from pywhispercpp.model import Model

MODEL_SIZE = "tiny.en"
_model: Model | None = None


def get_model() -> Model:
    global _model
    if _model is None:
        print(f"[ASR] Downloading Whisper model '{MODEL_SIZE}' (if needed)...")
        _model = Model(MODEL_SIZE, print_realtime=False, print_progress=False)
        print("[ASR] Model loaded.")
    return _model


def transcribe(audio_path: str) -> list[dict]:
    """Run Whisper ASR on audio file. Returns list of subtitle segments."""
    model = get_model()
    segments = model.transcribe(audio_path, language="en")

    results = []
    for i, segment in enumerate(segments):
        results.append({
            "index": i,
            "start_time": round(segment.t0 * 0.01, 2),  # ms → seconds
            "end_time": round(segment.t1 * 0.01, 2),
            "text": segment.text.strip(),
        })
    return results
