"""Unit tests for hermes_cli.status_bar_prompt_elapsed."""

from __future__ import annotations

import math
import time
from unittest.mock import patch

import pytest

from hermes_cli.status_bar_prompt_elapsed import (
    _EMOJI_FROZEN,
    _EMOJI_LIVE,
    format_prompt_elapsed_status_bar,
    prompt_elapsed_contains_emoji,
    should_show_prompt_timer_emoji,
)

_FIXED_NOW = 1_700_000_000.0


# --- prompt_elapsed_contains_emoji ---


class TestPromptElapsedContainsEmoji:
    def test_happy_path_detects_live_and_frozen(self):
        assert prompt_elapsed_contains_emoji(f"{_EMOJI_LIVE} 12s")
        assert prompt_elapsed_contains_emoji(f"{_EMOJI_FROZEN} 0s")

    def test_plain_time_has_no_emoji(self):
        assert not prompt_elapsed_contains_emoji("26s")
        assert not prompt_elapsed_contains_emoji("1m 3s")

    @pytest.mark.parametrize(
        "text",
        [None, "", "   ", "elapsed: 42s", "no timer here", "23f1 is not the glyph"],
    )
    def test_no_match_for_empty_or_unrelated(self, text):
        assert not prompt_elapsed_contains_emoji(text)  # type: ignore[arg-type]

    def test_both_glyphs_in_same_string(self):
        assert prompt_elapsed_contains_emoji(f"{_EMOJI_LIVE}x{_EMOJI_FROZEN}")


# --- should_show_prompt_timer_emoji ---


class TestShouldShowPromptTimerEmoji:
    def test_happy_path_true_when_enabled(self):
        assert should_show_prompt_timer_emoji(True) is True

    @pytest.mark.parametrize(
        "value",
        [False, 0, None, ""],
    )
    def test_falsy_or_non_bool_coerced(self, value):
        assert should_show_prompt_timer_emoji(value) is False

    @pytest.mark.parametrize("value", [1, "on", "yes"])
    def test_truthy_non_bool_uses_python_bool(self, value):
        assert should_show_prompt_timer_emoji(value) is True


# --- format_prompt_elapsed_status_bar: happy path ---


class TestFormatPromptElapsedHappyPath:
    def test_fresh_start_no_emoji(self):
        out = format_prompt_elapsed_status_bar(None, 0.0, show_emoji=False)
        assert out == "0s"
        assert not prompt_elapsed_contains_emoji(out)

    def test_fresh_start_with_emoji_upstream_parity(self):
        out = format_prompt_elapsed_status_bar(None, 0.0, show_emoji=True)
        assert out == f"{_EMOJI_FROZEN} 0s"

    def test_frozen_duration_minutes_seconds(self):
        out = format_prompt_elapsed_status_bar(None, 63.0, show_emoji=False)
        assert out == "1m 3s"

    def test_frozen_duration_hours(self):
        out = format_prompt_elapsed_status_bar(None, 3601.0, show_emoji=False)
        assert out == "1h 0m 1s"

    def test_frozen_duration_days(self):
        out = format_prompt_elapsed_status_bar(None, 90061.0, show_emoji=False)
        assert out == "1d 1h 1m"

    def test_live_elapsed_from_start_and_now(self):
        started = _FIXED_NOW - 42.0
        out = format_prompt_elapsed_status_bar(
            started, 0.0, live=True, show_emoji=False, now=_FIXED_NOW
        )
        assert out == "42s"

    def test_live_emoji_prefix(self):
        started = _FIXED_NOW - 12.0
        live_out = format_prompt_elapsed_status_bar(
            started, 0.0, live=True, show_emoji=True, now=_FIXED_NOW
        )
        frozen_out = format_prompt_elapsed_status_bar(None, 12.0, live=False, show_emoji=True)
        assert live_out.startswith(f"{_EMOJI_LIVE} ")
        assert frozen_out.startswith(f"{_EMOJI_FROZEN} ")

    def test_hours_without_trailing_seconds_when_zero(self):
        out = format_prompt_elapsed_status_bar(None, 3600.0, show_emoji=False)
        assert out == "1h 0m"

    def test_minutes_without_trailing_seconds_when_zero(self):
        out = format_prompt_elapsed_status_bar(None, 120.0, show_emoji=False)
        assert out == "2m"

    def test_sub_second_frozen_truncates_to_zero_seconds(self):
        out = format_prompt_elapsed_status_bar(None, 0.9, show_emoji=False)
        assert out == "0s"


