"""Normalize assistant markdown for institutional layout (headings, labels, lists, tables).

Pipeline highlights (see ``normalize_assistant_markdown``):
- Outline / ``**Label:**`` / ``<institutional_check>`` layout fixes
- NFR prose and comparison pseudo-layout (underscore, vs, em-dash) → markdown tables
- Context-aware overview tables (2–6 columns; auxiliary ``**Groep**`` blocks)
- Collapsed record rows: dense ``Component: … Keuze: … Status: … ——————`` on one line
  → ``_parse_collapsed_record_rows`` (after inline pipe-header in ``_parse_collapsed_overview_body``;
  eligibility guard skips ``**Groep**`` + one-key-per-line auxiliary blocks)
"""

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


_TABLE_DIVIDER_CELL_RE = re.compile(r"^\s*:?-{3,}:?\s*$")
_PSEUDO_SEPARATOR_LINE_RE = re.compile(r"^[\s_\-—─]{6,}\s*$")
_ORPHAN_TRAILING_PIPE_RE = re.compile(r"\|\s*$")
_HEADING_LINE_RE = re.compile(r"^\s{0,3}#{1,6}\s+.+$")
_VERSUS_IN_HEADING_RE = re.compile(
    r"(?P<a>.+?)\s+(?:versus|vs\.?|tegen)\s+(?P<b>.+)",
    re.IGNORECASE,
)
_INLINE_DUAL_SPLIT_RE = re.compile(r"_{4,}|─{4,}|\s+[—–-]{2,}\s+")
_BOLD_CATEGORY_LINE_RE = re.compile(r"^\*\*(?P<label>[^*\n]+)\*\*\s*$")
_BOLD_CATEGORY_INLINE_RE = re.compile(
    r"^\*\*(?P<label>[^*\n]+)\*\*\s+(?P<rest>.+)$"
)
_MAX_COMPARISON_COLUMNS = 6
# Overview intent: auxiliary/config/architecture tables (2-6 columns).
# Excludes bare "taken" to avoid false positives on "### Hulp taken" (Cloud/Lokaal).
_OVERVIEW_HEADING_HINT_RE = re.compile(
    r"(?i)\b(overzicht|auxiliary|configuratie|stack|architectuur|architectuursamenvatting|"
    r"samenvatting|implementatie|testresultaten|poc)\b",
)
_OVERVIEW_FIELD_LINE_RE = re.compile(r"^([^:|]{1,48}):\s*(.+)$", re.IGNORECASE)
# Keys for collapsed records: no spaces in label (avoids "Inter-agent communicatie Keuze" false keys).
_FIELD_KEY_TOKEN_RE = re.compile(r"(?i)\b([A-Za-z][A-Za-z0-9\-]{0,39}):\s")
_FIELD_REPEAT_GATE_RE = re.compile(
    r"(?i)(?:component|keuze|status|categorie|eis|meetmethode)\s*:"
)
_CATEGORY_HEADER_NAMES = frozenset({"category", "categorie", "taak", "task", "aspect"})


def _split_markdown_table_row(row: str) -> list[str]:
    s = row.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]


def _is_markdown_table_divider_line(row: str) -> bool:
    cells = _split_markdown_table_row(row)
    return len(cells) > 1 and all(_TABLE_DIVIDER_CELL_RE.match(c) for c in cells)


def _looks_like_markdown_table_row(row: str) -> bool:
    if "|" not in row:
        return False
    stripped = row.strip()
    if not stripped:
        return False
    if stripped.startswith("|"):
        return True
    return stripped.count("|") >= 2


def _section_has_markdown_table(body_lines: list[str]) -> bool:
    for line in body_lines:
        if _is_markdown_table_divider_line(line):
            return True
    return False


def _strip_orphan_trailing_pipe(line: str) -> str:
    return _ORPHAN_TRAILING_PIPE_RE.sub("", line).rstrip()


def _sanitize_table_cell(text: str) -> str:
    """Normalize cell text; pipes become `` / `` so markdown tables stay valid."""
    cell = re.sub(r"\s+", " ", (text or "").strip())
    cell = re.sub(r"_{2,}", " ", cell)
    cell = cell.replace("|", " / ")
    return cell.strip()


