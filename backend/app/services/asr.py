import os
import re
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


def _format_zh(text: str) -> str:
    """Format Chinese text: short phrases get spaces between chars, sentences stay continuous."""
    chinese_chars = re.findall(r'[一-鿿]', text)
    if len(chinese_chars) <= 4:
        result = []
        for ch in text:
            if re.match(r'[一-鿿]', ch):
                result.append(ch + ' ')
            else:
                result.append(ch)
        return ''.join(result).strip()
    return text


def _translate_text(text: str) -> str:
    """Translate English to Chinese. Tries multiple backends, falls back to EN-only."""
    return _try_translate(text)


def _try_translate(text: str) -> str:
    """Try translation backends in order, return bilingual or EN-only text."""
    # Try 1: deep-translator Google (may work with system proxy)
    try:
        from deep_translator import GoogleTranslator
        zh = GoogleTranslator(source="en", target="zh-CN").translate(text)
        return f"{text}\n{_format_zh(zh)}"
    except Exception:
        pass

    # Try 2: direct MyMemory API with Chinese
    try:
        import requests
        r = requests.get(
            "https://api.mymemory.translated.net/get",
            params={"q": text, "langpair": "en|zh-CN"},
            timeout=5,
        )
        if r.ok:
            zh = r.json()["responseData"]["translatedText"]
            if zh and zh != text:
                return f"{text}\n{_format_zh(zh)}"
    except Exception:
        pass

    # Fallback: English only
    return text


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
    """Run Whisper ASR + EN→ZH translation. Returns bilingual subtitle segments."""
    model = get_model()

    audio, sample_rate = sf.read(audio_path, dtype="float32")
    if audio.ndim > 1:
        audio = audio.mean(axis=1)

    audio = _resample(audio, sample_rate, TARGET_SR)

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        wav_path = f.name
    sf.write(wav_path, audio, TARGET_SR)

    try:
        segments = model.transcribe(wav_path, language="en")
        results = []
        for i, segment in enumerate(segments):
            en_text = segment.text.strip()
            results.append({
                "index": i,
                "start_time": round(segment.t0 * 0.01, 2),
                "end_time": round(segment.t1 * 0.01, 2),
                "text": _translate_text(en_text),
            })
        return results
    finally:
        os.unlink(wav_path)