# --- invalid input, non-finite, negative ---


class TestFormatPromptElapsedEdgeCases:
    def test_negative_duration_clamped_to_zero(self):
        out = format_prompt_elapsed_status_bar(None, -5.0, show_emoji=False)
        assert out == "0s"

    @pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
    def test_non_finite_duration_treated_as_zero(self, bad):
        out = format_prompt_elapsed_status_bar(None, bad, show_emoji=False)
        assert out == "0s"

    def test_non_finite_start_time_falls_back_to_duration(self):
        out = format_prompt_elapsed_status_bar(float("inf"), 45.0, show_emoji=False)
        assert out == "45s"

    def test_nan_start_time_uses_duration(self):
        out = format_prompt_elapsed_status_bar(float("nan"), 90.0, show_emoji=False)
        assert out == "1m 30s"

    def test_future_start_time_clamped_to_zero(self):
        future = _FIXED_NOW + 3600.0
        out = format_prompt_elapsed_status_bar(
            future, 0.0, live=True, show_emoji=False, now=_FIXED_NOW
        )
        assert out == "0s"

    @pytest.mark.parametrize(
        "invalid_start",
        ["not-a-time", [], {}, object()],
    )
    def test_invalid_start_type_uses_duration_only(self, invalid_start):
        out = format_prompt_elapsed_status_bar(invalid_start, 26.0, show_emoji=False)  # type: ignore[arg-type]
        assert out == "26s"

    @pytest.mark.parametrize("invalid_now", [float("nan"), float("inf"), "bad"])
    def test_invalid_now_falls_back_to_time_time(self, invalid_now):
        started = _FIXED_NOW - 30.0
        with patch(
            "hermes_cli.status_bar_prompt_elapsed.time.time",
            return_value=_FIXED_NOW,
        ) as mock_time:
            out = format_prompt_elapsed_status_bar(
                started,
                0.0,
                live=True,
                show_emoji=False,
                now=invalid_now,  # type: ignore[arg-type]
            )
        mock_time.assert_called_once()
        assert out == "30s"

    def test_valid_start_ignores_positive_duration(self):
        started = _FIXED_NOW - 10.0
        out = format_prompt_elapsed_status_bar(
            started, 999.0, live=False, show_emoji=False, now=_FIXED_NOW
        )
        assert out == "10s"

    def test_zero_duration_with_valid_start_uses_live_clock(self):
        started = _FIXED_NOW - 5.0
        out = format_prompt_elapsed_status_bar(
            started, 0.0, live=True, show_emoji=False, now=_FIXED_NOW
        )
        assert out == "5s"

    @pytest.mark.parametrize(
        "invalid_duration",
        [None, "30", []],  # non int/float -> 0s path when no start
    )
    def test_invalid_duration_coerced_for_fresh_start(self, invalid_duration):
        out = format_prompt_elapsed_status_bar(None, invalid_duration, show_emoji=False)  # type: ignore[arg-type]
        assert out == "0s"

    def test_bool_start_time_treated_as_numeric_timestamp(self):
        # bool is a subclass of int in Python; True == 1.0 epoch second formatting edge.
        out = format_prompt_elapsed_status_bar(
            True, 0.0, live=True, show_emoji=False, now=101.0
        )
        assert out == "1m 40s"

    def test_very_large_elapsed_days_format(self):
        out = format_prompt_elapsed_status_bar(None, 10 * 86400 + 3661.0, show_emoji=False)
        assert out.startswith("10d ")


# --- time.time mock: no accidental wall-clock dependency ---


class TestFormatPromptElapsedTimeMock:
    def test_missing_now_calls_time_time_once(self):
        started = 500.0
        with patch(
            "hermes_cli.status_bar_prompt_elapsed.time.time",
            return_value=530.0,
        ) as mock_time:
            out = format_prompt_elapsed_status_bar(
                started, 0.0, live=True, show_emoji=False, now=None
            )
        mock_time.assert_called_once()
        assert out == "30s"

    def test_finite_now_never_calls_time_time(self):
        with patch(
            "hermes_cli.status_bar_prompt_elapsed.time.time",
            return_value=999.0,
        ) as mock_time:
            format_prompt_elapsed_status_bar(
                _FIXED_NOW - 1.0, 0.0, live=True, show_emoji=False, now=_FIXED_NOW
            )
        mock_time.assert_not_called()