def _render_markdown_table(headers: list[str], rows: list[list[str]]) -> list[str]:
    ncols = len(headers)
    if ncols < 2 or not rows:
        return []
    out = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in range(ncols)) + " |",
    ]
    for row in rows:
        cells = [_sanitize_table_cell(c) for c in row[:ncols]]
        while len(cells) < ncols:
            cells.append("")
        out.append("| " + " | ".join(cells) + " |")
    return out


def _infer_columns_from_heading(heading_line: str) -> list[str] | None:
    title = re.sub(r"^\s{0,3}#{1,6}\s+", "", heading_line).strip()
    title = re.sub(r"^(?:vergelijking|comparison)\s*:\s*", "", title, flags=re.IGNORECASE)
    match = _VERSUS_IN_HEADING_RE.search(title)
    if match:
        a = match.group("a").strip().rstrip(":")
        b = match.group("b").strip()
        if a and b:
            return ["Aspect", a, b]
    return None


def _count_pseudo_table_signals(body_lines: list[str]) -> int:
    signals = 0
    for line in body_lines:
        stripped = _strip_orphan_trailing_pipe(line.strip())
        if not stripped:
            continue
        if _PSEUDO_SEPARATOR_LINE_RE.match(stripped):
            signals += 1
            continue
        if _ORPHAN_TRAILING_PIPE_RE.search(line):
            signals += 1
        if _BOLD_CATEGORY_INLINE_RE.match(stripped) and _INLINE_DUAL_SPLIT_RE.search(stripped):
            signals += 1
        if _INLINE_DUAL_SPLIT_RE.search(stripped) and not stripped.startswith("|"):
            signals += 1
        if _OVERVIEW_FIELD_LINE_RE.match(stripped):
            signals += 1
        if len(_FIELD_KEY_TOKEN_RE.findall(stripped)) >= 3:
            signals += 1
        if _BOLD_CATEGORY_LINE_RE.match(stripped):
            signals += 1
    return signals


def _discover_repeated_field_keys(text: str) -> list[str] | None:
    """Find Label: keys that repeat across em-dash-separated records (e.g. Component/Keuze/Status)."""
    if not text or not text.strip():
        return None
    counts: dict[str, int] = {}
    order: list[str] = []
    seen_low: set[str] = set()
    for match in _FIELD_KEY_TOKEN_RE.finditer(text):
        key = _normalize_field_key(match.group(1))
        low = key.lower()
        if not key or len(key) < 2:
            continue
        counts[low] = counts.get(low, 0) + 1
        if low not in seen_low:
            seen_low.add(low)
            order.append(key)
    repeated = [k for k in order if counts.get(k.lower(), 0) >= 2]
    if len(repeated) < 2:
        return None
    return repeated[:_MAX_COMPARISON_COLUMNS]


def _split_record_segments(
    full: str,
    keys: list[str],
    line_chunks: list[str],
) -> list[str]:
    """Split collapsed pseudo-records on em-dash, repeated anchor key, or one record per line."""
    segments = [p.strip() for p in _INLINE_DUAL_SPLIT_RE.split(full) if p.strip()]
    if len(segments) >= 2:
        return segments
    if len(line_chunks) >= 2 and all(_FIELD_KEY_TOKEN_RE.search(ln) for ln in line_chunks):
        return line_chunks
    if keys:
        anchor = keys[0]
        parts = re.split(rf"(?i)(?=\b{re.escape(anchor)}\s*:)", full)
        parts = [p.strip() for p in parts if p.strip()]
        if len(parts) >= 2:
            return parts
    return [full] if full.strip() else []


def _dedupe_table_rows(rows: list[list[str]]) -> list[list[str]]:
    seen: set[tuple[str, ...]] = set()
    unique: list[list[str]] = []
    for row in rows:
        key = tuple(row)
        if key in seen:
            continue
        seen.add(key)
        unique.append(row)
    return unique


