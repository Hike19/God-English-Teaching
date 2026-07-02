import os
import uuid
import subprocess
import yt_dlp
from ..config import settings


def download_media(url: str) -> str:
    """Download media from URL using yt-dlp. Returns the file path."""
    task_dir = os.path.join(settings.MEDIA_DIR, uuid.uuid4().hex)
    os.makedirs(task_dir, exist_ok=True)

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(task_dir, "%(title)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)

    if not os.path.exists(filename):
        files = os.listdir(task_dir)
        if not files:
            raise RuntimeError("Download failed: no output file found")
        filename = os.path.join(task_dir, files[0])

    return filename


def extract_audio(input_path: str) -> str:
    """Extract audio from video/audio file to mp3 using ffmpeg. Returns the mp3 path."""
    output_dir = os.path.dirname(input_path)
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
