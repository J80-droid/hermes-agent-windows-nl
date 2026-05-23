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

# Plain outline: "1. Title" -> ## Title (single segment)
_PLAIN_OUTLINE_H1_RE = re.compile(
    r"^(?P<num>\d+)\.\s+(?P<title>.+?)\s*$",
    re.MULTILINE,
)

# Bold outline: "**1. Title**" or "**2. Functionele Requirements**"
_BOLD_PLAIN_OUTLINE_H1_RE = re.compile(
    r"^\s*\*\*(?P<num>\d+)\.\s+(?P<title>[^*\n]+?)\*\*\s*$",
    re.MULTILINE,
)

# Chapter without dot after number: "2 Functionele Requirements"
_CHAPTER_NUM_SPACE_RE = re.compile(
    r"^(?P<num>\d+)\s+(?P<title>.+?)\s*$",
    re.MULTILINE,
)

# Dotted outline: "1.1 Title" or "1.2.1 Dependencies" -> ### / ####
_DOTTED_OUTLINE_HEADING_RE = re.compile(
    r"^(?P<num>\d+(?:\.\d+)+)\s+(?P<title>.+?)\s*$",
    re.MULTILINE,
)

# Bold dotted: "**1.1 Team Samenstelling**"
_BOLD_DOTTED_OUTLINE_HEADING_RE = re.compile(
    r"^\s*\*\*(?P<num>\d+(?:\.\d+)+)\s+(?P<title>[^*\n]+?)\*\*\s*$",
    re.MULTILINE,
)

# institutional_check on one line with content — force block layout
_INSTITUTIONAL_CHECK_INLINE_RE = re.compile(
    r"^(?P<open><institutional_check>)\s*(?P<body>.*?)(?P<close></institutional_check>)\s*$",
    re.MULTILINE | re.DOTALL | re.IGNORECASE,
)

# Collapse blank line(s) after a heading when the next line is body (not another heading).
_HEADING_TIGHT_TO_BODY_RE = re.compile(
    r"^(?P<h>(?:\s{0,3})#{1,6}\s+[^\n]+)\n\n+(?!(?:\s{0,3}#))(?=\S)",
    re.MULTILINE,
)

# Tables: always pull | rows directly under the heading (common model slip).
_HEADING_TIGHT_BEFORE_TABLE_RE = re.compile(
    r"^(?P<h>(?:\s{0,3})#{1,6}\s+[^\n]+)\n\n+(?=\|)",
    re.MULTILINE,
)

# Same for **Label:** before value (terminal layout: label close to content).
_LABEL_TIGHT_TO_VALUE_RE = re.compile(
    r"^(\s*(?:[-*+]\s+)?\*\*[^*\n]+:\*\*)\n\n+(?=\S)",
    re.MULTILINE,
)

