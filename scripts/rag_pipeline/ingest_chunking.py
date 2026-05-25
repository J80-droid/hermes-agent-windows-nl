"""Semantische document-chunking voor RAG-ingest."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

DEFAULT_MAX_WORDS = 400

_CODE_FENCE = re.compile(r"```[a-zA-Z0-9_+-]*\s*\n?([\s\S]*?)```", re.MULTILINE)
_MD_HEADING_SPLIT = re.compile(r"(?m)^(?=(?:#{2,6}\s))")
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?…])\s+")


def _word_count(text: str) -> int:
    return len(text.split())


def _iter_fenced_and_prose(text: str):
    """Wisselt tussen ruwe tekst (False) en volledige ```-fence inclusief backticks (True)."""
    last = 0
    for m in _CODE_FENCE.finditer(text):
        if m.start() > last:
            yield text[last:m.start()], False
        yield m.group(0), True
        last = m.end()
    if last < len(text):
        yield text[last:], False


def _pack_units(units: list[str], max_words: int, joiner: str) -> list[str]:
    out: list[str] = []
    buf: list[str] = []
    wc = 0
    for u in units:
        u = u.strip()
        if not u:
            continue
        uw = _word_count(u)
        if uw > max_words:
            if buf:
                out.append(joiner.join(buf))
                buf = []
                wc = 0
            out.extend(_split_oversized(u, max_words))
        elif wc + uw > max_words:
            if buf:
                out.append(joiner.join(buf))
            buf = [u]
            wc = uw
        else:
            buf.append(u)
            wc += uw
    if buf:
        out.append(joiner.join(buf))
    return out


def _split_oversized(unit: str, max_words: int) -> list[str]:
    parts = [p.strip() for p in _SENTENCE_SPLIT.split(unit) if p.strip()]
    if len(parts) <= 1:
        return _split_by_lines_or_words(unit, max_words)
    return _pack_units(parts, max_words, joiner=" ")


def _split_by_lines_or_words(unit: str, max_words: int) -> list[str]:
    lines = [ln.strip() for ln in unit.split("\n") if ln.strip()]
    if len(lines) > 1:
        return _pack_units(lines, max_words, joiner="\n")
    words = unit.split()
    if not words:
        return []
    out: list[str] = []
    for i in range(0, len(words), max_words):
        chunk = " ".join(words[i : i + max_words])
        if chunk.strip():
            out.append(chunk)
    return out


def _chunk_prose(text: str, max_words: int) -> list[str]:
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        return []
    units: list[str] = []
    for section in _MD_HEADING_SPLIT.split(text):
        section = section.strip()
        if not section:
            continue
        for para in re.split(r"\n{2,}", section):
            p = para.strip()
            if p:
                units.append(p)
    return _pack_units(units, max_words, joiner="\n\n")


def _chunk_code_fence(block: str, max_words: int) -> list[str]:
    block = block.strip()
    if not block:
        return []
    if _word_count(block) <= max_words:
        return [block]
    inner_parts = [p.strip() for p in block.split("\n\n") if p.strip()]
    if len(inner_parts) > 1:
        return _pack_units(inner_parts, max_words, joiner="\n\n")
    return _split_by_lines_or_words(block, max_words)


def chunk_row_id(relative_source: str, chunk_index: int) -> str:
    """Deterministische sleutel: zelfde bron + chunk-index => zelfde id (veilig voor upsert)."""
    rel = Path(relative_source).as_posix()
    return hashlib.sha256(f"{rel}\0#{chunk_index}".encode("utf-8")).hexdigest()


def _chunks_for_segment(segment: str, *, is_fence: bool, max_words: int) -> list[str]:
    if is_fence:
        return _chunk_code_fence(segment, max_words)
    return _chunk_prose(segment, max_words)


def semantic_chunk_document(text: str, max_words: int = DEFAULT_MAX_WORDS) -> list[str]:
    """
    Splits tekst op natuurlijke grenzen: fenced code, Markdown-koppen (##+),
    alinea's (dubbele newline), zinnen en zo nodig regels/woorden.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    chunks: list[str] = []
    for segment, is_fence in _iter_fenced_and_prose(text):
        chunks.extend(_chunks_for_segment(segment, is_fence=is_fence, max_words=max_words))
    return [c for c in chunks if c.strip()]
