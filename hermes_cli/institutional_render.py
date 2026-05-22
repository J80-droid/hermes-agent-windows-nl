"""Institutional Rich renderer for assistant answers (demo palette, per-column tables)."""

from __future__ import annotations

import re
from typing import ClassVar, Iterator

from rich import box
from rich.columns import Columns
from rich.console import Group, RenderableType
from rich.text import Text as RichText
from rich.markdown import Markdown, TableElement
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

from hermes_cli.markdown_output_normalize import normalize_assistant_markdown

# Per-column table header styles (Rich demo order).
TABLE_HEADER_PALETTE_DEMO = (
    "bold cyan",
    "bold green",
    "bold magenta",
    "bold yellow",
)

_LABEL_ONLY_LINE_RE = re.compile(r"^\*\*(?P<label>[^*\n]+?):\*\*\s*$")

_PALETTES: dict[str, dict[str, str]] = {
    "demo": {
        "h1": "bold cyan",
        "h2": "bold green",
        "h3": "bold magenta",
        "h4": "bold yellow",
        "h5": "italic bright_white",
        "h6": "dim",
        "strong": "bold bright_white",
        "code": "cyan",
        "link": "underline cyan",
        "table_header": "bold cyan",
        "label": "bold magenta",
        "text": "white",
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


def assistant_markdown_theme(palette: str = "demo") -> Theme:
    """Rich theme for assistant answers only (not Hermes UI skin)."""
    key = (palette or "demo").strip().lower()
    colors = _PALETTES.get(key, _PALETTES["demo"])
    return Theme(
        {
            "markdown.h1": colors["h1"],
            "markdown.h2": colors["h2"],
            "markdown.h3": colors["h3"],
            "markdown.h4": colors["h4"],
            "markdown.h5": colors["h5"],
            "markdown.h6": colors["h6"],
            "markdown.strong": colors["strong"],
            "markdown.em": "italic",
            "markdown.block_quote": "dim",
            "markdown.code": colors["code"],
            "markdown.code_block": "dim",
            "markdown.link": colors["link"],
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
    key = (palette or "demo").strip().lower()
    if key == "hermes":
        return ("bold #FFD700", "bold #FFBF00", "bold #DAA520", "bold #FFF8DC")
    if key == "neutral":
        return ("bold bright_cyan", "bold white", "bold bright_black", "dim")
    return TABLE_HEADER_PALETTE_DEMO


class InstitutionalTableElement(TableElement):
    """Markdown table with a distinct header style per column."""

    header_palette: ClassVar[tuple[str, ...]] = TABLE_HEADER_PALETTE_DEMO

    def __rich_console__(self, console, options):
        table = Table(
            box=box.SIMPLE_HEAVY,
            pad_edge=False,
            style="markdown.table.border",
            show_edge=True,
            collapse_padding=True,
            leading=1,
        )
        palette = self.header_palette

        if self.header is not None and self.header.row is not None:
            for idx, column in enumerate(self.header.row.cells):
                heading = column.content.copy()
                style = palette[idx % len(palette)]
                table.add_column(heading, header_style=style)

        if self.body is not None:
            for row in self.body.rows:
                row_content = [element.content for element in row.cells]
                table.add_row(*row_content)

        yield table


class InstitutionalMarkdown(Markdown):
    """Rich Markdown with institutional table rendering."""

    elements = {**Markdown.elements, "table_open": InstitutionalTableElement}


def _iter_content_blocks(text: str) -> Iterator[tuple[str, str, str]]:
    """Yield ('md', markdown, '') or ('label', label_plain, body_md)."""
    chunks = re.split(r"\n{2,}", text.strip())
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
        # Sub-split large markdown chunks at headings for clearer vertical spacing in Group.
        subparts = re.split(r"(?=\n#{1,6}\s)", "\n" + chunk.strip())
        for sub in subparts:
            sub = sub.strip()
            if sub:
                yield ("md", sub, "")


def render_institutional_assistant(
    text: str,
    *,
    palette: str = "demo",
    label_columns: bool = True,
    code_theme: str = "monokai",
    already_normalized: bool = False,
) -> RenderableType:
    """Build a Rich renderable for normalized assistant markdown."""
    plain = text or ""
    if not already_normalized:
        plain = normalize_assistant_markdown(plain)
    if not plain.strip():
        return RichText("")

    palette_key = (palette or "demo").strip().lower()
    colors = _PALETTES.get(palette_key, _PALETTES["demo"])
    InstitutionalTableElement.header_palette = table_header_palette(palette_key)

    parts: list[RenderableType] = []
    for kind, a, b in _iter_content_blocks(plain):
        if kind == "label" and label_columns:
            label_text = RichText(f"{a}:", style=colors["label"])
            body_md = InstitutionalMarkdown(b, code_theme=code_theme)
            parts.append(
                Columns(
                    [label_text, body_md],
                    expand=True,
                    equal=False,
                )
            )
        else:
            parts.append(InstitutionalMarkdown(a, code_theme=code_theme))

    if not parts:
        return InstitutionalMarkdown(plain, code_theme=code_theme)
    if len(parts) == 1:
        return parts[0]
    spaced: list[RenderableType] = []
    for idx, part in enumerate(parts):
        if idx > 0:
            spaced.append(RichText(""))
        spaced.append(part)
    return Group(*spaced)
