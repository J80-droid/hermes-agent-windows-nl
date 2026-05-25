"""Institutional Rich renderer for assistant answers (demo palette, per-column tables)."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import ClassVar, Iterator

from rich import box
from rich.console import Console, Group, RenderableType
from rich.segment import Segment
from rich.text import Text as RichText
from rich.markdown import Markdown, TableElement
from rich.table import Table
from rich.theme import Theme

from hermes_cli.markdown_output_normalize import normalize_assistant_markdown

logger = logging.getLogger(__name__)

TABLE_HEADER_PALETTE_DEMO = (
    "bold #66d9ef",
    "bold #a6e22e",
    "bold #f8f8f2",
    "bold #f92672",
)

_LABEL_ONLY_LINE_RE = re.compile(r"^\*\*(?P<label>[^*\n]+?):\*\*\s*$")
_HEADING_LINE_RE = re.compile(r"^(?P<h>(?:\s{0,3})(#{1,6})\s+[^\n]+)$")

_INSTITUTIONAL_CHECK_BLOCK_RE = re.compile(
    r"<institutional_check>\s*(?P<body>.*?)\s*</institutional_check>",
    re.DOTALL | re.IGNORECASE,
)

_BUILTIN_PALETTES: dict[str, dict[str, str]] = {
    "demo": {
        "h1": "bold #66d9ef underline",
        "h2": "bold #a6e22e",
        "h3": "bold #e6db74",
        "h4": "bold #ae81ff italic",
        "h5": "italic #cbd5e1",
        "h6": "dim",
        "strong": "bold #ff9e64",
        "code": "#66d9ef",
        "link": "underline #66d9ef",
        "table_header": "bold #66d9ef",
        "label": "bold #f92672",
        "text": "#cbd5e1",
    },
    "hermes": {
        "h1": "bold #FFD700 underline",
        "h2": "bold #FFBF00 underline",
        "h3": "bold #DAA520",
        "h4": "bold #DAA520 italic",
        "h5": "#DAA520 italic",
        "h6": "#B8860B italic",
        "strong": "bold #DAA520",
        "code": "#FFBF00",
        "link": "underline #FFBF00",
        "table_header": "bold #FFBF00",
        "label": "bold #DAA520",
        "text": "#FFF8DC",
    },
    "neutral": {
        "h1": "bold bright_white",
        "h2": "bold white",
        "h3": "bold bright_black",
        "h4": "italic white",
        "h5": "dim",
        "h6": "dim italic",
        "strong": "bold white",
        "code": "bright_black",
        "link": "underline bright_cyan",
        "table_header": "bold bright_cyan",
        "label": "bold bright_white",
        "text": "white",
    },
}

_PALETTE_REQUIRED_KEYS = frozenset(
    {"h1", "h2", "h3", "h4", "strong", "label", "text", "table_header"}
)

_PALETTES_CACHE: dict[str, dict[str, str]] | None = None


def _load_yaml_palettes() -> dict[str, dict[str, str]]:
    try:
        import yaml
    except ImportError:  # pragma: no cover
        return {}

    repo_root = Path(__file__).resolve().parent.parent
    for path in (repo_root / "config" / "palettes.yaml", repo_root / "palettes.yaml"):
        if not path.exists():
            continue
        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            if not isinstance(data, dict):
                continue
            validated: dict[str, dict[str, str]] = {}
            for name, colors in data.items():
                if not isinstance(colors, dict):
                    continue
                missing = _PALETTE_REQUIRED_KEYS - colors.keys()
                if missing:
                    continue
                validated[name] = {k: str(v).strip() for k, v in colors.items()}
            if validated:
                return validated
        except Exception as exc:
            logger.warning("Failed to load palettes from %s: %s", path, exc)
    return {}


def _get_all_palettes() -> dict[str, dict[str, str]]:
    global _PALETTES_CACHE
    if _PALETTES_CACHE is None:
        _PALETTES_CACHE = {**_BUILTIN_PALETTES, **_load_yaml_palettes()}
    return _PALETTES_CACHE


def assistant_markdown_theme(palette: str = "demo") -> Theme:
    palettes = _get_all_palettes()
    key = (palette or "demo").strip().lower()
    colors = palettes.get(key, palettes["demo"])
    return Theme(
        {
            "markdown.h1": colors["h1"],
            "markdown.h2": colors["h2"],
            "markdown.h3": colors["h3"],
            "markdown.h4": colors["h4"],
            "markdown.h5": colors.get("h5", "dim"),
            "markdown.h6": colors.get("h6", "dim italic"),
            "markdown.strong": colors["strong"],
            "markdown.em": "italic",
            "markdown.block_quote": "dim",
            "markdown.code": colors.get("code", "bright_black"),
            "markdown.code_block": "dim",
            "markdown.link": colors.get("link", "underline bright_cyan"),
            "markdown.link_url": "dim underline",
            "markdown.hr": "dim",
            "markdown.item": colors["text"],
            "markdown.item.bullet": "dim",
            "markdown.item.number": "dim",
            "markdown.table.header": colors["table_header"],
            "markdown.table.border": "dim",
        }
    )


def table_header_palette(palette: str = "demo") -> tuple[str, ...]:
    palettes = _get_all_palettes()
    key = (palette or "demo").strip().lower()
    colors = palettes.get(key, palettes["demo"])
    custom = colors.get("header_palette", "")
    if isinstance(custom, str) and custom:
        parts = [p.strip() for p in custom.split(",")]
        if len(parts) >= 2:
            return tuple(parts)
    if key == "hermes":
        return ("bold #FFD700", "bold #FFBF00", "bold #DAA520", "bold #FFF8DC")
    if key == "neutral":
        return ("bold bright_cyan", "bold white", "bold bright_black", "dim")
    return TABLE_HEADER_PALETTE_DEMO


class InstitutionalTableElement(TableElement):
    header_palette: ClassVar[tuple[str, ...]] = TABLE_HEADER_PALETTE_DEMO

    def __rich_console__(self, console, options):
        table = Table(
            box=box.SIMPLE_HEAVY,
            pad_edge=False,
            style="markdown.table.border",
            show_edge=True,
            collapse_padding=True,
            leading=0,
            padding=(0, 1),
        )
        palette = self.header_palette

        if self.header is not None and self.header.row is not None:
            for idx, column in enumerate(self.header.row.cells):
                heading = column.content.copy()
                style = palette[idx % len(palette)]
                cell_style = style.replace("bold ", "")
                table.add_column(heading, header_style=style, style=cell_style)

        if self.body is not None:
            for row in self.body.rows:
                row_content = [element.content for element in row.cells]
                table.add_row(*row_content)

        yield table


class InstitutionalMarkdown(Markdown):
    elements = {**Markdown.elements, "table_open": InstitutionalTableElement}


def _segment_line_is_blank(line: list[Segment]) -> bool:
    return not line or all(not (seg.text or "").strip() for seg in line)


class SectionSpacer:
    """Blank line(s) between sections (Rich ``Group`` needs two lines for a visible gap)."""

    def __init__(self, lines: int = 2) -> None:
        self.lines = max(1, lines)

    def __rich_console__(self, console: Console, options):
        for _ in range(self.lines):
            yield Segment.line()


def _is_compact_check_block(renderable: RenderableType) -> bool:
    if not isinstance(renderable, RichText):
        return False
    plain = getattr(renderable, "plain", "") or str(renderable)
    return plain.strip().startswith("Controle")


class TightHeadingBody:
    """Render title and body back-to-back (Rich ``Group`` inserts a spacer line)."""

    def __init__(self, title: RenderableType, body: RenderableType) -> None:
        self.title = title
        self.body = body

    def __rich_console__(self, console: Console, options):
        title_lines = console.render_lines(self.title, options)
        has_title = bool(title_lines and not _segment_line_is_blank(title_lines[0]))
        if has_title:
            yield from title_lines[0]

        body_lines = [
            ln
            for ln in console.render_lines(self.body, options)
            if not _segment_line_is_blank(ln)
        ]
        for idx, line in enumerate(body_lines):
            if idx > 0 or has_title:
                yield Segment.line()
            yield from line


def _heading_level(line: str) -> int:
    m = re.match(r"^(#{1,6})\s+", line.strip())
    return len(m.group(1)) if m else 0


def _is_heading_line(line: str) -> bool:
    return bool(_HEADING_LINE_RE.match(line.strip()))


def _peel_institutional_checks(text: str) -> list[tuple[str, str]]:
    if not text or "<institutional_check>" not in text.lower():
        return [("text", text)] if (text or "").strip() else []

    pieces: list[tuple[str, str]] = []
    pos = 0
    for match in _INSTITUTIONAL_CHECK_BLOCK_RE.finditer(text):
        if match.start() > pos:
            chunk = text[pos : match.start()].strip()
            if chunk:
                pieces.append(("text", chunk))
        body = match.group("body").strip()
        if body:
            pieces.append(("check", body))
        pos = match.end()
    if pos < len(text):
        tail = text[pos:].strip()
        if tail:
            pieces.append(("text", tail))
    return pieces or ([("text", text.strip())] if text.strip() else [])


def _render_institutional_check_compact(body: str, colors: dict[str, str]) -> RenderableType:
    items: list[str] = []
    for line in body.splitlines():
        line = line.strip()
        if not line:
            continue
        items.append(re.sub(r"^[-*+]\s+", "", line))

    label_style = colors.get("label", "bold #f92672")
    dim_style = "dim"

    if not items:
        return RichText("Controle", style=label_style)

    out = RichText()
    out.append("Controle  ", style=label_style)
    for idx, item in enumerate(items):
        if idx:
            out.append("  ·  ", style=dim_style)
        out.append(item, style=dim_style)
    return out


def _peel_heading_body_sections(text: str) -> list[tuple[str, str] | tuple[str, str, str]]:
    """Each heading line gets its own body until the next heading (any level)."""
    if not text or not text.strip():
        return []

    lines = text.splitlines()
    n = len(lines)
    heading_idxs: list[tuple[int, str]] = []
    for idx, line in enumerate(lines):
        hm = _HEADING_LINE_RE.match(line.strip())
        if hm:
            heading_idxs.append((idx, hm.group("h").strip()))

    if not heading_idxs:
        return [("md", text.strip())]

    pieces: list[tuple[str, str] | tuple[str, str, str]] = []
    cursor = 0
    for hi, (idx, h_line) in enumerate(heading_idxs):
        if idx > cursor:
            blob = "\n".join(lines[cursor:idx]).strip()
            if blob:
                pieces.append(("md", blob))
        body_start = idx + 1
        while body_start < n and not lines[body_start].strip():
            body_start += 1
        body_end = heading_idxs[hi + 1][0] if hi + 1 < len(heading_idxs) else n
        body = "\n".join(lines[body_start:body_end]).strip()
        pieces.append(("heading_body", h_line, body))
        cursor = body_end

    return pieces


def _render_heading_body_pair(
    heading_line: str,
    body_md: str,
    colors: dict[str, str],
    code_theme: str,
    *,
    label_columns: bool = True,
) -> RenderableType:
    hm = re.match(r"^(#{1,6})\s+(.+)$", heading_line.strip())
    if not hm:
        return InstitutionalMarkdown(f"{heading_line}\n{body_md}".strip(), code_theme=code_theme)
    level = min(6, len(hm.group(1)))
    style = colors.get(f"h{level}", colors["h2"])
    title = hm.group(2).strip()
    if not body_md.strip():
        return RichText(title, style=style)
    body_render = _render_body_with_embedded_labels(
        body_md.strip(),
        colors,
        code_theme,
        label_columns=label_columns,
    )
    return TightHeadingBody(RichText(title, style=style), body_render)


def _render_body_with_embedded_labels(
    body_md: str,
    colors: dict[str, str],
    code_theme: str,
    *,
    label_columns: bool,
) -> RenderableType:
    """Peel **Label:** lines from heading body; value always below label (checklist #5)."""
    lines = body_md.splitlines()
    parts: list[RenderableType] = []
    prose: list[str] = []
    idx = 0
    while idx < len(lines):
        stripped = lines[idx].strip()
        label_m = _LABEL_ONLY_LINE_RE.match(stripped)
        if label_m:
            if prose:
                blob = "\n".join(prose).strip()
                if blob:
                    parts.append(InstitutionalMarkdown(blob, code_theme=code_theme))
                prose = []
            # Zichtbare witregel vóór label na voorafgaande content
            if parts:
                parts.append(SectionSpacer(lines=2))
            label = label_m.group("label").strip()
            idx += 1
            value_lines: list[str] = []
            while idx < len(lines):
                nxt = lines[idx].strip()
                if not nxt:
                    idx += 1
                    break
                if _LABEL_ONLY_LINE_RE.match(nxt) or _is_heading_line(lines[idx]):
                    break
                value_lines.append(lines[idx])
                idx += 1
            parts.append(
                _render_label_block(
                    label,
                    "\n".join(value_lines).strip(),
                    colors,
                    code_theme,
                    label_columns=label_columns,
                )
            )
            continue
        prose.append(lines[idx])
        idx += 1
    if prose:
        blob = "\n".join(prose).strip()
        if blob:
            parts.append(InstitutionalMarkdown(blob, code_theme=code_theme))
    if not parts:
        return RichText("")
    if len(parts) == 1:
        return parts[0]
    return Group(*parts)


def _render_label_block(
    label: str,
    body_md: str,
    colors: dict[str, str],
    code_theme: str,
    *,
    label_columns: bool,
) -> RenderableType:
    del label_columns  # layout is always label above value (10/10 checklist)
    label_text = RichText(f"{label}:", style=colors["label"])
    body = body_md.strip()
    if not body:
        return label_text
    if body.startswith("|"):
        return TightHeadingBody(
            label_text,
            InstitutionalMarkdown(body, code_theme=code_theme),
        )
    body_render = (
        InstitutionalMarkdown(body, code_theme=code_theme)
        if "\n" in body
        else RichText(body, style=colors.get("text", ""))
    )
    return TightHeadingBody(label_text, body_render)


def _iter_content_blocks(text: str) -> Iterator[tuple[str, str, str]]:
    from hermes_cli.markdown_output_normalize import coalesce_heading_content_chunks

    raw_chunks = [c for c in re.split(r"\n{2,}", text.strip()) if c.strip()]
    chunks = coalesce_heading_content_chunks(raw_chunks)
    for chunk in chunks:
        if not chunk.strip():
            continue
        lines = chunk.split("\n")
        first = lines[0].strip()
        m = _LABEL_ONLY_LINE_RE.match(first)
        if m and len(lines) > 1 and not first.startswith("#"):
            body = "\n".join(lines[1:]).strip()
            yield ("label", m.group("label").strip(), body)
            continue
        yield ("md", chunk.strip(), "")


def _assemble_with_section_spacing(blocks: list[RenderableType]) -> RenderableType:
    """One blank line between sections; title+body stay flush inside each section."""
    if not blocks:
        return RichText("")
    if len(blocks) == 1:
        return blocks[0]

    spaced: list[RenderableType] = []
    for idx, part in enumerate(blocks):
        if idx > 0:
            gap = 1 if _is_compact_check_block(blocks[idx - 1]) else 2
            spaced.append(SectionSpacer(lines=gap))
        spaced.append(part)
    return Group(*spaced)


def render_institutional_assistant(
    text: str,
    *,
    palette: str = "demo",
    label_columns: bool = True,
    code_theme: str = "monokai",
    already_normalized: bool = False,
) -> RenderableType:
    plain = text or ""
    if not already_normalized:
        plain = normalize_assistant_markdown(plain)
    if not plain.strip():
        return RichText("")

    palette_key = (palette or "demo").strip().lower()
    all_palettes = _get_all_palettes()
    colors = all_palettes.get(palette_key, all_palettes["demo"])
    InstitutionalTableElement.header_palette = table_header_palette(palette_key)

    blocks: list[RenderableType] = []

    for segment_kind, segment_text in _peel_institutional_checks(plain):
        if segment_kind == "check":
            blocks.append(_render_institutional_check_compact(segment_text, colors))
            continue

        for section in _peel_heading_body_sections(segment_text):
            if section[0] == "heading_body":
                _, heading_line, body_md = section
                blocks.append(
                    _render_heading_body_pair(
                        heading_line,
                        body_md,
                        colors,
                        code_theme,
                        label_columns=label_columns,
                    )
                )
                continue

            md_blob = section[1]
            for kind, a, b in _iter_content_blocks(md_blob):
                if kind == "label":
                    blocks.append(
                        _render_label_block(
                            a, b, colors, code_theme, label_columns=label_columns
                        )
                    )
                else:
                    for sub in _peel_heading_body_sections(a):
                        if sub[0] == "heading_body":
                            _, h_line, body = sub
                            blocks.append(
                                _render_heading_body_pair(
                                    h_line,
                                    body,
                                    colors,
                                    code_theme,
                                    label_columns=label_columns,
                                )
                            )
                        else:
                            blob = sub[1]
                            if blob.strip():
                                blocks.append(
                                    InstitutionalMarkdown(blob, code_theme=code_theme)
                                )

    if not blocks:
        return InstitutionalMarkdown(plain, code_theme=code_theme)
    return _assemble_with_section_spacing(blocks)
