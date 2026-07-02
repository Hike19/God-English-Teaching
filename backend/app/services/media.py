import os
import shutil
import uuid
import subprocess
import yt_dlp
from ..config import settings

AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".flac", ".webm", ".ogg"}

CN_SITES = {"bilibili.com", "b23.tv", "douyin.com", "xiaohongshu.com",
            "v.qq.com", "iqiyi.com", "music.163.com", "y.qq.com"}


def _is_cn_site(url: str) -> bool:
    return any(s in url for s in CN_SITES)


def is_audio_file(path: str) -> bool:
    return os.path.splitext(path)[1].lower() in AUDIO_EXTENSIONS


def download_media(url: str) -> str:
    """Download media from URL. Uses you-get for Chinese sites, yt-dlp for others."""
    task_dir = os.path.join(settings.MEDIA_DIR, uuid.uuid4().hex)
    os.makedirs(task_dir, exist_ok=True)

    if _is_cn_site(url):
        return _download_with_youget(url, task_dir)
    return _download_with_ytdlp(url, task_dir)


def _download_with_youget(url: str, task_dir: str) -> str:
    """Download using you-get (better for B站, 抖音, etc.)"""
    cmd = [
        "you-get", "--no-caption", "--format=worstaudio",
        "-o", task_dir, "-O", "downloaded",
        url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        # Fallback to yt-dlp
        return _download_with_ytdlp(url, task_dir)

    files = os.listdir(task_dir)
    if not files:
        raise RuntimeError("you-get: no output file")

    return os.path.join(task_dir, files[0])


def _download_with_ytdlp(url: str, task_dir: str) -> str:
    """Download using yt-dlp."""
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(task_dir, "%(title)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "cookiesfrombrowser": ("edge",),
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://www.bilibili.com/",
        },
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
    except Exception:
        opts = dict(ydl_opts)
        opts.pop("cookiesfrombrowser", None)
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

    if not os.path.exists(filename):
        files = os.listdir(task_dir)
        if not files:
            raise RuntimeError("Download failed: no output file")
        filename = os.path.join(task_dir, files[0])

    return filename


def extract_audio(input_path: str) -> str:
    """Extract audio to mp3. For audio files, copies as-is. For video, uses ffmpeg.

    Returns the path to the audio file usable for both playback and ASR.
    """
    output_dir = os.path.dirname(input_path)

    if is_audio_file(input_path):
        ext = os.path.splitext(input_path)[1].lower()
        output_path = os.path.join(output_dir, f"audio{ext}")
        shutil.copy2(input_path, output_path)
        return output_path

    output_path = os.path.join(output_dir, "audio.mp3")

    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-vn",
        "-acodec", "libmp3lame",
        "-ar", "16000",
        "-ac", "1",
        "-b:a", "64k",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg audio extraction failed: {result.stderr}")
    return output_path
