import os
import re
import tempfile
import numpy as np
import soundfile as sf
from pywhispercpp.model import Model
from transformers import pipeline

MODEL_SIZE = "tiny.en"
TARGET_SR = 16000
_model: Model | None = None
_translator = None


def get_model() -> Model:
    global _model
    if _model is None:
        print(f"[ASR] Loading Whisper model '{MODEL_SIZE}'...")
        _model = Model(MODEL_SIZE, print_realtime=False, print_progress=False)
        print("[ASR] Model loaded.")
    return _model


def get_translator():
    """Lazy-load OPUS-MT en→zh translation model."""
    global _translator
    if _translator is None:
        print("[TR] Loading translation model Helsinki-NLP/opus-mt-en-zh...")
        _translator = pipeline("translation", model="Helsinki-NLP/opus-mt-en-zh")
        print("[TR] Translation model loaded.")
    return _translator


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


def _translate_batch(texts: list[str]) -> list[str]:
    """Batch translate English texts to Chinese using local OPUS-MT model.
    Returns bilingual strings in format "English\n中文"."""
    if not texts:
        return texts

    try:
        translator = get_translator()
        results = []
        for text in texts:
            if not text.strip():
                results.append(text)
                continue
            zh_result = translator(text, max_length=512)
            zh_text = zh_result[0]["translation_text"]
            results.append(f"{text}\n{_format_zh(zh_text)}")
        return results
    except Exception as e:
        print(f"[TR] Translation failed: {e}, falling back to English only")
        return texts


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
        en_texts = [seg.text.strip() for seg in segments]
        print(f"[ASR] Transcribed {len(en_texts)} segments, translating...")
        bilingual = _translate_batch(en_texts)
        results = []
        for i, segment in enumerate(segments):
            results.append({
                "index": i,
                "start_time": round(segment.t0 * 0.01, 2),
                "end_time": round(segment.t1 * 0.01, 2),
                "text": bilingual[i],
            })
        return results
    finally:
        os.unlink(wav_path)
