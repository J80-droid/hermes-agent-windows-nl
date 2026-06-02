import httpx

from agent.venice_usage import (
    append_venice_429_hint_if_needed,
    fetch_venice_quota,
    filter_models_by_venice_trait,
    format_venice_status_bar_quota,
    is_venice_runtime,
    render_venice_quota_lines,
    resolve_status_bar_venice_quota,
    resolve_venice_openai_model,
)
from agent.account_usage import fetch_account_usage, render_account_usage_lines


class _Response:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


class _RoutingClient:
    def __init__(self, routes):
        self._routes = routes

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def get(self, url, headers=None, params=None):
        path = url.split("?", 1)[0]
        for prefix, payload in sorted(self._routes.items(), key=lambda item: -len(item[0])):
            if path.endswith(prefix) or prefix in path:
                if payload is None:
                    request = httpx.Request("GET", url)
                    response = httpx.Response(401, request=request)
                    raise httpx.HTTPStatusError(
                        "401", request=request, response=response
                    )
                return _Response(payload, status_code=200)
        return _Response(None, status_code=404)


def test_is_venice_runtime_host_safe():
    assert is_venice_runtime("custom", "https://api.venice.ai/api/v1")
    assert not is_venice_runtime("custom", "https://evil.venice.ai.attacker.com/v1")


def test_fetch_venice_quota_merges_rate_limits_when_billing_admin_only(monkeypatch):
    monkeypatch.setattr(
        "agent.venice_usage.resolve_runtime_provider",
        lambda requested, explicit_base_url=None, explicit_api_key=None: {
            "base_url": "https://api.venice.ai/api/v1",
            "api_key": "vn-test",
        },
    )
    monkeypatch.setattr(
        "agent.venice_usage.httpx.Client",
        lambda timeout=12.0: _RoutingClient(
            {
                "/billing/balance": None,
                "/api_keys/rate_limits": {
                    "data": {
                        "accessPermitted": True,
                        "balances": {"DIEM": 9.5, "USD": 25.0},
                        "nextEpochBegins": "2026-06-03T00:00:00.000Z",
                    }
                },
            }
        ),
    )

    report = fetch_venice_quota(api_key="vn-test")

    assert report.diem_remaining == 9.5
    assert report.usd_balance == 25.0
    assert report.billing_available is False
    assert format_venice_status_bar_quota(report) == "VN 9.5 DIEM"


def test_fetch_venice_quota_with_billing_epoch(monkeypatch):
    monkeypatch.setattr(
        "agent.venice_usage.resolve_runtime_provider",
        lambda requested, explicit_base_url=None, explicit_api_key=None: {
            "base_url": "https://api.venice.ai/api/v1",
            "api_key": "vn-admin",
        },
    )
    monkeypatch.setattr(
        "agent.venice_usage.httpx.Client",
        lambda timeout=12.0: _RoutingClient(
            {
                "/billing/balance": {
                    "canConsume": True,
                    "consumptionCurrency": "DIEM",
                    "balances": {"diem": 90.5, "usd": 25},
                    "diemEpochAllocation": 100,
                },
                "/api_keys/rate_limits": {"data": {"accessPermitted": True, "balances": {}}},
            }
        ),
    )

    report = fetch_venice_quota(api_key="vn-admin")

    assert report.billing_available is True
    assert format_venice_status_bar_quota(report) == "VN 90.5/100.0"


def test_account_usage_venice_custom_provider(monkeypatch):
    monkeypatch.setattr(
        "agent.venice_usage.resolve_runtime_provider",
        lambda requested, explicit_base_url=None, explicit_api_key=None: {
            "base_url": "https://api.venice.ai/api/v1",
            "api_key": "vn-test",
        },
    )
    monkeypatch.setattr(
        "agent.venice_usage.httpx.Client",
        lambda timeout=12.0: _RoutingClient(
            {
                "/billing/balance": None,
                "/api_keys/rate_limits": {
                    "data": {
                        "balances": {"DIEM": 5.0, "USD": 1.0},
                        "nextEpochBegins": "2026-06-03T00:00:00.000Z",
                    }
                },
            }
        ),
    )

    snapshot = fetch_account_usage(
        "custom",
        base_url="https://api.venice.ai/api/v1",
        api_key="vn-test",
    )

    assert snapshot is not None
    assert snapshot.provider == "venice"
    lines = render_account_usage_lines(snapshot)
    assert any("DIEM balance: 5.0000" in line for line in lines)


def test_append_venice_429_hint():
    err = Exception("HTTP 429")
    err.status_code = 429  # type: ignore[attr-defined]
    once = append_venice_429_hint_if_needed(
        "HTTP 429",
        err,
        provider="custom",
        base_url="https://api.venice.ai/api/v1",
    )
    assert "/vquota" in once


