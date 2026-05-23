"""Normalize assistant markdown for institutional layout (headings, labels, lists)."""

from __future__ import annotations

import re

# Heading with trailing prose on the same line (Dutch/English sentence starters).
_HEADING_INLINE_BODY_RE = re.compile(
    r"^(?P<prefix>\s{0,3}#{1,6}\s+)(?P<title>.+?)\s+"
    r"(?P<body>(?:Dit|Het|De|Een|The|This|These|When|If)\s.+)$",
    re.MULTILINE | re.IGNORECASE,
)

# Bold label with value on same line: "**Label:** value" -> label line + blank + value
_LABEL_INLINE_VALUE_RE = re.compile(
    r"^(\s*(?:[-*+]\s+)?)\*\*([^*\n]+?):\*\*\s+(\S.+)$",
    re.MULTILINE,
)

# Blank line before markdown headings (not at document start).
_SECTION_BREAK_BEFORE_HEADING_RE = re.compile(
    r"(?<!\n\n)(?<=\S\n)(?P<hash>#{1,6}\s)",
    re.MULTILINE,
)

# ACTIEPLAN-style: "1 Stap 1: Title" or "2 Stap 2: Title"
_NUMBERED_STEP_HEADING_RE = re.compile(
    r"^(?P<num>\d+)\s+Stap\s+(?P<step>\d+)\s*:\s*(?P<title>.+?)\s*$",
    re.MULTILINE | re.IGNORECASE,
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
        return f"{lead}**{label}:**\n{value}"

    out = _LABEL_INLINE_VALUE_RE.sub(_split_label, out)

    return out


def ensure_section_breaks(text: str) -> str:
    """Insert a blank line before each markdown heading that follows body text."""
    if not text or not text.strip():
        return text or ""

    out = _SECTION_BREAK_BEFORE_HEADING_RE.sub(r"\n\n\g<hash>", text)
    out = re.sub(
        r"(?<!\n\n)(\n)(?P<h>#{1,6}\s)",
        r"\n\n\g<h>",
        out,
    )
    return collapse_extra_blank_lines(out)


def normalize_numbered_headings(text: str) -> str:
    """Convert 'N Stap N: Title' lines to ## markdown headings."""
    if not text or not text.strip():
        return text or ""

    def _step_heading(match: re.Match[str]) -> str:
        title = match.group("title").strip()
        return f"## Stap {match.group('step')}: {title}"

    return _NUMBERED_STEP_HEADING_RE.sub(_step_heading, text)


def collapse_extra_blank_lines(text: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", text or "")


def normalize_assistant_markdown(
    text: str,
    *,
    normalize_numbered_headings_flag: bool = True,
) -> str:
    """Apply institutional typography normalizers before Rich/Ink render."""
    out = text or ""
    out = ensure_heading_line_breaks(out)
    if normalize_numbered_headings_flag:
        out = normalize_numbered_headings(out)
    out = ensure_section_breaks(out)
    return collapse_extra_blank_lines(out)
