from faster_whisper import WhisperModel

MODEL_SIZE = "large-v3"
_model: WhisperModel | None = None


def get_model() -> WhisperModel:
    global _model
    if _model is None:
        _model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
    return _model


def transcribe(audio_path: str) -> list[dict]:
    """Run Whisper ASR on audio file. Returns list of subtitle segments.

    Returns:
        list[dict]: [{"index": 0, "start_time": 0.0, "end_time": 2.5, "text": "Hello"}, ...]
    """
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
