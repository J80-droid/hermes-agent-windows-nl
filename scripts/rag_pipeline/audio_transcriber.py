"""Lokale audio/video-transcriptie via faster-whisper voor RAG-ingestie.

Gebruikt hetzelfde faster-whisper-pakket dat al in pyproject.toml staat
(zie tools/transcription_tools.py).  Extracteert audio uit videobestanden
via ffmpeg (vereiste voor faster-whisper bij .m4a/.mp4 etc.).

Configuratie via omgevingsvariabelen:
  HERMES_WHISPER_MODEL       — modelgrootte (tiny/base/small/medium/large-v3)
  HERMES_WHISPER_DEVICE      — cpu of cuda
  HERMES_WHISPER_COMPUTE_TYPE — int8, float16, int8_float16
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

from source_formats import AUDIO_SUFFIXES, VIDEO_SUFFIXES


# ---------------------------------------------------------------------------
# Interne helpers
# ---------------------------------------------------------------------------

def _has_cuda() -> bool:
    """Snelle heuristiek: is CUDA beschikbaar zonder PyTorch te importeren?"""
    try:
        import importlib.util

        if importlib.util.find_spec("torch") is None:
            return False
        import torch

        return torch.cuda.is_available()
    except Exception:
        return False


# Configuratie (env vars) — na _has_cuda() omdat we die hier nodig hebben
_WHISPER_MODEL = (os.getenv("HERMES_WHISPER_MODEL") or "medium").strip().lower()
_WHISPER_DEVICE = (os.getenv("HERMES_WHISPER_DEVICE") or "auto").strip().lower()
_WHISPER_COMPUTE = (os.getenv("HERMES_WHISPER_COMPUTE_TYPE") or "auto").strip().lower()

if _WHISPER_DEVICE == "auto":
    _WHISPER_DEVICE = "cuda" if _has_cuda() else "cpu"

if _WHISPER_COMPUTE == "auto":
    _WHISPER_COMPUTE = "float16" if _WHISPER_DEVICE == "cuda" else "int8"


def _ffmpeg_extract_audio(video_path: Path, output_wav: Path) -> None:
    """Extraheert audio uit video via ffmpeg (vereist voor mp4/mov/mkv/webm)."""
    cmd = [
        "ffmpeg",
        "-y",  # overwrite
        "-i",
        str(video_path),
        "-vn",  # geen video
        "-acodec",
        "pcm_s16le",
        "-ar",
        "16000",
        "-ac",
        "1",
        str(output_wav),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg audio-extractie mislukt voor {video_path}: {result.stderr[:500]}")


def _is_video(suffix: str) -> bool:
    return suffix.lower() in VIDEO_SUFFIXES


def _is_audio(suffix: str) -> bool:
    return suffix.lower() in AUDIO_SUFFIXES


def _model_cache_dir() -> Path:
    """Cache-map voor Whisper-modellen (gelijk aan tools/transcription_tools.py)."""
    cache = Path.home() / ".cache" / "whisper"
    cache.mkdir(parents=True, exist_ok=True)
    return cache


# ---------------------------------------------------------------------------
# Publieke API
# ---------------------------------------------------------------------------


def transcribe_media_file(
    media_path: Path,
    *,
    model_size: Optional[str] = None,
    language: str = "nl",
) -> str:
    """Transcribeer een audio- of videobestand lokaal via faster-whisper.

    Retourneert de platte transcriptie-tekst.  De caller is verantwoordelijk
    voor het opslaan en opruimen van het .txt-bestand.
    """
    suffix = media_path.suffix

    # --- ffmpeg extractie voor video --------------------------------------
    if _is_video(suffix):
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_wav = Path(tmp.name)
        try:
            _ffmpeg_extract_audio(media_path, tmp_wav)
            audio_path = tmp_wav
        except Exception:
            tmp_wav.unlink(missing_ok=True)
            raise
    else:
        audio_path = media_path

    # --- faster-whisper ---------------------------------------------------
    try:
        from hermes_cli.hardware_backend import load_faster_whisper_model
    except ImportError as exc:
        raise ImportError(
            "faster-whisper is niet geinstalleerd. "
            "Installeer:  uv pip install faster-whisper==1.2.1"
        ) from exc

    size = (model_size or _WHISPER_MODEL).lower()
    preferred = _WHISPER_DEVICE

    model = load_faster_whisper_model(size, preferred_device=preferred)

    segments, info = model.transcribe(str(audio_path), language=language, vad_filter=True)
    parts = [seg.text.strip() for seg in segments if seg.text.strip()]
    transcript = "\n".join(parts)

    # cleanup tijdelijke wav na video-extractie
    if _is_video(suffix):
        tmp_wav.unlink(missing_ok=True)

    return transcript


def write_transcript_to_temp(
    media_path: Path,
    transcript: str,
    *,
    suffix: str = ".transcript.txt",
) -> Path:
    """Schrijf transcriptie naar een tijdelijk bestand naast het originele.

    Het pad bevat een deterministische hash zodat herhaalde runs hetzelfde
    pad produceren (handig voor idempotente upsert-logica in ingest.py).
    """
    base = media_path.stem
    h = hashlib.sha256(str(media_path).encode()).hexdigest()[:8]
    temp_name = f"{base}_{h}{suffix}"
    temp_path = media_path.parent / temp_name
    temp_path.write_text(transcript, encoding="utf-8")
    return temp_path
