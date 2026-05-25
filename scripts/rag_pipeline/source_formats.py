"""Centrale extensiematrix voor RAG-ingest — enige bron van waarheid.

Wijzig alleen hier (en `ingest_config.py` voor uitsluitingen); `ingest.py` en
`audio_transcriber.py` importeren deze sets.
"""

from __future__ import annotations

import os
from pathlib import Path


# --- Platte tekst (UTF-8 in ingest) ------------------------------------------

PLAIN_SUFFIXES: frozenset[str] = frozenset(
    {
        ".txt",
        ".md",
        ".markdown",
        ".json",
        ".jsonl",
        ".log",
        ".csv",
        ".tsv",
        ".yaml",
        ".yml",
        ".toml",
        ".ini",
        ".cfg",
        ".rst",
        ".adoc",
        ".asciidoc",
        # Ondertitels: bestaand transcript, geen Whisper
        ".vtt",
        ".srt",
        ".sbv",
    }
)

# --- MarkItDown (kantoor, web, archief, beeld) -------------------------------
# Vereist: pip install "markitdown[all]" (+ optioneel OCR/vision voor scans)

MARKITDOWN_SUFFIXES: frozenset[str] = frozenset(
    {
        # PDF & web
        ".pdf",
        ".html",
        ".htm",
        ".xhtml",
        ".xml",
        ".rss",
        ".atom",
        # Microsoft Word
        ".docx",
        ".doc",
        ".docm",
        ".dotx",
        ".dotm",
        ".rtf",
        # Microsoft Excel
        ".xlsx",
        ".xls",
        ".xlsm",
        ".xlsb",
        # Microsoft PowerPoint
        ".pptx",
        ".ppt",
        ".pptm",
        ".ppsx",
        ".pps",
        # Outlook / e-mail
        ".msg",
        ".eml",
        # OpenDocument (LibreOffice) — MarkItDown probeert conversie; bij falen [WARN]
        ".odt",
        ".ods",
        ".odp",
        # Overig MarkItDown
        ".epub",
        ".ipynb",
        ".zip",
        # Afbeeldingen (OCR/beschrijving met markitdown[all] + vision-deps)
        ".png",
        ".jpg",
        ".jpeg",
        ".jpe",
        ".jfif",
        ".webp",
        ".gif",
        ".bmp",
        ".tif",
        ".tiff",
        ".heic",
        ".heif",
    }
)

# --- Audio (faster-whisper) ----------------------------------------------------

AUDIO_SUFFIXES: frozenset[str] = frozenset(
    {
        ".m4a",
        ".mp3",
        ".wav",
        ".ogg",
        ".flac",
        ".aac",
        ".wma",
        ".aiff",
        ".aif",
        ".au",
        ".opus",
        ".mka",
    }
)

# --- Video (ffmpeg → whisper) --------------------------------------------------

VIDEO_SUFFIXES: frozenset[str] = frozenset(
    {
        ".mp4",
        ".mov",
        ".mkv",
        ".webm",
        ".m4v",
        ".avi",
        ".wmv",
        ".mpeg",
        ".mpg",
        ".3gp",
        ".3g2",
        ".flv",
        ".ogv",
    }
)

MEDIA_SUFFIXES: frozenset[str] = AUDIO_SUFFIXES | VIDEO_SUFFIXES

ALL_INDEXED_SUFFIXES: frozenset[str] = PLAIN_SUFFIXES | MARKITDOWN_SUFFIXES | MEDIA_SUFFIXES


def supported_extension_globs() -> list[str]:
    """Glob-patronen voor Path.rglob, gesorteerd voor stabiele scans."""
    return [f"*{ext}" for ext in sorted(ALL_INDEXED_SUFFIXES)]


_SKIP_DIR_NAMES_CF = frozenset(
    {
        ".git",
        ".svn",
        ".hg",
        "node_modules",
        "__pycache__",
        ".venv",
        "venv",
        ".tox",
        ".mypy_cache",
        ".pytest_cache",
        ".idea",
        ".vs",
        "dist",
        "build",
        "_PROBLEMATISCHE_BESTANDEN",
    }
)


def _should_prune_dir(name: str) -> bool:
    return name.casefold() in _SKIP_DIR_NAMES_CF


def collect_indexed_files(root: Path) -> list[Path]:
    """Single tree walk: filter op ALL_INDEXED_SUFFIXES (geen 70+ rglob-passes)."""
    seen: set[object] = set()
    out: list[Path] = []
    try:
        root = root.resolve()
    except OSError:
        return []

    def _walk(dir_path: Path) -> None:
        try:
            with os.scandir(dir_path) as entries:
                for entry in entries:
                    if entry.is_symlink():
                        continue
                    if entry.is_dir(follow_symlinks=False):
                        if not _should_prune_dir(entry.name):
                            _walk(Path(entry.path))
                        continue
                    if not entry.is_file(follow_symlinks=False):
                        continue
                    path = Path(entry.path)
                    if path.suffix.lower() not in ALL_INDEXED_SUFFIXES:
                        continue
                    try:
                        key = path.resolve()
                    except OSError:
                        key = path
                    if key in seen:
                        continue
                    seen.add(key)
                    out.append(path)
        except OSError:
            return

    if root.is_dir():
        _walk(root)
    out.sort(key=lambda p: str(p).casefold())
    return out


def route_for_suffix(suffix: str) -> str:
    """Retourneert 'plain', 'markitdown', 'media' of 'unknown'."""
    s = suffix.lower()
    if s in PLAIN_SUFFIXES:
        return "plain"
    if s in MARKITDOWN_SUFFIXES:
        return "markitdown"
    if s in MEDIA_SUFFIXES:
        return "media"
    return "unknown"