def _collapsed_record_layout_eligible(chunks: list[str], full: str) -> bool:
    """True for dense Component/Keuze/Status lines, not **Groep** + one-key-per-line blocks."""
    if _INLINE_DUAL_SPLIT_RE.search(full):
        return True
    if any(len(_FIELD_KEY_TOKEN_RE.findall(ln)) >= 3 for ln in chunks):
        return True
    if len(chunks) >= 2 and all(_FIELD_KEY_TOKEN_RE.search(ln) for ln in chunks):
        if not any(_BOLD_CATEGORY_LINE_RE.match(ln) for ln in chunks):
            return True
    return False


def _parse_collapsed_record_rows(
    body_lines: list[str],
    field_keys: list[str] | None = None,
) -> tuple[list[str], list[list[str]]] | None:
    """Parse em-dash-separated Component/Keuze/Status blocks into a markdown table."""
    chunks: list[str] = []
    for line in body_lines:
        stripped = _strip_orphan_trailing_pipe(line.strip())
        if not stripped or _PSEUDO_SEPARATOR_LINE_RE.match(stripped):
            continue
        if stripped.startswith("|") and _looks_like_markdown_table_row(stripped):
            return None
        chunks.append(stripped)
    if not chunks:
        return None
    full = " ".join(chunks)
    if not _collapsed_record_layout_eligible(chunks, full):
        return None
    keys = field_keys or _discover_repeated_field_keys(full)
    if not keys or len(keys) < 2:
        return None
    segments = _split_record_segments(full, keys, chunks)
    rows: list[list[str]] = []
    for segment in segments:
        values = _extract_field_values_from_text(segment, keys)
        filled = sum(1 for k in keys if (values.get(k) or "").strip())
        if filled >= 2:
            rows.append([_sanitize_table_cell(values.get(k, "-")) for k in keys])
    rows = _dedupe_table_rows(rows)
    if len(rows) < 2:
        return None
    return keys, rows


def _normalize_field_key(key: str) -> str:
    return re.sub(r"\s+", " ", (key or "").strip())


def _field_key_matches(header: str, key: str) -> bool:
    return _normalize_field_key(header).lower() == _normalize_field_key(key).lower()


def _infer_section_intent(heading_line: str, body_lines: list[str]) -> str:
    """Return comparison | overview | explicit_grid | generic."""
    if _infer_columns_from_heading(heading_line):
        return "comparison"
    if _OVERVIEW_HEADING_HINT_RE.search(heading_line):
        return "overview"
    if re.search(r"(?i)\b(vergelijk|versus|vs\.?|comparison|tabel)\b", heading_line):
        return "comparison"
    for line in body_lines:
        stripped = line.strip()
        if not stripped or _PSEUDO_SEPARATOR_LINE_RE.match(stripped):
            continue
        if _looks_like_markdown_table_row(stripped) and not _is_markdown_table_divider_line(stripped):
            return "explicit_grid"
        break
    return "generic"


def _collect_overview_field_keys(body_lines: list[str]) -> list[str]:
    """Unique Label: keys in first-seen order."""
    keys: list[str] = []
    seen: set[str] = set()
    for line in body_lines:
        stripped = line.strip()
        if not stripped or _PSEUDO_SEPARATOR_LINE_RE.match(stripped):
            continue
        if _BOLD_CATEGORY_LINE_RE.match(stripped):
            continue
        match = _OVERVIEW_FIELD_LINE_RE.match(stripped)
        if not match:
            continue
        key = _normalize_field_key(match.group(1))
        low = key.lower()
        if key and low not in seen:
            seen.add(low)
            keys.append(key)
    return keys


def _overview_headers_from_body(body_lines: list[str]) -> list[str] | None:
    """Infer headers from first pipe row or accumulated Label: keys."""
    for line in body_lines:
        stripped = _strip_orphan_trailing_pipe(line.strip())
        if not stripped or _PSEUDO_SEPARATOR_LINE_RE.match(stripped):
            continue
        if _looks_like_markdown_table_row(stripped) and not _is_markdown_table_divider_line(stripped):
            cells = [_sanitize_table_cell(c) for c in _split_markdown_table_row(stripped)]
            if len(cells) >= 2 and any(cells):
                return cells[:_MAX_COMPARISON_COLUMNS]
        break
    field_keys = _collect_overview_field_keys(body_lines)
    if len(field_keys) < 2:
        return None
    if field_keys[0].lower() in _CATEGORY_HEADER_NAMES:
        return field_keys[:_MAX_COMPARISON_COLUMNS]
    return (["Categorie"] + field_keys)[:_MAX_COMPARISON_COLUMNS]


