"""Hermes RAG ingest terminal UI (aligned with install-jamel.ps1 styling)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

def _env_truthy(name: str) -> bool:
    v = os.environ.get(name)
    if v is None or str(v).strip() == "":
        return False
    return str(v).strip().lower() not in ("0", "false", "no", "n", "off")


def _tty_out() -> bool:
    return sys.stdout.isatty()


def _tty_err() -> bool:
    return sys.stderr.isatty()


def _use_color() -> bool:
    if "NO_COLOR" in os.environ:
        return False
    if _env_truthy("FORCE_COLOR") or _env_truthy("HERMES_FORCE_COLOR"):
        return True
    return _tty_out() or _tty_err()


USE_COLOR = _use_color()
LOG_IO = sys.stderr if _tty_err() else sys.stdout if _tty_out() else sys.stderr
TTY_PROGRESS = _tty_out() or _tty_err()
VERBOSE = _env_truthy("HERMES_RAG_VERBOSE")

if USE_COLOR:
    C_GOLD = "\033[93m"
    C_AMBER = "\033[33m"
    C_CYAN = "\033[96m"
    C_GREEN = "\033[92m"
    C_YELLOW = "\033[93m"
    C_RED = "\033[91m"
    C_DIM = "\033[2m"
    C_RESET = "\033[0m"
else:
    C_GOLD = C_AMBER = C_CYAN = C_GREEN = C_YELLOW = C_RED = C_DIM = C_RESET = ""

try:
    import colorama

    if USE_COLOR:
        colorama.init()
except ImportError:
    pass

try:
    from tqdm import tqdm as tqdm_lib
except ImportError:

    class _TqdmShim:
        __slots__ = ("disable", "fp", "n", "total")

        def __init__(self, total: int = 0, **_kwargs: object) -> None:
            self.disable = True
            self.fp = None
            self.n = 0
            self.total = total

        def update(self, n: int = 1) -> None:
            self.n += n

        def set_postfix_str(self, *_a: object, **_k: object) -> None:
            return None

        def close(self) -> None:
            return None

    def tqdm_lib(*args: object, **kwargs: object):  # type: ignore[misc]
        if args:
            return args[0]
        return _TqdmShim(**kwargs)


def print_banner(*, total_files: int, scan_total: int, db_path: str, workers: int) -> None:
    line = "═" * 58
    print(f"{C_GOLD}{line}{C_RESET}", file=LOG_IO)
    print(
        f"{C_GOLD}  HERMES RAG — LanceDB kennisindex{C_RESET}",
        file=LOG_IO,
    )
    print(
        f"{C_AMBER}  Bronnen: {total_files} te verwerken (scan: {scan_total})  |  workers: {workers}{C_RESET}",
        file=LOG_IO,
    )
    print(f"{C_DIM}  Database: {db_path}{C_RESET}", file=LOG_IO)
    print(f"{C_GOLD}{line}{C_RESET}", file=LOG_IO)
    print("", file=LOG_IO)


def print_phase(title: str) -> None:
    print(f"{C_AMBER}  ── {title} ──{C_RESET}", file=LOG_IO)


def info(message: str) -> None:
    print(f"{C_CYAN}[INFO]{C_RESET} {message}", file=LOG_IO)


def ok(message: str) -> None:
    print(f"{C_GREEN}[OK]{C_RESET} {message}", file=LOG_IO)


def warn(message: str) -> None:
    print(f"{C_YELLOW}[WARN]{C_RESET} {message}", file=LOG_IO)


def error(message: str) -> None:
    print(f"{C_RED}[ERROR]{C_RESET} {message}", file=LOG_IO)


def create_file_progress(total: int):
    """tqdm with explicit n/total (e.g. 3/1669) and Hermes gold bar."""
    fp = sys.stderr if _tty_err() else sys.stdout if _tty_out() else sys.stderr
    desc = f"{C_GOLD}RAG Index{C_RESET}" if USE_COLOR else "RAG Index"
    bar_kw: dict = {
        "total": total,
        "desc": desc,
        "unit": "bron",
        "disable": not TTY_PROGRESS,
        "file": fp,
        "dynamic_ncols": True,
        "bar_format": (
            "{desc} {percentage:3.0f}%|{bar:28}| {n_fmt}/{total_fmt} "
            "[{elapsed}<{remaining}]{postfix}"
        ),
    }
    if USE_COLOR:
        bar_kw["colour"] = "yellow"
    return tqdm_lib(**bar_kw)


def log_during_progress(pbar: object, message: str, *, force: bool = False) -> None:
    """Write without breaking the progress bar. Skip detail unless verbose."""
    if not force and not VERBOSE and "[WARN]" not in message and "[ERROR]" not in message:
        if "[OK]" in message or "Kennisbron succesvol" in message:
            pass  # always show per-file OK in compact mode
        elif "[INFO]" in message or "[CONVERTEREN]" in message or "[EMBEDDEN]" in message or "[LEZEN]" in message:
            return
    fp = getattr(pbar, "fp", None) or LOG_IO
    if hasattr(pbar, "set_postfix_str") and not getattr(pbar, "disable", True):
        try:
            tqdm_lib.write(message, file=fp)
        except Exception:
            print(message, file=fp)
    else:
        print(message, file=fp)


def set_progress_file(pbar: object, file_path: Path, root: Path, phase: str = "") -> None:
    try:
        rel = file_path.relative_to(root)
        label = rel.as_posix()
    except ValueError:
        label = str(file_path)
    if len(label) > 56:
        label = "…" + label[-55:]
    prefix = f"{phase} " if phase else ""
    styled = f"{prefix}{label}"
    if C_DIM:
        styled = f"{C_DIM}{styled}{C_RESET}"
    if hasattr(pbar, "set_postfix_str"):
        pbar.set_postfix_str(styled, refresh=True)


def set_progress_phase_count(pbar: object, phase: str, current: int, total: int) -> None:
    if hasattr(pbar, "set_postfix_str"):
        text = f"{phase} {current}/{total}"
        if C_AMBER:
            text = f"{C_AMBER}{text}{C_RESET}"
        pbar.set_postfix_str(text, refresh=True)


def compact_ok_line(relative_source: str, chunk_count: int | None = None) -> str:
    extra = f" ({chunk_count} chunks)" if chunk_count else ""
    return (
        f"{C_GREEN}[RAG]{C_RESET} {C_GREEN}✓{C_RESET} {relative_source}{C_DIM}{extra}{C_RESET}"
    )
