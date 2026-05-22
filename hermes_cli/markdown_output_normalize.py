"""Normalize assistant markdown for institutional layout (headings, labels, lists)."""

from __future__ import annotations

import re

# Heading with trailing prose on the same line (Dutch/English sentence starters).
_HEADING_INLINE_BODY_RE = re.compile(
    r"^(?P<prefix>\s{0,3}#{1,6}\s+)(?P<title>.+?)\s+"
    r"(?P<body>(?:Dit|Het|De|Een|Bij|In|Op|Na|Voor|The|This|These|When|If)\s.+)$",
    re.MULTILINE | re.IGNORECASE,
)

# Bold label with value on same line: "**Label:** value" -> label line + blank + value
_LABEL_INLINE_VALUE_RE = re.compile(
    r"^(\s*(?:[-*+]\s+)?)\*\*([^*\n]+?):\*\*\s+(\S.+)$",
    re.MULTILINE,
)

# List marker glued to long content without following blank line (conservative)
_LIST_MARKER_GLUE_RE = re.compile(
    r"^(\s*[-*+]\s+)(?!\[(?: |x|X)\]\s)(.+)$",
    re.MULTILINE,
)


def ensure_heading_line_breaks(text: str) -> str:
    """Split headings and **Label:** lines so body text starts on the next line."""
    if not text or not text.strip():
        return text or ""

    out = text

    def _split_heading(match: re.Match[str]) -> str:
        prefix = match.group("prefix")
        title = match.group("title").strip()
        body = match.group("body").strip()
        return f"{prefix}{title}\n\n{body}"

    out = _HEADING_INLINE_BODY_RE.sub(_split_heading, out)

    def _split_label(match: re.Match[str]) -> str:
        lead = match.group(1)
        label = match.group(2).strip()
        value = match.group(3).strip()
        return f"{lead}**{label}:**\n\n{value}"

    out = _LABEL_INLINE_VALUE_RE.sub(_split_label, out)

    return out


def normalize_assistant_markdown(text: str) -> str:
    """Apply institutional typography normalizers before Rich/Ink render."""
    return ensure_heading_line_breaks(text or "")