def _extract_field_values_from_text(text: str, field_keys: list[str]) -> dict[str, str]:
    """Pull Label: value pairs from a collapsed line."""
    values: dict[str, str] = {}
    keys = field_keys[:_MAX_COMPARISON_COLUMNS]
    for key in keys:
        others = tuple(k for k in keys if k.lower() != key.lower())
        others_pat = "|".join(re.escape(k) for k in others)
        lookahead = rf"(?=\s+(?:{others_pat})\s*:|$)" if others_pat else r"$"
        match = re.search(rf"(?i){re.escape(key)}\s*:\s*(.+?){lookahead}", text)
        if match:
            values[key] = match.group(1).strip()
    return values


def _parse_overview_field_rows(
    body_lines: list[str],
    headers: list[str],
) -> list[list[str]] | None:
    """Parse grouped **Category** + Provider:/Model: blocks into table rows."""
    if len(headers) < 2:
        return None

    field_keys = headers[1:] if headers[0].lower() in _CATEGORY_HEADER_NAMES else headers
    category_in_headers = headers[0].lower() in _CATEGORY_HEADER_NAMES
    rows: list[list[str]] = []
    category = ""
    values: dict[str, str] = {}

    def flush() -> None:
        nonlocal category, values
        if not category and not any(v.strip() and v != "-" for v in values.values()):
            return
        if category_in_headers:
            row = [category or "-"] + [values.get(key, "-") for key in field_keys]
        else:
            row = [values.get(key, "-") for key in headers]
        rows.append(row)
        category = ""
        values = {}

    for line in body_lines:
        stripped = _strip_orphan_trailing_pipe(line.strip())
        if not stripped:
            continue
        if _PSEUDO_SEPARATOR_LINE_RE.match(stripped):
            flush()
            continue
        if stripped.startswith("|") and _looks_like_markdown_table_row(stripped):
            continue

        bold_only = _BOLD_CATEGORY_LINE_RE.match(stripped)
        if bold_only:
            flush()
            category = bold_only.group("label").strip()
            continue

        field_match = _OVERVIEW_FIELD_LINE_RE.match(stripped)
        if field_match:
            key = _normalize_field_key(field_match.group(1))
            val = field_match.group(2).strip()
            for hdr in field_keys:
                if _field_key_matches(hdr, key):
                    values[hdr] = val
                    break
            continue

        inline_vals = _extract_field_values_from_text(stripped, field_keys)
        if inline_vals:
            values.update(inline_vals)

    flush()
    return rows if len(rows) >= 2 else None


def _parse_collapsed_overview_body(
    body_lines: list[str],
) -> tuple[list[str], list[list[str]]] | None:
    """Single-paragraph pseudo with embedded pipe header + Label: tokens."""
    chunks: list[str] = []
    for line in body_lines:
        stripped = _strip_orphan_trailing_pipe(line.strip())
        if not stripped or _PSEUDO_SEPARATOR_LINE_RE.match(stripped):
            continue
        chunks.append(stripped)
    if not chunks:
        return None
    full = " ".join(chunks)

    header_match = re.match(
        r"^((?:[A-Za-z][A-Za-z0-9 /]{0,40}\s*\|\s*){1,}[A-Za-z][A-Za-z0-9 /]{0,40})",
        full,
    )
    if header_match:
        header_part = header_match.group(1)
        headers = [
            _sanitize_table_cell(c)
            for c in _split_markdown_table_row(header_part)
            if c.strip()
        ]
        if len(headers) >= 2:
            remainder = full[header_match.end() :].strip()
            field_keys = headers[1:] if headers[0].lower() in _CATEGORY_HEADER_NAMES else headers
            parts = re.split(r"\*\*([^*]+)\*\*", remainder)
            rows: list[list[str]] = []
            if len(parts) >= 3:
                for idx in range(1, len(parts), 2):
                    label = parts[idx].strip()
                    content = parts[idx + 1].strip() if idx + 1 < len(parts) else ""
                    vals = _extract_field_values_from_text(content, field_keys)
                    if headers[0].lower() in _CATEGORY_HEADER_NAMES:
                        rows.append([label] + [vals.get(key, "-") for key in field_keys])
                    else:
                        row = [vals.get(key, "-") for key in headers]
                        rows.append(row)
            if len(rows) >= 2:
                return headers[:_MAX_COMPARISON_COLUMNS], rows

    # Record parser runs after pipe-header match so inline ``A | B | C`` grids stay intact.
    record_parsed = _parse_collapsed_record_rows(body_lines)
    if record_parsed:
        return record_parsed

    headers = _overview_headers_from_body(body_lines)
    if not headers:
        return None
    rows = _parse_overview_field_rows(body_lines, headers)
    if rows:
        return headers, rows
    return None


