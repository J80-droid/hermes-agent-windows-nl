"""Incrementele ingest-staat (mtime/grootte/content-fingerprint) naast LanceDB."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from kb_schema import DB_PATH

STATE_VERSION = 1
STATE_BASENAME = ".hermes_rag_ingest_state.json"


def _env_truthy(name: str, *, default: str = "1") -> bool:
    raw = (os.environ.get(name) if os.environ.get(name) is not None else default).strip()
    return raw.lower() not in ("0", "false", "no", "n", "off")


def incremental_ingest_enabled() -> bool:
    """Uit met HERMES_RAG_FORCE_FULL=1; standaard aan (HERMES_RAG_INCREMENTAL=1)."""
    if _env_truthy("HERMES_RAG_FORCE_FULL", default="0"):
        return False
    return _env_truthy("HERMES_RAG_INCREMENTAL", default="1")


def orphan_cleanup_enabled() -> bool:
    return _env_truthy("HERMES_RAG_ORPHAN_CLEANUP", default="1")


def checkpoint_interval() -> int:
    """Schrijf ingest-staat elke N succesvolle bronnen (0 = alleen bij save()/einde)."""
    raw = (os.environ.get("HERMES_RAG_STATE_CHECKPOINT") or "25").strip()
    try:
        n = int(raw)
    except ValueError:
        n = 25
    return max(0, n)


def _hash_full_max_bytes() -> int:
    raw = (os.environ.get("HERMES_RAG_HASH_FULL_MAX_MB") or "32").strip()
    try:
        mb = float(raw)
    except ValueError:
        mb = 32.0
    if mb <= 0:
        return 0
    return int(mb * 1024 * 1024)


def state_file_path() -> Path:
    return Path(DB_PATH) / STATE_BASENAME


def normalize_relative_source(relative_source: str) -> str:
    """Eenduidige sleutel voor state/LanceDB (forward slashes, ook op Windows)."""
    return str(relative_source).replace("\\", "/")


def file_content_fingerprint(path: Path) -> str:
    """SHA-256 van inhoud (kleine bestanden) of deterministische fp bij grote bestanden."""
    st = path.stat()
    full_max = _hash_full_max_bytes()
    if full_max == 0 or st.st_size > full_max:
        return hashlib.sha256(f"fp:{st.st_size}:{st.st_mtime_ns}".encode()).hexdigest()
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            block = f.read(1 << 20)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


class IngestState:
    def __init__(self, entries: dict[str, dict[str, Any]] | None = None) -> None:
        self.entries: dict[str, dict[str, Any]] = entries or {}
        self._pending_checkpoint: int = 0

    @classmethod
    def load(cls) -> IngestState:
        p = state_file_path()
        if not p.is_file():
            return cls()
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return cls()
        if data.get("version") != STATE_VERSION:
            return cls()
        raw = data.get("sources")
        if not isinstance(raw, dict):
            return cls()
        entries = {
            normalize_relative_source(str(k)): dict(v)
            for k, v in raw.items()
            if isinstance(v, dict)
        }
        return cls(entries=entries)

    def save(self) -> None:
        p = state_file_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        payload = {"version": STATE_VERSION, "sources": self.entries}
        text = json.dumps(payload, indent=2, ensure_ascii=False)
        fd, tmp = tempfile.mkstemp(dir=p.parent, suffix=".tmp", prefix=STATE_BASENAME + ".")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(text)
            os.replace(tmp, p)
        except Exception:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

    def needs_processing(self, relative_source: str, path: Path) -> bool:
        if not incremental_ingest_enabled():
            return True
        rel = normalize_relative_source(relative_source)
        prev = self.entries.get(rel)
        if prev is None:
            return True
        try:
            st = path.stat()
        except OSError:
            return True
        if int(prev.get("mtime_ns", -1)) != st.st_mtime_ns or int(prev.get("size", -1)) != st.st_size:
            fp = file_content_fingerprint(path)
            return prev.get("content_hash") != fp
        return False

    def _entry_for_path(self, path: Path, *, chunk_count: int) -> dict[str, Any]:
        st = path.stat()
        return {
            "mtime_ns": st.st_mtime_ns,
            "size": st.st_size,
            "content_hash": file_content_fingerprint(path),
            "chunk_count": chunk_count,
        }

    def record_success(
        self,
        relative_source: str,
        path: Path,
        *,
        chunk_count: int,
        checkpoint: bool = True,
    ) -> None:
        rel = normalize_relative_source(relative_source)
        self.entries[rel] = self._entry_for_path(path, chunk_count=chunk_count)
        if checkpoint:
            self.maybe_checkpoint_save()

    def maybe_checkpoint_save(self) -> None:
        """Periodieke persist zodat een crash/OOM niet alle voortgang wist."""
        every = checkpoint_interval()
        if every <= 0:
            return
        self._pending_checkpoint += 1
        if self._pending_checkpoint >= every:
            self.save()
            self._pending_checkpoint = 0

    def bootstrap_entry(self, relative_source: str, path: Path, *, chunk_count: int = 0) -> bool:
        """Registreer bron vanuit bestaande index (geen LanceDB-herindex)."""
        try:
            rel = normalize_relative_source(relative_source)
            self.entries[rel] = self._entry_for_path(path, chunk_count=chunk_count)
            return True
        except OSError:
            return False

    def prune_removed_sources(self, current_sources: set[str]) -> list[str]:
        normalized_current = {normalize_relative_source(s) for s in current_sources}
        removed = [k for k in self.entries if k not in normalized_current]
        for k in removed:
            del self.entries[k]
        return removed
