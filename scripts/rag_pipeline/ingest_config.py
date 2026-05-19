"""Ingest-uitsluitingen en limieten (omgevingsvariabelen)."""

from __future__ import annotations

import os
from pathlib import Path

# Mappen die nooit gescand worden (padsegment, case-insensitive op Windows)
SKIP_PATH_DIR_NAMES: frozenset[str] = frozenset(
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
    }
)

# Bestandsnaam-prefixen (Office lock-bestanden)
SKIP_NAME_PREFIXES: tuple[str, ...] = ("~$",)

# Extensies die nooit geïndexeerd worden (ook als ze per ongeluk in bron staan)
SKIP_SUFFIXES: frozenset[str] = frozenset(
    {
        ".exe",
        ".dll",
        ".so",
        ".dylib",
        ".bin",
        ".iso",
        ".img",
        ".dmg",
        ".msi",
        ".msp",
        ".cab",
        ".dat",
        ".db",
        ".sqlite",
        ".sqlite3",
        ".parquet",
        ".feather",
        ".arrow",
        ".pkl",
        ".pickle",
        ".pt",
        ".pth",
        ".onnx",
        ".wasm",
        ".class",
        ".jar",
        ".war",
        ".deb",
        ".rpm",
        ".7z",
        ".rar",
        ".gz",
        ".bz2",
        ".xz",
        ".tar",
        ".lock",
        ".bak",
        ".tmp",
        ".temp",
        ".swp",
        ".swo",
    }
)


def max_file_bytes() -> int | None:
    """Max. bestandsgrootte; None = geen limiet. Zet HERMES_RAG_MAX_FILE_MB (default 150)."""
    raw = (os.environ.get("HERMES_RAG_MAX_FILE_MB") or "150").strip()
    if raw.lower() in ("0", "none", "off", "unlimited", ""):
        return None
    try:
        mb = float(raw)
    except ValueError:
        mb = 150.0
    if mb <= 0:
        return None
    return int(mb * 1024 * 1024)


def should_skip_ingest_path(file_path: Path) -> str | None:
    """Reden om over te slaan, of None als het bestand verwerkt mag worden."""
    name = file_path.name
    for prefix in SKIP_NAME_PREFIXES:
        if name.startswith(prefix):
            return "office-lock"
    suf = file_path.suffix.lower()
    if suf in SKIP_SUFFIXES:
        return f"uitgesloten-extensie{suf}"
    for part in file_path.parts:
        if part.casefold() in {d.casefold() for d in SKIP_PATH_DIR_NAMES}:
            return f"map-{part}"
    limit = max_file_bytes()
    if limit is not None:
        try:
            size = file_path.stat().st_size
        except OSError:
            return "stat-fout"
        if size > limit:
            return f"te-groot-{size}"
    return None


def filter_ingest_candidates(paths: list[Path]) -> tuple[list[Path], dict[str, int]]:
    """Filtert scan-resultaten; retourneert (behouden, tellingen per skip-reden)."""
    kept: list[Path] = []
    skipped: dict[str, int] = {}
    for p in paths:
        reason = should_skip_ingest_path(p)
        if reason is None:
            kept.append(p)
            continue
        key = reason.split("-", 1)[0] if reason else "overig"
        skipped[key] = skipped.get(key, 0) + 1
    return kept, skipped