def _parse_explicit_header_grid(
    body_lines: list[str],
) -> tuple[list[str], list[list[str]]] | None:
    """Body is already pipe rows; first line is header."""
    substantive = [
        ln.strip()
        for ln in body_lines
        if ln.strip() and not _PSEUDO_SEPARATOR_LINE_RE.match(ln.strip())
    ]
    if len(substantive) < 2:
        return None
    if not all(_looks_like_markdown_table_row(ln) for ln in substantive):
        return None
    headers = [
        _sanitize_table_cell(c) for c in _split_markdown_table_row(substantive[0])
    ]
    headers = headers[:_MAX_COMPARISON_COLUMNS]
    if sum(1 for c in headers if c.strip()) < 2:
        return None
    rows: list[list[str]] = []
    for line in substantive[1:]:
        if _is_markdown_table_divider_line(line):
            continue
        cells = [
            _sanitize_table_cell(c) for c in _split_markdown_table_row(line) if c.strip() or c == ""
        ]
        while len(cells) < len(headers):
            cells.append("")
        rows.append(cells[: len(headers)])
    if len(rows) < 2:
        return None
    return headers, rows


def _parse_overview_body_to_rows(
    body_lines: list[str],
) -> tuple[list[str], list[list[str]]] | None:
    """Context-dependent overview/config tables (2-6 columns)."""
    headers = _overview_headers_from_body(body_lines)
    if headers:
        rows = _parse_overview_field_rows(body_lines, headers)
        if rows:
            return headers, rows
    return _parse_collapsed_overview_body(body_lines)


def _parse_section_to_table(
    heading_line: str,
    body_lines: list[str],
    intent: str | None = None,
) -> tuple[list[str], list[list[str]]] | None:
    """Route section body to the best parser for its intent."""
    resolved_intent = intent or _infer_section_intent(heading_line, body_lines)
    if resolved_intent == "explicit_grid":
        return _parse_explicit_header_grid(body_lines)
    if resolved_intent == "comparison":
        return _parse_comparison_body_to_rows(
            body_lines, _infer_columns_from_heading(heading_line)
        )
    if resolved_intent == "overview":
        parsed = _parse_overview_body_to_rows(body_lines)
        if parsed:
            return parsed
        return _parse_comparison_body_to_rows(
            body_lines, _infer_columns_from_heading(heading_line)
        )
    default_headers = _infer_columns_from_heading(heading_line)
    parsed = _parse_comparison_body_to_rows(body_lines, default_headers)
    if parsed:
        return parsed
    return _parse_overview_body_to_rows(body_lines)


def _should_attempt_pseudo_normalize(
    heading_line: str,
    body_lines: list[str],
    intent: str,
) -> bool:
    if intent == "comparison":
        return True
    if intent == "overview":
        return (
            _count_pseudo_table_signals(body_lines) >= 1
            or _overview_headers_from_body(body_lines) is not None
        )
    if intent == "explicit_grid":
        return True
    joined = "\n".join(
        _strip_orphan_trailing_pipe(ln.strip())
        for ln in body_lines
        if ln.strip() and not _PSEUDO_SEPARATOR_LINE_RE.match(ln.strip())
    )
    if _discover_repeated_field_keys(joined):
        return True
    return _count_pseudo_table_signals(body_lines) >= 2


def _split_labeled_entity_value(text: str) -> tuple[str | None, str]:
    match = re.match(r"^([^:|]{1,40}):\s*(.+)$", (text or "").strip())
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return None, (text or "").strip()


