"""Shared Rich markdown rendering for classic CLI, gateway, and rich_output bridge."""

from __future__ import annotations

import re
import shutil
import sys
from io import StringIO
from pathlib import Path
from rich.console import Console
from rich.markdown import Markdown
from rich.text import Text as RichText
from rich.theme import Theme

from agent.markdown_tables import realign_markdown_tables
from hermes_cli.institutional_render import (
    assistant_markdown_theme,
    render_institutional_assistant,
)
from hermes_cli.markdown_output_normalize import normalize_assistant_markdown

_WINDOWS_PATH_WITH_DOT_SEGMENT_RE = re.compile(
    r"(?i)(?:\b[a-z]:\\|\\\\)[^\s`]*\\\.[^\s`]*"
)


def _wrap_bron_citations_for_display(text: str) -> str:
    try:
        rag_dir = Path(__file__).resolve().parent.parent / "scripts" / "rag_pipeline"
        if str(rag_dir) not in sys.path:
            sys.path.insert(0, str(rag_dir))
        from rag_display import wrap_bron_citations_for_markdown_display

        return wrap_bron_citations_for_markdown_display(text)
    except Exception:
        return text


def _preserve_windows_dot_segments_for_markdown(text: str) -> str:
    if "\\." not in text:
        return text

    def _protect(match: re.Match[str]) -> str:
        return re.sub(r"(?<!\\)\\(?=\.)", r"\\\\", match.group(0))

    return _WINDOWS_PATH_WITH_DOT_SEGMENT_RE.sub(_protect, text)


def _rich_text_from_ansi(text: str) -> RichText:
    return RichText.from_ansi(text or "")


def strip_markdown_syntax(text: str) -> str:
    """Best-effort markdown marker removal for plain-text display."""
    plain = _rich_text_from_ansi(text or "").plain
    plain = re.sub(r"^\s{0,3}(?:[-_]\s*){3,}$", "", plain, flags=re.MULTILINE)
    plain = re.sub(r"^\s{0,3}(?:\*\s*){3}\s*$", "", plain, flags=re.MULTILINE)
    plain = re.sub(r"^\s{0,3}#{1,6}\s+", "", plain, flags=re.MULTILINE)
    plain = re.sub(r"(```+|~~~+)", "", plain)
    plain = re.sub(r"`([^`]*)`", r"\1", plain)
    plain = re.sub(r"!\[([^\]]*)\]\([^\)]*\)", r"\1", plain)
    plain = re.sub(r"\[([^\]]+)\]\([^\)]*\)", r"\1", plain)
    plain = re.sub(r"\*\*\*([^*]+)\*\*\*", r"\1", plain)
    plain = re.sub(r"(?<!\w)___([^_]+)___(?!\w)", r"\1", plain)
    plain = re.sub(r"\*\*([^*]+)\*\*", r"\1", plain)
    plain = re.sub(r"(?<!\w)__([^_]+)__(?!\w)", r"\1", plain)
    plain = re.sub(r"\*([^\s*][^*]*?[^\s*])\*", r"\1", plain)
    plain = re.sub(r"(?<!\w)_([^_]+)_(?!\w)", r"\1", plain)
    plain = re.sub(r"~~([^~]+)~~", r"\1", plain)
    plain = re.sub(r"\n{3,}", "\n\n", plain)
    return plain.strip("\n")


def skin_markdown_theme() -> Theme:
    """Rich theme for ``final_response_markdown=render`` — skin gold, not default magenta."""
    try:
        from hermes_cli.skin_engine import get_active_skin

        skin = get_active_skin()
        title = skin.get_color("banner_title", "#FFD700")
        accent = skin.get_color("banner_accent", "#FFBF00")
        label = skin.get_color("ui_label", "#DAA520")
        dim = skin.get_color("banner_dim", "#B8860B")
        text = skin.get_color("banner_text", "#FFF8DC")
        ok = skin.get_color("ui_ok", "#8FBC8F")
    except Exception:
        title, accent, label, dim = "#FFD700", "#FFBF00", "#DAA520", "#B8860B"
        text, ok = "#FFF8DC", "#8FBC8F"

    return Theme(
        {
            "markdown.h1": f"bold {title} underline",
            "markdown.h2": f"bold {accent} underline",
            "markdown.h3": f"bold {label}",
            "markdown.h4": f"bold {label} italic",
            "markdown.h5": f"{label} italic",
            "markdown.h6": f"{dim} italic",
            "markdown.strong": f"bold {label}",
            "markdown.em": "italic",
            "markdown.block_quote": dim,
            "markdown.code": accent,
            "markdown.code_block": dim,
            "markdown.link": f"underline {accent}",
            "markdown.link_url": f"underline {dim}",
            "markdown.hr": dim,
            "markdown.item": text,
            "markdown.item.bullet": dim,
            "markdown.item.number": dim,
            "markdown.table.header": f"bold {accent}",
            "markdown.table.border": dim,
        }
    )