# Dutch imperative starters — usually numbered *list* steps, not chapter titles
_LIST_ITEM_VERB_PREFIX_RE = re.compile(
    r"^(?:doe|do|ga|open|voer|importeer|controleer|kies|zet|voeg|stel|maak|lees|schrijf|"
    r"bewaar|start|stop|gebruik|download|upload|installeer|bekijk|test|verifieer)\b",
    re.IGNORECASE,
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


def tighten_heading_and_label_spacing(text: str) -> str:
    """Single newline after headings/labels before tables, lists, or prose (not before ##)."""
    if not text or not text.strip():
        return text or ""
    out = _HEADING_TIGHT_BEFORE_TABLE_RE.sub(r"\g<h>\n", text)
    out = _HEADING_TIGHT_TO_BODY_RE.sub(r"\g<h>\n", out)
    out = _LABEL_TIGHT_TO_VALUE_RE.sub(r"\1\n", out)
    return out


_HEADING_ONLY_LINE = re.compile(r"^(?:\s{0,3})#{1,6}\s+[^\n]+\s*$")


def coalesce_heading_content_chunks(chunks: list[str]) -> list[str]:
    """Merge isolated '# Title' chunks with the following table/list/prose chunk."""
    if not chunks:
        return chunks
    out: list[str] = []
    i = 0
    while i < len(chunks):
        chunk = chunks[i].strip()
        if i + 1 < len(chunks):
            nxt = chunks[i + 1].strip()
            if _HEADING_ONLY_LINE.match(chunk) and nxt and not re.match(
                r"^(?:\s{0,3})#", nxt
            ):
                out.append(f"{chunk}\n{nxt}")
                i += 2
                continue
        out.append(chunk)
        i += 1
    return out


# Backward-compatible alias
coalesce_heading_table_chunks = coalesce_heading_content_chunks


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


def _heading_level_from_outline_depth(segment_count: int) -> int:
    """Map outline depth (1 -> 1.1 -> 1.2.1) to markdown heading level (## .. ######)."""
    return min(6, max(2, segment_count + 1))


def _looks_like_outline_heading_title(title: str) -> bool:
    """Heuristic: '1. Projectoverzicht' vs numbered list item '1. Open het menu'."""
    title = title.strip()
    if len(title) < 2:
        return False
    if title.endswith("."):
        return False
    if title.startswith(("[", "-", "*", "`")):
        return False
    if title[0].islower():
        return False
    if _LIST_ITEM_VERB_PREFIX_RE.match(title):
        return False
    if len(title) > 100:
        return False
    if title.count(". ") > 1:
        return False
    return True


def _markdown_heading_for_outline(num: str, title: str) -> str:
    depth = num.count(".") + 1
    level = _heading_level_from_outline_depth(depth)
    return f"{'#' * level} {title.strip()}"


def normalize_plain_outline_headings(text: str) -> str:
    """Convert outline-style lines to ## / ### markdown headings."""
    if not text or not text.strip():
        return text or ""

    def _dotted(match: re.Match[str]) -> str:
        return _markdown_heading_for_outline(match.group("num"), match.group("title"))

    def _plain_h1(match: re.Match[str]) -> str:
        title = match.group("title").strip()
        if not _looks_like_outline_heading_title(title):
            return match.group(0)
        return f"## {title}"

    def _bold_plain_h1(match: re.Match[str]) -> str:
        title = match.group("title").strip()
        if not _looks_like_outline_heading_title(title):
            return match.group(0)
        return f"## {title}"

    def _bold_dotted(match: re.Match[str]) -> str:
        return _markdown_heading_for_outline(match.group("num"), match.group("title"))

    def _chapter_space(match: re.Match[str]) -> str:
        title = match.group("title").strip()
        if not _looks_like_outline_heading_title(title):
            return match.group(0)
        return f"## {title}"

    out = _BOLD_DOTTED_OUTLINE_HEADING_RE.sub(_bold_dotted, text)
    out = _BOLD_PLAIN_OUTLINE_H1_RE.sub(_bold_plain_h1, out)
    out = _DOTTED_OUTLINE_HEADING_RE.sub(_dotted, out)
    out = _PLAIN_OUTLINE_H1_RE.sub(_plain_h1, out)
    out = _CHAPTER_NUM_SPACE_RE.sub(_chapter_space, out)
    return out


def ensure_institutional_check_spacing(text: str) -> str:
    """Blank lines before/after <institutional_check> when adjacent to body text."""
    if not text or "<institutional_check>" not in text.lower():
        return text or ""

    out = re.sub(
        r"(?<=\S)\n(?P<tag><institutional_check>)",
        r"\n\n\g<tag>",
        text,
        flags=re.IGNORECASE,
    )
    out = re.sub(
        r"(?P<close></institutional_check>)\n(?=\S)",
        r"\g<close>\n\n",
        out,
        flags=re.IGNORECASE,
    )
    return out


def normalize_numbered_headings(text: str) -> str:
    """Convert 'N Stap N: Title' lines to ## markdown headings."""
    if not text or not text.strip():
        return text or ""

    def _step_heading(match: re.Match[str]) -> str:
        title = match.group("title").strip()
        return f"## Stap {match.group('step')}: {title}"

    return _NUMBERED_STEP_HEADING_RE.sub(_step_heading, text)


def ensure_institutional_check_block(text: str) -> str:
    """Put <institutional_check> on its own lines with blank lines around the block."""
    if not text or "<institutional_check>" not in text.lower():
        return text or ""

    def _block(match: re.Match[str]) -> str:
        body = match.group("body").strip()
        if not body:
            return "<institutional_check>\n</institutional_check>"
        lines = [ln.strip() for ln in body.splitlines() if ln.strip()]
        inner = "\n".join(lines)
        return f"<institutional_check>\n{inner}\n</institutional_check>"

    return _INSTITUTIONAL_CHECK_INLINE_RE.sub(_block, text)


_NFR_INLINE_ROW_RE = re.compile(
    r"^Categorie:\s*(?P<cat>.+?)\s+Eis:\s*(?P<eis>.+?)\s+Meetmethode:\s*(?P<met>.+?)\s*$",
    re.IGNORECASE,
)


def normalize_plain_nfr_rows_to_table(text: str) -> str:
    """Turn 'Categorie: … Eis: … Meetmethode: …' lines into a markdown table."""
    if not text or "Categorie:" not in text:
        return text or ""

    lines = text.splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if _NFR_INLINE_ROW_RE.match(stripped):
            rows: list[tuple[str, str, str]] = []
            while i < len(lines):
                s = lines[i].strip()
                if not s or re.match(r"^[-*_]{3,}\s*$", s):
                    i += 1
                    continue
                m = _NFR_INLINE_ROW_RE.match(s)
                if not m:
                    break
                rows.append(
                    (
                        m.group("cat").strip(),
                        m.group("eis").strip(),
                        m.group("met").strip(),
                    )
                )
                i += 1
            if rows:
                out.append("| Categorie | Eis | Meetmethode |")
                out.append("| --- | --- | --- |")
                for cat, eis, met in rows:
                    out.append(f"| {cat} | {eis} | {met} |")
                continue
        out.append(lines[i])
        i += 1
    return "\n".join(out)


_NFR_SECTION_HEADING_RE = re.compile(
    r"^\s{0,3}(?P<h>#{1,6}\s+Niet-functionele\s+requirements)\s*$",
    re.IGNORECASE,
)
_NFR_LONG_DASH_LINE_RE = re.compile(r"^[\s\-—_]{6,}\s*$")
_NFR_BOLD_CATEGORY_RE = re.compile(r"^\*\*(?P<cat>[^*\n]+)\*\*\s*$")
_NFR_CATEGORY_DASH_RE = re.compile(
    r"^(?P<cat>\*\*[^*]+\*\*|[^|—\-\n]+?)\s*[—\-:]\s*(?P<eis>.+?)(?:\s*[—\-]\s*(?P<met>.+))?\s*$"
)


def _strip_md_bold(text: str) -> str:
    return re.sub(r"^\*\*|\*\*$", "", text.strip()).strip()


def _parse_nfr_prose_lines(body_lines: list[str]) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    pending_cat: str | None = None
    pending_eis: list[str] = []

    def _flush_pending() -> None:
        nonlocal pending_cat, pending_eis
        if pending_cat and pending_eis:
            rows.append((pending_cat, " ".join(pending_eis).strip(), "-"))
        pending_cat = None
        pending_eis = []

    for line in body_lines:
        stripped = line.strip()
        if not stripped or _NFR_LONG_DASH_LINE_RE.match(stripped):
            _flush_pending()
            continue
        if stripped.startswith("|"):
            break

        bold = _NFR_BOLD_CATEGORY_RE.match(stripped)
        if bold:
            _flush_pending()
            pending_cat = bold.group("cat").strip()
            continue

        dash = _NFR_CATEGORY_DASH_RE.match(stripped)
        if dash:
            _flush_pending()
            cat = _strip_md_bold(dash.group("cat"))
            eis = dash.group("eis").strip()
            met = (dash.group("met") or "-").strip()
            rows.append((cat, eis, met or "-"))
            continue

        if pending_cat:
            pending_eis.append(stripped)
        elif len(stripped) > 3:
            pending_cat = stripped.rstrip(":")
            pending_eis = []

    _flush_pending()
    return rows


def normalize_nfr_prose_section_to_table(text: str) -> str:
    """Convert prose under ### Niet-functionele requirements into a markdown table."""
    if not text or "niet-functionele" not in text.lower():
        return text or ""

    lines = text.splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if not _NFR_SECTION_HEADING_RE.match(line):
            out.append(line)
            i += 1
            continue

        out.append(line)
        i += 1
        while i < len(lines) and not lines[i].strip():
            i += 1

        if i >= len(lines):
            break

        if lines[i].strip().startswith("|"):
            while i < len(lines):
                if _NFR_SECTION_HEADING_RE.match(lines[i]):
                    break
                if re.match(r"^\s{0,3}#{1,6}\s+", lines[i]) and not lines[i].strip().lower().startswith(
                    "### niet-functionele"
                ):
                    break
                out.append(lines[i])
                i += 1
            continue

        body_lines: list[str] = []
        while i < len(lines):
            if re.match(r"^\s{0,3}#{1,6}\s+", lines[i]):
                break
            body_lines.append(lines[i])
            i += 1

        rows = _parse_nfr_prose_lines(body_lines)
        if rows:
            out.append("| Categorie | Eis | Meetmethode |")
            out.append("| --- | --- | --- |")
            for cat, eis, met in rows:
                out.append(f"| {cat} | {eis} | {met} |")
        else:
            out.extend(body_lines)

    return "\n".join(out)


def collapse_extra_blank_lines(text: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", text or "")


def normalize_assistant_markdown(
    text: str,
    *,
    normalize_numbered_headings_flag: bool = True,
    normalize_plain_outline_headings_flag: bool = True,
) -> str:
    """Apply institutional typography normalizers before Rich/Ink render."""
    out = text or ""
    out = ensure_institutional_check_block(out)
    out = ensure_institutional_check_spacing(out)
    out = ensure_heading_line_breaks(out)
    if normalize_numbered_headings_flag:
        out = normalize_numbered_headings(out)
    if normalize_plain_outline_headings_flag:
        out = normalize_plain_outline_headings(out)
    out = ensure_section_breaks(out)
    out = tighten_heading_and_label_spacing(out)
    out = normalize_plain_nfr_rows_to_table(out)
    out = normalize_nfr_prose_section_to_table(out)
    return collapse_extra_blank_lines(out)