def _append_dual_entity_row(
    rows: list[list[str]],
    entity_headers: list[str] | None,
    label: str,
    part_a: str,
    part_b: str,
) -> list[str] | None:
    entity_a, value_a = _split_labeled_entity_value(part_a)
    entity_b, value_b = _split_labeled_entity_value(part_b)
    if entity_a and entity_b:
        pair = [entity_a, entity_b]
        if entity_headers is None:
            entity_headers = pair
        elif entity_headers != pair:
            entity_headers = None
    else:
        value_a = re.sub(r"^[A-Za-z0-9 .+\-]+:\s*", "", part_a).strip()
        value_b = re.sub(r"^[A-Za-z0-9 .+\-]+:\s*", "", part_b).strip()
    rows.append([label, value_a, value_b])
    return entity_headers


def _parse_comparison_body_to_rows(
    body_lines: list[str],
    default_headers: list[str] | None,
) -> tuple[list[str], list[list[str]]] | None:
    """Parse pseudo-comparison prose into (headers, rows)."""
    rows: list[list[str]] = []
    pending_label: str | None = None
    entity_headers: list[str] | None = None

    for line in body_lines:
        stripped = _strip_orphan_trailing_pipe(line.strip())
        if not stripped:
            continue
        if _PSEUDO_SEPARATOR_LINE_RE.match(stripped):
            pending_label = None
            continue
        if stripped.startswith("|"):
            return None

        bold_only = _BOLD_CATEGORY_LINE_RE.match(stripped)
        if bold_only:
            pending_label = bold_only.group("label").strip()
            continue

        bold_inline = _BOLD_CATEGORY_INLINE_RE.match(stripped)
        if bold_inline:
            label = bold_inline.group("label").strip()
            parts = _INLINE_DUAL_SPLIT_RE.split(bold_inline.group("rest").strip())
            parts = [p.strip() for p in parts if p.strip()]
            if len(parts) >= 2:
                rows.append([label, parts[0], parts[1]])
            pending_label = None
            continue

        if pending_label:
            parts = _INLINE_DUAL_SPLIT_RE.split(stripped)
            parts = [p.strip() for p in parts if p.strip()]
            if len(parts) >= 2:
                entity_headers = _append_dual_entity_row(
                    rows, entity_headers, pending_label, parts[0], parts[1]
                )
                pending_label = None
                continue

        dash = _NFR_CATEGORY_DASH_RE.match(stripped)
        if dash and not _INLINE_DUAL_SPLIT_RE.search(stripped):
            cat = _strip_md_bold(dash.group("cat"))
            eis = dash.group("eis").strip()
            met = (dash.group("met") or "-").strip()
            rows.append([cat, eis, met or "-"])
            pending_label = None
            continue

        label_colon = re.match(r"^([^:|]{2,40}):\s*(.+)$", stripped)
        if label_colon and not pending_label:
            label = label_colon.group(1).strip()
            rest = label_colon.group(2).strip()
            parts = _INLINE_DUAL_SPLIT_RE.split(rest)
            parts = [p.strip() for p in parts if p.strip()]
            if len(parts) >= 2:
                entity_headers = _append_dual_entity_row(
                    rows, entity_headers, label, parts[0], parts[1]
                )
                continue

    if len(rows) < 2:
        return None

    max_cols = min(_MAX_COMPARISON_COLUMNS, max(len(r) for r in rows))
    if max_cols < 2:
        return None

    if default_headers and len(default_headers) == max_cols:
        headers = default_headers
    elif max_cols == 3 and entity_headers and len(entity_headers) == 2:
        headers = ["Aspect", entity_headers[0], entity_headers[1]]
    elif max_cols == 2:
        headers = ["Aspect", "Optie A", "Optie B"]
    elif max_cols == 3 and default_headers and len(default_headers) >= 3:
        headers = default_headers[:3]
    else:
        headers = ["Aspect"] + [f"Kolom {i}" for i in range(1, max_cols)]

    normalized_rows: list[list[str]] = []
    for row in rows:
        cells = row[:max_cols]
        while len(cells) < max_cols:
            cells.append("")
        normalized_rows.append(cells)

    return headers, normalized_rows