def test_fetch_venice_quota_extended(monkeypatch):
    monkeypatch.setattr(
        "agent.venice_usage.resolve_runtime_provider",
        lambda requested, explicit_base_url=None, explicit_api_key=None: {
            "base_url": "https://api.venice.ai/api/v1",
            "api_key": "vn-ext",
        },
    )
    monkeypatch.setattr(
        "agent.venice_usage.httpx.Client",
        lambda timeout=12.0: _RoutingClient(
            {
                "/billing/balance": None,
                "/api_keys/rate_limits": {
                    "data": {"balances": {"DIEM": 8.0}, "nextEpochBegins": "2026-06-03T00:00:00.000Z"}
                },
                "/billing/usage": {
                    "data": [
                        {
                            "timestamp": "2026-06-01T10:00:00.000Z",
                            "sku": "glm-llm",
                            "amount": -0.05,
                            "currency": "DIEM",
                            "units": 1,
                            "notes": "API Inference",
                            "inferenceDetails": {
                                "promptTokens": 10,
                                "completionTokens": 20,
                                "requestId": "r1",
                                "inferenceExecutionTime": 100,
                            },
                        }
                    ],
                    "pagination": {"total": 42},
                },
                "/billing/usage-analytics": {
                    "lookback": "7d",
                    "byDate": [{"date": "2026-06-01", "DIEM": 1.5, "USD": 0.25}],
                    "byModel": [
                        {
                            "modelName": "GLM 5.1",
                            "totalDiem": 1.5,
                            "totalUsd": 0.0,
                            "totalUnits": 1000,
                            "unitType": "tokens",
                            "modelType": "LLM",
                        }
                    ],
                },
                "/api_keys/rate_limits/log": {
                    "data": [
                        {
                            "apiKeyId": "k1",
                            "modelId": "zai-org-glm-5-1",
                            "rateLimitType": "RPM",
                            "rateLimitTier": "paid",
                            "timestamp": "2026-06-01T09:00:00.000Z",
                        }
                    ],
                    "object": "list",
                },
                "/models/traits": {
                    "data": {"default": "zai-org-glm-5-1", "fastest": "kimi-k2-6"},
                    "object": "list",
                    "type": "text",
                },
                "/models/compatibility_mapping": {
                    "data": {"gpt-4o": "zai-org-glm-5-1"},
                    "object": "list",
                    "type": "text",
                },
            }
        ),
    )

    report = fetch_venice_quota(api_key="vn-ext", include_extended="full")

    assert len(report.usage_entries) == 1
    assert report.usage_total_count == 42
    assert report.analytics_lookback == "7d"
    assert report.analytics_period_diem == 1.5
    assert report.analytics_top_models
    assert len(report.rate_limit_logs) == 1
    assert report.model_traits[0].startswith("default")
    assert "gpt-4o" in report.compatibility_mappings[0]
    lines = render_venice_quota_lines(report, include_extended="full")
    assert any("Usage (7d)" in line for line in lines)
    assert any("Recent charges" in line for line in lines)


def test_fetch_venice_extended_records_http_errors(monkeypatch):
    monkeypatch.setattr(
        "agent.venice_usage.resolve_runtime_provider",
        lambda requested, explicit_base_url=None, explicit_api_key=None: {
            "base_url": "https://api.venice.ai/api/v1",
            "api_key": "vn-ext",
        },
    )
    monkeypatch.setattr(
        "agent.venice_usage.httpx.Client",
        lambda timeout=12.0: _RoutingClient(
            {
                "/billing/balance": None,
                "/api_keys/rate_limits": {
                    "data": {"balances": {"DIEM": 1.0}},
                },
                "/billing/usage": None,
                "/billing/usage-analytics": None,
                "/api_keys/rate_limits/log": {
                    "data": [],
                    "object": "list",
                },
                "/models/traits": {"data": {}, "object": "list", "type": "text"},
                "/models/compatibility_mapping": {
                    "data": {},
                    "object": "list",
                    "type": "text",
                },
            }
        ),
    )

    report = fetch_venice_quota(api_key="vn-ext", include_extended="account")

    assert report.diem_remaining == 1.0
    assert not report.model_traits
    assert not report.rate_limit_logs
    assert any("billing/usage" in err for err in report.extended_errors)
    assert any("usage-analytics" in err for err in report.extended_errors)


def test_filter_models_by_venice_trait_suffix():
    models = ["zai-org-glm-5-1", "zai-org-glm-5-1:web", "other-model"]
    matched = filter_models_by_venice_trait(models, "zai-org-glm-5-1")
    assert matched == ["zai-org-glm-5-1", "zai-org-glm-5-1:web"]


def test_resolve_venice_openai_model_case_insensitive():
    mapping = {"gpt-4o": "zai-org-glm-5-1", "GPT-4.1": "other-id"}
    assert resolve_venice_openai_model("gpt-4o", mapping) == "zai-org-glm-5-1"
    assert resolve_venice_openai_model("GPT-4.1", mapping) == "other-id"
    assert resolve_venice_openai_model("unknown", mapping) is None
