"""Tests for two-row classic CLI status bar packing."""

from hermes_cli.status_bar_layout import (
    STATUS_BAR_MAX_LINES,
    fragments_plain_text,
    pack_status_bar_plain_lines,
    should_use_status_bar_second_line,
    truncate_status_bar_end,
)


def test_status_bar_max_lines_is_two():
    assert STATUS_BAR_MAX_LINES == 2


def test_should_use_second_line_when_model_row_overflows():
    line1 = " ⚕ provider/vendor/some-very-long-model-id"
    metrics = "12k/128k │ ████░░ 42%"
    assert should_use_status_bar_second_line(
        line1_width=60,
        line1_text=line1,
        metrics_text=metrics,
    )


def test_pack_status_bar_plain_lines_splits_to_two_rows():
    line1 = " ⚕ provider/vendor/some-very-long-model-id"
    metrics = "12k/128k │ ████░░ 42% │ $0.12"
    row1, row2 = pack_status_bar_plain_lines(
        line1_text=line1,
        metrics_text=metrics,
        line1_width=60,
        line2_width=60,
    )
    assert row2 is not None
    assert "12k/128k" in row2
    assert "some-very-long-model-id" in row1


def test_pack_status_bar_plain_lines_single_row_when_fits():
    line1 = " ⚕ gpt-4"
    metrics = "12k/128k"
    row1, row2 = pack_status_bar_plain_lines(
        line1_text=line1,
        metrics_text=metrics,
        line1_width=120,
        line2_width=120,
    )
    assert row2 is None
    assert "gpt-4" in row1
    assert "12k/128k" in row1


def test_fragments_plain_text_joins_styles():
    frags = [("class:a", " ⚕ "), ("class:b", "model")]
    assert fragments_plain_text(frags) == " ⚕ model"


def test_should_use_second_line_when_line1_width_invalid():
    assert should_use_status_bar_second_line(
        line1_width=0,
        line1_text=" ⚕ model",
        metrics_text="ctx",
    )


def test_truncate_status_bar_end_adds_ellipsis():
    text = "x" * 100
    out = truncate_status_bar_end(text, 12)
    assert out.endswith("…")
    assert len(out) < len(text)
