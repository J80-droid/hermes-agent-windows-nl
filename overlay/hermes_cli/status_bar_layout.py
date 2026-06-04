"""Pack classic CLI / prompt_toolkit status bar into at most two terminal rows.

Row 1: model (+ provider quota). Row 2: context, cost, throughput, and other metrics.
Used by ``HermesCLI._pack_status_bar_fragment_rows`` when terminal width is >= 76 cols.
"""

from __future__ import annotations

from typing import Sequence

STATUS_BAR_MAX_LINES = 2

StatusBarFragment = tuple[str, str]


def _display_width(text: str) -> int:
    try:
        from wcwidth import wcwidth

        total = 0

        for ch in text or "":
            w = wcwidth(ch)

            total += w if w is not None and w >= 0 else 1

        return total
    except Exception:
        return len(text or "")


def truncate_status_bar_end(text: str, max_width: int) -> str:
    if max_width <= 0:
        return ""
    if _display_width(text) <= max_width:
        return text
    ellipsis = "…"
    ellipsis_width = _display_width(ellipsis)
    if max_width <= ellipsis_width:
        return ellipsis[:max_width]
    out: list[str] = []
    width = 0
    for ch in text:
        ch_width = _display_width(ch)
        if width + ch_width + ellipsis_width > max_width:
            break
        out.append(ch)
        width += ch_width
    return "".join(out) + ellipsis


def should_use_status_bar_second_line(
    *,
    line1_width: int,
    line1_text: str,
    metrics_text: str,
) -> bool:
    metrics_text = str(metrics_text or "")
    if not metrics_text.strip():
        return False
    line1_width = max(1, int(line1_width or 1))
    if _display_width(line1_text) > line1_width:
        return True
    combined = f"{line1_text} │ {metrics_text}"
    return _display_width(combined) > line1_width


def fragments_plain_text(frags: Sequence[StatusBarFragment]) -> str:
    """Join styled fragment tuples into one plain string."""
    return "".join(text for _, text in frags)


def pack_status_bar_plain_lines(
    *,
    line1_text: str,
    metrics_text: str,
    line1_width: int,
    line2_width: int,
    max_lines: int = STATUS_BAR_MAX_LINES,
) -> tuple[str, str | None]:
    """Return one or two plain-text rows for the status bar."""
    metrics_text = str(metrics_text or "").strip()
    if max_lines < 2 or not should_use_status_bar_second_line(
        line1_width=line1_width,
        line1_text=line1_text,
        metrics_text=metrics_text,
    ):
        single = line1_text
        if metrics_text:
            single = f"{line1_text} │ {metrics_text}"
        return truncate_status_bar_end(single, line1_width), None
    line1 = truncate_status_bar_end(line1_text, line1_width)
    line2 = truncate_status_bar_end(metrics_text, line2_width) if metrics_text else None
    return line1, line2