def ensure_markdown_table_dividers(text: str) -> str:
    """Insert ``|---|`` when consecutive pipe rows omit the divider line."""
    if not text or "|" not in text:
        return text or ""

    lines = text.splitlines()
    out: list[str] = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]
        if _looks_like_markdown_table_row(line) and not _is_markdown_table_divider_line(line):
            if i + 1 < n and _is_markdown_table_divider_line(lines[i + 1]):
                out.append(line)
                i += 1
                while i < n and _looks_like_markdown_table_row(lines[i]):
                    out.append(lines[i])
                    i += 1
                continue
            if (
                i + 1 < n
                and _looks_like_markdown_table_row(lines[i + 1])
                and not _is_markdown_table_divider_line(lines[i + 1])
            ):
                header_cells = _split_markdown_table_row(line)
                if len(header_cells) > 1 and any(c.strip() for c in header_cells):
                    out.append(line)
                    divider = "| " + " | ".join("---" for _ in header_cells) + " |"
                    out.append(divider)
                    i += 1
                    while i < n and _looks_like_markdown_table_row(lines[i]):
                        if _is_markdown_table_divider_line(lines[i]):
                            i += 1
                            continue
                        out.append(lines[i])
                        i += 1
                    continue
        out.append(line)
        i += 1

    return "\n".join(out)


def normalize_pseudo_tables_to_markdown(text: str) -> str:
    """Convert pseudo-layout blocks into markdown tables (context-aware 2-6 columns).

    Routing per heading section: explicit_grid (pipe rows) → comparison (vs/Cloud-Lokaal)
    → overview (auxiliary/config) → generic fallback. See ``_parse_section_to_table``.
    Uses ``str.splitlines()`` so CRLF inputs from Windows editors parse correctly.
    """
    if not text or not text.strip():
        return text or ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if not (
        "|" in text
        or re.search(r"_{4,}", text)
        or re.search(r"^\*\*[^*]+\*\*", text, re.MULTILINE)
        or re.search(r"(?i)\b(versus|vs\.?|vergelijk|comparison|overzicht|auxiliary)\b", text)
        or re.search(r"[—–-]{4,}", text)
        or len(_FIELD_REPEAT_GATE_RE.findall(text)) >= 2
    ):
        return text

    lines = text.splitlines()
    out: list[str] = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]
        if not _HEADING_LINE_RE.match(line):
            out.append(line)
            i += 1
            continue

        heading = line
        i += 1
        body_lines: list[str] = []
        while i < n and not _HEADING_LINE_RE.match(lines[i]):
            body_lines.append(lines[i])
            i += 1

        if not body_lines:
            out.append(heading)
            continue

        if _section_has_markdown_table(body_lines):
            out.append(heading)
            out.extend(body_lines)
            continue

        intent = _infer_section_intent(heading, body_lines)
        if not _should_attempt_pseudo_normalize(heading, body_lines, intent):
            out.append(heading)
            out.extend(body_lines)
            continue

        parsed = _parse_section_to_table(heading, body_lines, intent)
        if parsed:
            headers, rows = parsed
            out.append(heading)
            out.extend(_render_markdown_table(headers, rows))
            continue

        out.append(heading)
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
    """Apply institutional typography normalizers before Rich/Ink render.

    Normalizes Windows CRLF and legacy Mac CR to LF before parsing so pseudo-table
    detection behaves the same on all platforms.
    """
    out = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    out = ensure_institutional_check_block(out)
    out = ensure_institutional_check_spacing(out)
    out = ensure_heading_line_breaks(out)
    if normalize_numbered_headings_flag:
        out = normalize_numbered_headings(out)
    if normalize_plain_outline_headings_flag:
        out = normalize_plain_outline_headings(out)
    out = ensure_section_breaks(out)
    out = ensure_markdown_table_dividers(out)
    out = normalize_pseudo_tables_to_markdown(out)
    out = tighten_heading_and_label_spacing(out)
    out = normalize_plain_nfr_rows_to_table(out)
    out = normalize_nfr_prose_section_to_table(out)
    return collapse_extra_blank_lines(out)