# --- emoji toggle negative scenarios ---


class TestFormatPromptElapsedEmojiNegative:
    def test_show_emoji_false_never_prefixes(self):
        cases = [
            (None, 0.0, False),
            (None, 26.0, False),
            (_FIXED_NOW - 5.0, 0.0, True),
        ]
        for start, dur, live in cases:
            out = format_prompt_elapsed_status_bar(
                start, dur, live=live, show_emoji=False, now=_FIXED_NOW
            )
            assert not prompt_elapsed_contains_emoji(out)

    def test_show_emoji_true_always_prefixes_non_fresh(self):
        out = format_prompt_elapsed_status_bar(None, 5.0, show_emoji=True)
        assert out.startswith(f"{_EMOJI_FROZEN} ")

    def test_fresh_start_emoji_frozen_not_live(self):
        out = format_prompt_elapsed_status_bar(
            None, 0.0, live=True, show_emoji=True
        )
        assert out.startswith(f"{_EMOJI_FROZEN} ")


# --- parametrized scale boundaries ---


@pytest.mark.parametrize(
    "seconds,expected",
    [
        (59.0, "59s"),
        (60.0, "1m"),
        (61.0, "1m 1s"),
        (3599.0, "59m 59s"),
        (3600.0, "1h 0m"),
        (86399.0, "23h 59m 59s"),
        (86400.0, "1d 0h 0m"),
    ],
)
def test_time_scale_boundaries(seconds, expected):
    out = format_prompt_elapsed_status_bar(None, seconds, show_emoji=False)
    assert out == expected


# --- legacy flat tests (kept for stable -k filters / E2E inline runner) ---


def test_no_emoji_fresh_start():
    out = format_prompt_elapsed_status_bar(None, 0.0, show_emoji=False)
    assert out == "0s"
    assert not prompt_elapsed_contains_emoji(out)


def test_no_emoji_seconds():
    started = time.time() - 42.0
    out = format_prompt_elapsed_status_bar(started, 0.0, live=True, show_emoji=False, now=time.time())
    assert out.endswith("s")
    assert "m" not in out or out.count("m") == 0
    assert not prompt_elapsed_contains_emoji(out)


def test_no_emoji_minutes_and_seconds():
    out = format_prompt_elapsed_status_bar(None, 63.0, show_emoji=False)
    assert out == "1m 3s"


def test_no_emoji_hours():
    out = format_prompt_elapsed_status_bar(None, 3601.0, show_emoji=False)
    assert out == "1h 0m 1s"


def test_emoji_upstream_parity_fresh():
    out = format_prompt_elapsed_status_bar(None, 0.0, show_emoji=True)
    assert out == f"{_EMOJI_FROZEN} 0s"


def test_emoji_live_vs_frozen():
    started = time.time() - 12.0
    live_out = format_prompt_elapsed_status_bar(
        started, 0.0, live=True, show_emoji=True, now=time.time()
    )
    frozen_out = format_prompt_elapsed_status_bar(None, 12.0, live=False, show_emoji=True)
    assert live_out.startswith(f"{_EMOJI_LIVE} ")
    assert frozen_out.startswith(f"{_EMOJI_FROZEN} ")


def test_negative_duration_clamped():
    out = format_prompt_elapsed_status_bar(None, -5.0, show_emoji=False)
    assert out == "0s"


def test_days_scale():
    out = format_prompt_elapsed_status_bar(None, 90061.0, show_emoji=False)
    assert out.startswith("1d ")


def test_non_finite_duration_treated_as_zero():
    out = format_prompt_elapsed_status_bar(None, float("nan"), show_emoji=False)
    assert out == "0s"


def test_non_finite_start_time_uses_duration():
    out = format_prompt_elapsed_status_bar(float("inf"), 45.0, show_emoji=False)
    assert out == "45s"


def test_future_start_time_clamped_to_zero():
    future = time.time() + 3600.0
    out = format_prompt_elapsed_status_bar(future, 0.0, live=True, show_emoji=False, now=time.time())
    assert out == "0s"


def test_should_show_prompt_timer_emoji_helper():
    assert should_show_prompt_timer_emoji(True) is True
    assert should_show_prompt_timer_emoji(False) is False
