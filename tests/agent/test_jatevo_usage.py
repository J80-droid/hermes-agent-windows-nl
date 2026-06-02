from agent.jatevo_usage import (
    append_jatevo_429_hint_if_needed,
    fetch_jatevo_quota,
    format_jatevo_status_bar_quota,
    is_jatevo_daily_quota_http_error,
    is_jatevo_runtime,
    render_jatevo_quota_lines,
    resolve_status_bar_jatevo_quota,
)


class _Response:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


class _Client:
    def __init__(self, payload):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def get(self, url, headers=None):
        return _Response(self._payload)


def test_fetch_jatevo_quota_dashboard_fields(monkeypatch):
    monkeypatch.setattr(
        "agent.jatevo_usage.resolve_runtime_provider",
        lambda requested, explicit_base_url=None, explicit_api_key=None: {
            "base_url": "https://jatevo.ai/v1",
            "api_key": "sk-clb-test",
        },
    )
    monkeypatch.setattr(
        "agent.jatevo_usage.httpx.Client",
        lambda timeout=12.0: _Client(
            {
                "request_count": 5,
                "limits": [
                    {
                        "limit_type": "requests",
                        "limit_window": "daily",
                        "max_value": 562,
                        "current_value": 0,
                        "remaining_value": 562,
                        "reset_at": "2026-06-03T00:00:00Z",
                    }
                ],
            }
        ),
    )

    report = fetch_jatevo_quota(api_key="sk-clb-test")

    assert report.daily_used == 0
    assert report.daily_max == 562
    lines = render_jatevo_quota_lines(report)
    assert "Daily requests: 0 / 562 (current key usage)" in lines
    assert "Daily quota: 562 requests/day" in lines


def test_render_jatevo_quota_lines_includes_usage_stats_by_default(monkeypatch):
    monkeypatch.setattr(
        "agent.jatevo_usage.resolve_runtime_provider",
        lambda requested, explicit_base_url=None, explicit_api_key=None: {
            "base_url": "https://jatevo.ai/v1",
            "api_key": "sk-clb-test",
        },
    )
    monkeypatch.setattr(
        "agent.jatevo_usage.httpx.Client",
        lambda timeout=12.0: _Client(
            {
                "request_count": 12,
                "total_tokens": 45000,
                "total_cost_usd": 0.0832,
                "limits": [
                    {
                        "limit_type": "requests",
                        "limit_window": "daily",
                        "max_value": 562,
                        "current_value": 12,
                        "remaining_value": 550,
                        "reset_at": "2026-06-03T00:00:00Z",
                    }
                ],
            }
        ),
    )
    report = fetch_jatevo_quota(api_key="sk-clb-test")
    stat_lines = render_jatevo_quota_lines(report)
    assert "Tokens today: 45,000" in stat_lines
    assert "Cost today: $0.0832" in stat_lines
    assert "Tokens today" not in render_jatevo_quota_lines(
        report, include_usage_stats=False
    )


def test_is_jatevo_runtime_detects_custom_with_jatevo_url():
    assert is_jatevo_runtime("custom", "https://jatevo.ai/v1")
    assert is_jatevo_runtime("custom", "https://2.lb.jatevo.ai/v1")
    assert not is_jatevo_runtime("openrouter", "https://openrouter.ai/api/v1")
    assert not is_jatevo_runtime("custom", "https://evil.jatevo.ai.attacker.com/v1")


def test_is_jatevo_daily_quota_detects_rate_limit_error_without_status_code():
    class RateLimitError(Exception):
        pass

    err = RateLimitError("too many requests")
    assert is_jatevo_daily_quota_http_error(
        err,
        provider="custom",
        base_url="https://jatevo.ai/v1",
    )


def test_status_bar_quota_label_and_cache(monkeypatch):
    monkeypatch.setattr(
        "agent.jatevo_usage.resolve_runtime_provider",
        lambda requested, explicit_base_url=None, explicit_api_key=None: {
            "base_url": "https://jatevo.ai/v1",
            "api_key": "sk-clb-test",
        },
    )
    monkeypatch.setattr(
        "agent.jatevo_usage.httpx.Client",
        lambda timeout=12.0: _Client(
            {
                "limits": [
                    {
                        "limit_type": "requests",
                        "limit_window": "daily",
                        "max_value": 562,
                        "current_value": 3,
                        "remaining_value": 559,
                    }
                ],
            }
        ),
    )
    result = resolve_status_bar_jatevo_quota(
        provider="custom",
        base_url="https://jatevo.ai/v1",
        api_key="sk-clb-test",
        cache_bucket="test",
    )
    assert result == ("JV 3/562", 1)


def test_append_jatevo_429_hint_idempotent():
    err = Exception("HTTP 429")
    err.status_code = 429  # type: ignore[attr-defined]
    once = append_jatevo_429_hint_if_needed(
        "HTTP 429: quota",
        err,
        provider="custom",
        base_url="https://jatevo.ai/v1",
    )
    twice = append_jatevo_429_hint_if_needed(once, err, provider="custom", base_url="https://jatevo.ai/v1")
    assert once == twice
    assert "/jquota" in once
