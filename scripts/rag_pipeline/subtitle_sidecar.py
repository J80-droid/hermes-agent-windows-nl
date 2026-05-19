"""Ondertitel-sidecars (.vtt/.srt) vóór Whisper voor media."""

from __future__ import annotations

import re
from pathlib import Path

from source_formats import MEDIA_SUFFIXES

SUBTITLE_SUFFIXES: frozenset[str] = frozenset({".vtt", ".srt", ".sbv"})

_VTT_TIMING = re.compile(
    r"^\d{2}:\d{2}:\d{2}\.\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}\.\d{3}\s*$"
)
_SRT_TIMING = re.compile(
    r"^\d{2}:\d{2}:\d{2},\d{3}\s*-->\s*\d{2}:\d{2}:\d{2},\d{3}\s*$"
)


def _sidecar_candidates(media_path: Path) -> list[Path]:
    stem = media_path.stem
    parent = media_path.parent
    names: list[str] = []
    for ext in SUBTITLE_SUFFIXES:
        names.append(f"{stem}{ext}")
        names.append(f"{stem}.nl{ext}")
        names.append(f"{stem}.en{ext}")
    return [parent / n for n in names]


def find_subtitle_sidecar(media_path: Path) -> Path | None:
    """Eerste niet-lege ondertitel naast media, of None."""
    for candidate in _sidecar_candidates(media_path):
        if not candidate.is_file():
            continue
        try:
            if candidate.stat().st_size == 0:
                continue
        except OSError:
            continue
        return candidate
    return None


def subtitle_to_plain_text(path: Path) -> str:
    """Zet .vtt/.srt om naar doorlopende tekst (zonder timing/metadata)."""
    raw = path.read_text(encoding="utf-8", errors="replace")
    lines: list[str] = []
    for line in raw.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.upper() == "WEBVTT":
            continue
        if s.isdigit():
            continue
        if _VTT_TIMING.match(s) or _SRT_TIMING.match(s):
            continue
        if s.startswith("NOTE") or s.startswith("STYLE") or s.startswith("REGION"):
            continue
        lines.append(s)
    return "\n".join(lines)


def read_media_text_via_sidecar(media_path: Path) -> tuple[str | None, Path | None]:
    """Lees transcript uit sidecar; (tekst, pad) of (None, None)."""
    sidecar = find_subtitle_sidecar(media_path)
    if sidecar is None:
        return None, None
    text = subtitle_to_plain_text(sidecar)
    if not text.strip():
        return None, sidecar
    return text, sidecar


def _subtitle_covered_by_media(media_keys: set[tuple[object, str]], sub_path: Path) -> bool:
    parent_key = sub_path.parent.resolve()
    stem = sub_path.stem.casefold()
    if (parent_key, stem) in media_keys:
        return True
    for lang in (".nl", ".en"):
        if stem.endswith(lang):
            base = stem[: -len(lang)]
            if (parent_key, base) in media_keys:
                return True
    return False


def filter_subtitles_indexed_via_media(files: list[Path]) -> tuple[list[Path], int]:
    """Laat losse ondertitels weg als media met dezelfde stem in dezelfde map staat."""
    media_keys = {
        (p.parent.resolve(), p.stem.casefold())
        for p in files
        if p.suffix.lower() in MEDIA_SUFFIXES
    }
    out: list[Path] = []
    skipped = 0
    for p in files:
        if p.suffix.lower() not in SUBTITLE_SUFFIXES:
            out.append(p)
            continue
        if _subtitle_covered_by_media(media_keys, p):
            skipped += 1
        else:
            out.append(p)
    return out, skipped