def _display_config() -> dict:
    try:
        from hermes_cli.config import CLI_CONFIG

        block = CLI_CONFIG.get("display")
        if isinstance(block, dict):
            return block
    except Exception:
        pass
    return {}


def get_assistant_render_settings() -> dict:
    """Assistant answer render options (independent of Hermes UI skin)."""
    d = _display_config()
    style = str(d.get("assistant_render_style", "institutional_rich")).strip().lower()
    if style not in {"institutional_rich", "markdown_legacy"}:
        style = "institutional_rich"
    palette = str(d.get("assistant_palette", "demo")).strip().lower()
    if palette not in {"demo", "hermes", "neutral"}:
        palette = "demo"
    label_cols = d.get("assistant_label_columns", True)
    if isinstance(label_cols, str):
        label_cols = label_cols.strip().lower() in {"1", "true", "yes", "on"}
    return {
        "assistant_render_style": style,
        "assistant_palette": palette,
        "assistant_label_columns": bool(label_cols),
    }


def default_panel_width(cols: int | None = None) -> int:
    if cols is not None:
        return max(20, int(cols) - 12)
    try:
        width = shutil.get_terminal_size((80, 24)).columns
    except Exception:
        width = 80
    return max(20, width - 12)


def prepare_assistant_markdown_plain(
    text: str,
    *,
    panel_width: int | None = None,
    normalize_layout: bool = True,
) -> str:
    """Plain markdown string ready for Rich ``Markdown``."""
    plain = _rich_text_from_ansi(text or "").plain
    if normalize_layout:
        plain = normalize_assistant_markdown(plain)
    plain = _wrap_bron_citations_for_display(plain)
    plain = _preserve_windows_dot_segments_for_markdown(plain)
    width = panel_width if panel_width is not None else default_panel_width()
    return realign_markdown_tables(plain, width)


def render_final_assistant_markdown(
    text: str,
    mode: str = "render",
    *,
    panel_width: int | None = None,
):
    """Render final assistant content as markdown, stripped text, or raw ANSI text."""
    width = panel_width if panel_width is not None else default_panel_width()
    normalized_mode = str(mode or "render").strip().lower()
    text = text or ""

    if normalized_mode == "strip":
        return RichText(realign_markdown_tables(strip_markdown_syntax(text), width))
    if normalized_mode == "raw":
        return _rich_text_from_ansi(text)

    plain = prepare_assistant_markdown_plain(text, panel_width=width)
    settings = get_assistant_render_settings()
    if settings["assistant_render_style"] == "institutional_rich":
        return render_institutional_assistant(
            plain,
            palette=settings["assistant_palette"],
            label_columns=settings["assistant_label_columns"],
            already_normalized=True,
        )
    return Markdown(plain)


def get_assistant_console_theme() -> Theme:
    """Rich Console theme for rendering assistant answer panels (not UI chrome)."""
    settings = get_assistant_render_settings()
    if settings["assistant_render_style"] == "institutional_rich":
        return assistant_markdown_theme(settings["assistant_palette"])
    return skin_markdown_theme()


def format_response_ansi(text: str, cols: int = 80) -> str | None:
    """Render assistant markdown to ANSI for TUI gateway ``payload.rendered``."""
    try:
        renderable = render_final_assistant_markdown(
            text,
            mode="render",
            panel_width=default_panel_width(cols),
        )
        buf = StringIO()
        Console(
            file=buf,
            width=max(20, cols),
            force_terminal=True,
            color_system="truecolor",
            theme=get_assistant_console_theme(),
        ).print(renderable)
        return buf.getvalue()
    except Exception:
        return None


class StreamingRenderer:
    """Incremental Rich renderer for gateway stream events (best-effort)."""

    def __init__(self, cols: int = 80) -> None:
        self.cols = cols
        self._buf = ""

    def feed(self, chunk: str) -> str | None:
        """Accumulate deltas only; Ink uses raw ``text`` (#16391). Final ANSI on ``finish``."""
        if not chunk:
            return None
        self._buf += chunk
        return None

    def finish(self) -> str | None:
        if not self._buf:
            return None
        return format_response_ansi(self._buf, self.cols)
