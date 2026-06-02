"""Venice.ai quota, billing usage, analytics, and model metadata APIs.

Core balance (status bar + fast path):
  - ``GET /billing/balance`` (epoch cap; often requires admin API key)
  - ``GET /api_keys/rate_limits`` (DIEM/USD + ``nextEpochBegins``)

Extended detail (``include_extended=True`` for ``/vquota`` and ``/usage``):
  fetches in parallel via ``ThreadPoolExecutor``:
  - ``GET /billing/usage`` — recent charges (7d window)
  - ``GET /billing/usage-analytics`` — 7d aggregates + top models (beta)
  - ``GET /api_keys/rate_limits/log`` — last rate-limit hits
  - ``GET /models/traits`` and ``GET /models/compatibility_mapping`` (text)

Partial HTTP failures are recorded on ``VeniceQuotaReport.extended_errors``.
Status bar uses ``include_extended=False`` and a 90s TTL cache (``VN …`` label).

Model picker (``hermes model`` for Venice): ``fetch_venice_model_traits``,
``fetch_venice_compatibility_mapping``, ``filter_models_by_venice_trait``,
``resolve_venice_openai_model`` — wired via ``hermes_cli/venice_model_picker.py``.
"""

from __future__ import annotations

import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Literal, Optional, Union

VeniceExtendedScope = Literal["none", "account", "full"]

import httpx

from hermes_cli.runtime_provider import resolve_runtime_provider
from utils import base_url_host_matches

VENICE_429_HINT = (
    " Venice rate limit — /vquota voor DIEM/USD, rate-limit logs en epoch-reset, "
    "of top-up op venice.ai."
)

_STATUS_BAR_CACHE: dict[str, tuple["VeniceQuotaReport", float]] = {}
_STATUS_BAR_CACHE_TTL_SECONDS = 90.0
_STATUS_BAR_CACHE_MAX_ENTRIES = 32
_FETCH_TIMEOUT_SECONDS = 12.0
_QUICK_TIMEOUT_SECONDS = 3.0
_EXTENDED_FETCH_TIMEOUT_SECONDS = 10.0
_EXTENDED_MAX_WORKERS = 5

_STATUS_BAR_LOCK = threading.Lock()
_STATUS_BAR_INFLIGHT: set[str] = set()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _http_status_from_error(error: Exception) -> Optional[int]:
    status = getattr(error, "status_code", None)
    if status is not None:
        try:
            return int(status)
        except (TypeError, ValueError):
            pass
    if type(error).__name__ == "RateLimitError":
        return 429
    return None


def _parse_dt(value: Any) -> Optional[datetime]:
    if value in {None, ""}:
        return None
    if isinstance(value, dict):
        return None
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        except (OSError, OverflowError, ValueError):
            return None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        if text.isdigit():
            try:
                return datetime.fromtimestamp(float(text), tz=timezone.utc)
            except (OSError, OverflowError, ValueError):
                return None
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(text)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


def _clamp_int(value: Any, default: int, *, lo: int, hi: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(lo, min(parsed, hi))


def format_venice_local_timestamp(dt: Optional[datetime]) -> str:
    if not dt:
        return "?"
    return dt.astimezone().strftime("%Y-%m-%d %H:%M")


def coerce_venice_extended_scope(value: Union[bool, str, VeniceExtendedScope, None]) -> VeniceExtendedScope:
    """Map legacy ``include_extended`` booleans to a fetch/render scope."""
    if value in (False, None, "", 0, "none", "false", "False"):
        return "none"
    if value is True or value in {"full", "true", "True"}:
        return "full"
    if value == "account":
        return "account"
    return "none"


def format_venice_epoch_bar_line(
    report: VeniceQuotaReport,
    *,
    rich: bool = False,
) -> Optional[str]:
    """ASCII epoch progress bar (CLI ``/vquota`` only)."""
    if not (report.diem_epoch_allocation and report.diem_remaining is not None):
        return None
    pct = max(0.0, min(1.0, report.diem_used_fraction))
    width = 20
    filled = int(round(pct * width))
    bar = "▓" * filled + "░" * (width - filled)
    label = f"{'DIEM epoch':40s}  {bar}  {int(pct * 100):3d}%"
    return label if not rich else label


def format_venice_reset(dt: Optional[datetime]) -> str:
    if not dt:
        return "unknown"
    local_dt = dt.astimezone()
    delta = dt - _utc_now()
    total_seconds = int(delta.total_seconds())
    if total_seconds <= 0:
        return f"now ({local_dt.strftime('%Y-%m-%d %H:%M %Z')})"
    hours, rem = divmod(total_seconds, 3600)
    minutes = rem // 60
    if hours >= 24:
        days, hours = divmod(hours, 24)
        rel = f"in {days}d {hours}h"
    elif hours > 0:
        rel = f"in {hours}h {minutes}m"
    else:
        rel = f"in {minutes}m"
    return f"{rel} ({local_dt.strftime('%Y-%m-%d %H:%M %Z')})"


def is_venice_runtime(provider: Optional[str], base_url: Optional[str] = None) -> bool:
    normalized = str(provider or "").strip().lower()
    if normalized in {"venice", "custom:venice"}:
        return True
    if normalized.startswith("custom:"):
        slug = normalized.split(":", 1)[1].strip()
        if slug == "venice":
            return True
    if base_url and base_url_host_matches(str(base_url), "venice.ai"):
        return True
    return False


def is_venice_rate_limit_http_error(
    error: Exception,
    *,
    provider: Optional[str] = None,
    base_url: Optional[str] = None,
) -> bool:
    if _http_status_from_error(error) != 429:
        return False
    if provider or base_url:
        return is_venice_runtime(provider, base_url)
    blob = f"{error} {getattr(error, 'body', '')}".lower()
    return "venice" in blob


def append_venice_429_hint_if_needed(
    summary: str,
    error: Exception,
    *,
    provider: Optional[str] = None,
    base_url: Optional[str] = None,
) -> str:
    if "/vquota" in summary:
        return summary
    if not is_venice_rate_limit_http_error(error, provider=provider, base_url=base_url):
        return summary
    return f"{summary.rstrip()}{VENICE_429_HINT}"


def _resolve_venice_api_root(base_url: str) -> str:
    normalized = str(base_url or "").strip().rstrip("/")
    if not normalized:
        return "https://api.venice.ai/api/v1"
    if base_url_host_matches(normalized, "venice.ai"):
        if normalized.endswith("/api/v1"):
            return normalized
        if normalized.endswith("/v1"):
            return normalized[: -len("/v1")] + "/api/v1"
        return normalized + "/api/v1"
    return normalized


@dataclass(frozen=True)
class VeniceBillingUsageEntry:
    timestamp: Optional[datetime]
    sku: str
    amount: float
    currency: str
    units: float
    notes: str = ""
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None


@dataclass(frozen=True)
class VeniceRateLimitLog:
    model_id: str
    rate_limit_type: str
    rate_limit_tier: str
    timestamp: Optional[datetime]


@dataclass(frozen=True)
class VeniceQuotaReport:
    diem_remaining: Optional[float] = None
    diem_epoch_allocation: Optional[float] = None
    usd_balance: Optional[float] = None
    can_consume: Optional[bool] = None
    consumption_currency: Optional[str] = None
    access_permitted: Optional[bool] = None
    next_epoch_begins: Optional[datetime] = None
    billing_available: bool = False
    fetched_at: datetime = field(default_factory=_utc_now)
    # Extended (billing/usage, usage-analytics, rate_limits/log, models/*)
    usage_entries: tuple[VeniceBillingUsageEntry, ...] = ()
    usage_total_count: Optional[int] = None
    usage_warning: Optional[str] = None
    analytics_lookback: Optional[str] = None
    analytics_period_diem: Optional[float] = None
    analytics_period_usd: Optional[float] = None
    analytics_top_models: tuple[str, ...] = ()
    rate_limit_logs: tuple[VeniceRateLimitLog, ...] = ()
    model_traits: tuple[str, ...] = ()
    compatibility_mappings: tuple[str, ...] = ()
    extended_errors: tuple[str, ...] = ()

    @property
    def diem_used(self) -> Optional[float]:
        if (
            self.diem_remaining is None
            or self.diem_epoch_allocation is None
            or self.diem_epoch_allocation <= 0
        ):
            return None
        return max(0.0, float(self.diem_epoch_allocation) - float(self.diem_remaining))

    @property
    def diem_used_fraction(self) -> float:
        if self.diem_epoch_allocation and self.diem_epoch_allocation > 0 and self.diem_remaining is not None:
            used = self.diem_used or 0.0
            return max(0.0, min(1.0, used / float(self.diem_epoch_allocation)))
        return 0.0


class VeniceQuotaError(Exception):
    pass


def format_venice_status_bar_quota(report: VeniceQuotaReport) -> str:
    if report.diem_epoch_allocation and report.diem_epoch_allocation > 0 and report.diem_remaining is not None:
        rem = report.diem_remaining
        alloc = report.diem_epoch_allocation
        if float(rem).is_integer() and float(alloc).is_integer():
            return f"VN {int(rem)}/{int(alloc)}"
        return f"VN {rem:.1f}/{alloc:.1f}"
    if report.diem_remaining is not None:
        val = report.diem_remaining
        if float(val).is_integer():
            return f"VN {int(val)} DIEM"
        return f"VN {val:.1f} DIEM"
    if report.usd_balance is not None:
        return f"VN ${report.usd_balance:.2f}"
    return "VN —"


def venice_status_bar_used_percent(report: VeniceQuotaReport) -> int:
    if report.diem_epoch_allocation and report.diem_epoch_allocation > 0:
        return max(0, min(100, round(report.diem_used_fraction * 100)))
    return 0


def _prune_status_bar_cache(now: float) -> None:
    stale_before = now - (_STATUS_BAR_CACHE_TTL_SECONDS * 2)
    for key, (_, ts) in list(_STATUS_BAR_CACHE.items()):
        if ts < stale_before:
            del _STATUS_BAR_CACHE[key]
    overflow = len(_STATUS_BAR_CACHE) - _STATUS_BAR_CACHE_MAX_ENTRIES
    if overflow <= 0:
        return
    for key, _ in sorted(_STATUS_BAR_CACHE.items(), key=lambda item: item[1][1])[:overflow]:
        del _STATUS_BAR_CACHE[key]


def resolve_status_bar_venice_quota(
    *,
    provider: Optional[str],
    base_url: Optional[str],
    api_key: Optional[str],
    cache_bucket: str = "default",
) -> Optional[tuple[str, int]]:
    if not is_venice_runtime(provider, base_url):
        return None
    now = time.monotonic()
    cache_key = f"{cache_bucket}:{provider}:{base_url}"
    cached = _STATUS_BAR_CACHE.get(cache_key)
    if cached and (now - cached[1]) < _STATUS_BAR_CACHE_TTL_SECONDS:
        report = cached[0]
        return format_venice_status_bar_quota(report), venice_status_bar_used_percent(report)

    with _STATUS_BAR_LOCK:
        if cache_key in _STATUS_BAR_INFLIGHT:
            if cached:
                report = cached[0]
                return format_venice_status_bar_quota(report), venice_status_bar_used_percent(report)
            return "VN …", 0
        _STATUS_BAR_INFLIGHT.add(cache_key)

    try:
        report = fetch_venice_quota(
            base_url=base_url,
            api_key=api_key,
            requested_provider=provider or "venice",
            timeout=_QUICK_TIMEOUT_SECONDS,
        )
        with _STATUS_BAR_LOCK:
            _STATUS_BAR_CACHE[cache_key] = (report, now)
            _prune_status_bar_cache(now)
        return format_venice_status_bar_quota(report), venice_status_bar_used_percent(report)
    except Exception:
        if cached:
            report = cached[0]
            return format_venice_status_bar_quota(report), venice_status_bar_used_percent(report)
        return "VN —", 0
    finally:
        with _STATUS_BAR_LOCK:
            _STATUS_BAR_INFLIGHT.discard(cache_key)


def _fetch_json_response(
    client: httpx.Client,
    url: str,
    headers: dict[str, str],
    *,
    params: Optional[dict[str, Any]] = None,
) -> tuple[Optional[dict[str, Any]], Optional[int]]:
    try:
        response = client.get(url, headers=headers, params=params)
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        return None, exc.response.status_code
    except httpx.RequestError:
        return None, None
    try:
        payload = response.json()
    except ValueError:
        return None, None
    if not isinstance(payload, dict):
        return None, None
    return payload, response.status_code


def _fetch_json(
    client: httpx.Client,
    url: str,
    headers: dict[str, str],
    *,
    params: Optional[dict[str, Any]] = None,
) -> Optional[dict[str, Any]]:
    payload, _status = _fetch_json_response(client, url, headers, params=params)
    return payload


def _resolve_venice_auth(
    *,
    base_url: Optional[str],
    api_key: Optional[str],
    requested_provider: str,
) -> tuple[str, dict[str, str]]:
    requested = (
        "custom:venice"
        if str(requested_provider or "").strip().lower().startswith("custom:")
        else "venice"
    )
    runtime = resolve_runtime_provider(
        requested=requested,
        explicit_base_url=base_url,
        explicit_api_key=api_key,
    )
    token = str(runtime.get("api_key", "") or "").strip()
    if not token or token == "no-key-required":
        token = str(os.getenv("VENICE_API_KEY", "") or "").strip()
    if not token:
        raise VeniceQuotaError(
            "Set VENICE_API_KEY — sync via SYNC_HERMES_API_ENV.bat or venice.ai"
        )
    api_root = _resolve_venice_api_root(
        str(runtime.get("base_url", "") or base_url or "https://api.venice.ai/api/v1")
    )
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "User-Agent": "hermes-cli",
    }
    return api_root, headers


def _parse_billing_usage_entry(raw: Any) -> Optional[VeniceBillingUsageEntry]:
    if not isinstance(raw, dict):
        return None
    sku = str(raw.get("sku") or "").strip() or "unknown"
    currency = str(raw.get("currency") or "").strip() or "?"
    amount = float(raw["amount"]) if isinstance(raw.get("amount"), (int, float)) else 0.0
    units_raw = raw.get("units")
    if units_raw is None:
        units_raw = raw.get("unit")
    units = float(units_raw) if isinstance(units_raw, (int, float)) else 0.0
    notes = str(raw.get("notes") or "").strip()
    inference = raw.get("inferenceDetails")
    prompt_tokens = None
    completion_tokens = None
    if isinstance(inference, dict):
        if isinstance(inference.get("promptTokens"), (int, float)):
            prompt_tokens = int(inference["promptTokens"])
        if isinstance(inference.get("completionTokens"), (int, float)):
            completion_tokens = int(inference["completionTokens"])
    return VeniceBillingUsageEntry(
        timestamp=_parse_dt(raw.get("timestamp")),
        sku=sku,
        amount=amount,
        currency=currency,
        units=units,
        notes=notes,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
    )


def _fetch_billing_usage(
    client: httpx.Client,
    api_root: str,
    headers: dict[str, str],
    *,
    limit: int = 5,
) -> tuple[tuple[VeniceBillingUsageEntry, ...], Optional[int], Optional[str], Optional[str]]:
    start = (_utc_now() - timedelta(days=7)).strftime("%Y-%m-%dT00:00:00.000Z")
    payload, status = _fetch_json_response(
        client,
        f"{api_root}/billing/usage",
        headers,
        params={
            "limit": _clamp_int(limit, 5, lo=1, hi=50),
            "page": 1,
            "sortOrder": "desc",
            "startDate": start,
        },
    )
    if not payload:
        err = f"billing/usage unavailable (HTTP {status})" if status else "billing/usage unreachable"
        return (), None, None, err
    warning = str(payload.get("warningMessage") or "").strip() or None
    rows = payload.get("data")
    entries: list[VeniceBillingUsageEntry] = []
    if isinstance(rows, list):
        for row in rows[:limit]:
            entry = _parse_billing_usage_entry(row)
            if entry:
                entries.append(entry)
    total: Optional[int] = None
    pagination = payload.get("pagination")
    if isinstance(pagination, dict) and isinstance(pagination.get("total"), (int, float)):
        total = int(pagination["total"])
    return tuple(entries), total, warning, None


def _fetch_usage_analytics(
    client: httpx.Client,
    api_root: str,
    headers: dict[str, str],
    *,
    lookback: str = "7d",
    top_models: int = 3,
) -> tuple[Optional[str], Optional[float], Optional[float], tuple[str, ...], Optional[str]]:
    payload, status = _fetch_json_response(
        client,
        f"{api_root}/billing/usage-analytics",
        headers,
        params={"lookback": lookback},
    )
    if not payload:
        err = (
            f"billing/usage-analytics unavailable (HTTP {status})"
            if status
            else "billing/usage-analytics unreachable"
        )
        return None, None, None, (), err
    resolved_lookback = str(payload.get("lookback") or lookback).strip() or lookback
    period_diem = 0.0
    period_usd = 0.0
    by_date = payload.get("byDate")
    if isinstance(by_date, list):
        for row in by_date:
            if not isinstance(row, dict):
                continue
            if isinstance(row.get("DIEM"), (int, float)):
                period_diem += float(row["DIEM"])
            if isinstance(row.get("USD"), (int, float)):
                period_usd += float(row["USD"])
    top_lines: list[str] = []
    by_model = payload.get("byModel")
    if isinstance(by_model, list):
        for row in by_model[: _clamp_int(top_models, 3, lo=1, hi=10)]:
            if not isinstance(row, dict):
                continue
            name = str(row.get("modelName") or row.get("modelType") or "model").strip()
            diem = float(row["totalDiem"]) if isinstance(row.get("totalDiem"), (int, float)) else 0.0
            usd = float(row["totalUsd"]) if isinstance(row.get("totalUsd"), (int, float)) else 0.0
            units = row.get("totalUnits")
            unit_type = str(row.get("unitType") or "").strip()
            parts = []
            if diem > 0:
                parts.append(f"{diem:.4f} DIEM")
            if usd > 0:
                parts.append(f"${usd:.4f}")
            if isinstance(units, (int, float)) and units > 0 and unit_type:
                parts.append(f"{float(units):g} {unit_type}")
            detail = ", ".join(parts) if parts else "—"
            top_lines.append(f"{name}: {detail}")
    return resolved_lookback, period_diem, period_usd, tuple(top_lines), None


def _fetch_rate_limit_logs(
    client: httpx.Client,
    api_root: str,
    headers: dict[str, str],
    *,
    max_items: int = 5,
) -> tuple[tuple[VeniceRateLimitLog, ...], Optional[str]]:
    payload, status = _fetch_json_response(
        client, f"{api_root}/api_keys/rate_limits/log", headers
    )
    if not payload:
        err = (
            f"api_keys/rate_limits/log unavailable (HTTP {status})"
            if status
            else "api_keys/rate_limits/log unreachable"
        )
        return (), err
    rows = payload.get("data")
    if not isinstance(rows, list):
        return (), "api_keys/rate_limits/log returned unexpected payload"
    logs: list[VeniceRateLimitLog] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        logs.append(
            VeniceRateLimitLog(
                model_id=str(row.get("modelId") or "").strip() or "?",
                rate_limit_type=str(row.get("rateLimitType") or "").strip() or "?",
                rate_limit_tier=str(row.get("rateLimitTier") or "").strip() or "?",
                timestamp=_parse_dt(row.get("timestamp")),
            )
        )
    logs.sort(key=lambda item: item.timestamp or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return tuple(logs[: _clamp_int(max_items, 5, lo=1, hi=50)]), None


def _parse_string_map_payload(payload: Optional[dict[str, Any]], data_key: str = "data") -> dict[str, str]:
    if not payload:
        return {}
    data = payload.get(data_key)
    if not isinstance(data, dict):
        return {}
    result: dict[str, str] = {}
    for key, value in data.items():
        name = str(key or "").strip()
        model_id = str(value or "").strip()
        if name and model_id:
            result[name] = model_id
    return result


def fetch_venice_model_traits(
    *,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    model_type: str = "text",
    timeout: float = 8.0,
) -> tuple[dict[str, str], Optional[str]]:
    """Load ``GET /models/traits`` as ``{trait: model_id}`` (e.g. ``default``, ``fastest``)."""
    try:
        api_root, headers = _resolve_venice_auth(
            base_url=base_url,
            api_key=api_key,
            requested_provider="venice",
        )
    except VeniceQuotaError as exc:
        return {}, str(exc)
    with httpx.Client(timeout=timeout) as client:
        payload, status = _fetch_json_response(
            client,
            f"{api_root}/models/traits",
            headers,
            params={"type": model_type},
        )
    if not payload:
        err = f"models/traits unavailable (HTTP {status})" if status else "models/traits unreachable"
        return {}, err
    traits = _parse_string_map_payload(payload)
    if not traits:
        return {}, "models/traits returned no entries"
    return traits, None


def fetch_venice_compatibility_mapping(
    *,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    model_type: str = "text",
    timeout: float = 8.0,
) -> tuple[dict[str, str], Optional[str]]:
    """Load ``GET /models/compatibility_mapping`` as ``{openai_name: venice_model_id}``."""
    try:
        api_root, headers = _resolve_venice_auth(
            base_url=base_url,
            api_key=api_key,
            requested_provider="venice",
        )
    except VeniceQuotaError as exc:
        return {}, str(exc)
    with httpx.Client(timeout=timeout) as client:
        payload, status = _fetch_json_response(
            client,
            f"{api_root}/models/compatibility_mapping",
            headers,
            params={"type": model_type},
        )
    if not payload:
        err = (
            f"models/compatibility_mapping unavailable (HTTP {status})"
            if status
            else "models/compatibility_mapping unreachable"
        )
        return {}, err
    mapping = _parse_string_map_payload(payload)
    if not mapping:
        return {}, "models/compatibility_mapping returned no entries"
    return mapping, None


def filter_models_by_venice_trait(
    models: list[str],
    trait_model_id: str,
) -> list[str]:
    """Keep live ``/models`` IDs that match a trait's Venice model id (incl. ``:suffix``)."""
    needle = str(trait_model_id or "").strip()
    if not needle:
        return list(models)
    matched = [
        model_id
        for model_id in models
        if model_id == needle or model_id.startswith(f"{needle}:")
    ]
    if matched:
        return matched
    return [needle]


def resolve_venice_openai_model(
    openai_name: str,
    mapping: dict[str, str],
) -> Optional[str]:
    """Map an OpenAI-style model name to a Venice model id via compatibility_mapping."""
    query = str(openai_name or "").strip()
    if not query or not mapping:
        return None
    if query in mapping:
        return mapping[query]
    lowered = query.lower()
    for key, value in mapping.items():
        if key.lower() == lowered:
            return value
    return None


def _fetch_model_trait_lines(
    client: httpx.Client,
    api_root: str,
    headers: dict[str, str],
    *,
    model_type: str = "text",
    max_items: int = 6,
) -> tuple[tuple[str, ...], Optional[str]]:
    payload, status = _fetch_json_response(
        client,
        f"{api_root}/models/traits",
        headers,
        params={"type": model_type},
    )
    if not payload:
        err = f"models/traits unavailable (HTTP {status})" if status else "models/traits unreachable"
        return (), err
    traits = _parse_string_map_payload(payload)
    if not traits:
        return (), "models/traits returned unexpected payload"
    lines = [
        f"{trait} → {model_id}"
        for trait, model_id in list(traits.items())[: _clamp_int(max_items, 6, lo=1, hi=20)]
    ]
    return tuple(lines), None


def _fetch_compatibility_mapping_lines(
    client: httpx.Client,
    api_root: str,
    headers: dict[str, str],
    *,
    model_type: str = "text",
    max_items: int = 6,
) -> tuple[tuple[str, ...], Optional[str]]:
    payload, status = _fetch_json_response(
        client,
        f"{api_root}/models/compatibility_mapping",
        headers,
        params={"type": model_type},
    )
    if not payload:
        err = (
            f"models/compatibility_mapping unavailable (HTTP {status})"
            if status
            else "models/compatibility_mapping unreachable"
        )
        return (), err
    mapping = _parse_string_map_payload(payload)
    if not mapping:
        return (), "models/compatibility_mapping returned unexpected payload"
    lines = [
        f"{openai_name} → {venice_id}"
        for openai_name, venice_id in list(mapping.items())[: _clamp_int(max_items, 6, lo=1, hi=20)]
    ]
    return tuple(lines), None


@dataclass(frozen=True)
class _VeniceExtendedData:
    usage_entries: tuple[VeniceBillingUsageEntry, ...] = ()
    usage_total_count: Optional[int] = None
    usage_warning: Optional[str] = None
    analytics_lookback: Optional[str] = None
    analytics_period_diem: Optional[float] = None
    analytics_period_usd: Optional[float] = None
    analytics_top_models: tuple[str, ...] = ()
    rate_limit_logs: tuple[VeniceRateLimitLog, ...] = ()
    model_traits: tuple[str, ...] = ()
    compatibility_mappings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()


def _run_with_client(
    timeout: float,
    fn: Callable[..., Any],
    *args: Any,
    **kwargs: Any,
) -> Any:
    with httpx.Client(timeout=timeout) as client:
        return fn(client, *args, **kwargs)


def _fetch_venice_extended_parallel(
    api_root: str,
    headers: dict[str, str],
    *,
    timeout: float = _EXTENDED_FETCH_TIMEOUT_SECONDS,
    scope: VeniceExtendedScope = "full",
) -> _VeniceExtendedData:
    """Fetch optional Venice endpoints in parallel (separate clients per thread).

    ``account`` scope (for ``/usage``): billing/usage + usage-analytics only.
    ``full`` scope (for ``/vquota``): all extended endpoints including traits.
    """
    tasks: dict[str, Callable[[], Any]] = {
        "usage": lambda: _run_with_client(
            timeout, _fetch_billing_usage, api_root, headers
        ),
        "analytics": lambda: _run_with_client(
            timeout, _fetch_usage_analytics, api_root, headers
        ),
    }
    if scope == "full":
        tasks.update(
            {
                "rate_logs": lambda: _run_with_client(
                    timeout, _fetch_rate_limit_logs, api_root, headers
                ),
                "traits": lambda: _run_with_client(
                    timeout, _fetch_model_trait_lines, api_root, headers
                ),
                "compat": lambda: _run_with_client(
                    timeout, _fetch_compatibility_mapping_lines, api_root, headers
                ),
            }
        )
    errors: list[str] = []
    usage_entries: tuple[VeniceBillingUsageEntry, ...] = ()
    usage_total_count: Optional[int] = None
    usage_warning: Optional[str] = None
    analytics_lookback: Optional[str] = None
    analytics_period_diem: Optional[float] = None
    analytics_period_usd: Optional[float] = None
    analytics_top_models: tuple[str, ...] = ()
    rate_limit_logs: tuple[VeniceRateLimitLog, ...] = ()
    model_traits: tuple[str, ...] = ()
    compatibility_mappings: tuple[str, ...] = ()

    with ThreadPoolExecutor(max_workers=_EXTENDED_MAX_WORKERS) as pool:
        future_map = {pool.submit(worker): name for name, worker in tasks.items()}
        for future in as_completed(future_map):
            name = future_map[future]
            try:
                result = future.result()
            except Exception as exc:
                errors.append(f"{name}: {exc}")
                continue
            if name == "usage":
                usage_entries, usage_total_count, usage_warning, err = result
                if err:
                    errors.append(err)
            elif name == "analytics":
                (
                    analytics_lookback,
                    analytics_period_diem,
                    analytics_period_usd,
                    analytics_top_models,
                    err,
                ) = result
                if err:
                    errors.append(err)
            elif name == "rate_logs":
                rate_limit_logs, err = result
                if err:
                    errors.append(err)
            elif name == "traits":
                model_traits, err = result
                if err:
                    errors.append(err)
            elif name == "compat":
                compatibility_mappings, err = result
                if err:
                    errors.append(err)

    return _VeniceExtendedData(
        usage_entries=usage_entries,
        usage_total_count=usage_total_count,
        usage_warning=usage_warning,
        analytics_lookback=analytics_lookback,
        analytics_period_diem=analytics_period_diem,
        analytics_period_usd=analytics_period_usd,
        analytics_top_models=analytics_top_models,
        rate_limit_logs=rate_limit_logs,
        model_traits=model_traits,
        compatibility_mappings=compatibility_mappings,
        errors=tuple(errors),
    )


def fetch_venice_quota(
    *,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    requested_provider: str = "venice",
    timeout: float = _FETCH_TIMEOUT_SECONDS,
    include_extended: Union[bool, VeniceExtendedScope] = False,
) -> VeniceQuotaReport:
    """Load Venice balances.

    ``include_extended`` may be ``False``, ``True``/``"full"``, or ``"account"``.
    ``account`` loads billing/usage + usage-analytics only (faster, for ``/usage``).
    ``full`` adds rate-limit logs and model metadata (for ``/vquota``).
    """
    extended_scope = coerce_venice_extended_scope(include_extended)
    api_root, headers = _resolve_venice_auth(
        base_url=base_url,
        api_key=api_key,
        requested_provider=requested_provider,
    )

    billing_available = False
    diem_remaining: Optional[float] = None
    diem_epoch_allocation: Optional[float] = None
    usd_balance: Optional[float] = None
    can_consume: Optional[bool] = None
    consumption_currency: Optional[str] = None
    access_permitted: Optional[bool] = None
    next_epoch_begins: Optional[datetime] = None

    with httpx.Client(timeout=timeout) as client:
        billing = _fetch_json(client, f"{api_root}/billing/balance", headers)
        if billing:
            billing_available = True
            balances = billing.get("balances") if isinstance(billing.get("balances"), dict) else {}
            if isinstance(balances.get("diem"), (int, float)):
                diem_remaining = float(balances["diem"])
            if isinstance(balances.get("usd"), (int, float)):
                usd_balance = float(balances["usd"])
            if isinstance(billing.get("diemEpochAllocation"), (int, float)):
                diem_epoch_allocation = float(billing["diemEpochAllocation"])
            if isinstance(billing.get("canConsume"), bool):
                can_consume = billing["canConsume"]
            currency = billing.get("consumptionCurrency")
            if currency:
                consumption_currency = str(currency)

        rate_payload = _fetch_json(client, f"{api_root}/api_keys/rate_limits", headers)
        if not rate_payload and not billing_available:
            raise VeniceQuotaError("Venice quota APIs unreachable (billing + rate_limits)")

        data = (rate_payload or {}).get("data") if isinstance(rate_payload, dict) else None
        if isinstance(data, dict):
            if isinstance(data.get("accessPermitted"), bool):
                access_permitted = data["accessPermitted"]
            next_epoch_begins = _parse_dt(data.get("nextEpochBegins")) or next_epoch_begins
            rl_balances = data.get("balances")
            if isinstance(rl_balances, dict):
                if isinstance(rl_balances.get("DIEM"), (int, float)):
                    diem_remaining = float(rl_balances["DIEM"])
                if isinstance(rl_balances.get("USD"), (int, float)):
                    usd_balance = float(rl_balances["USD"])

    usage_entries: tuple[VeniceBillingUsageEntry, ...] = ()
    usage_total_count: Optional[int] = None
    usage_warning: Optional[str] = None
    analytics_lookback: Optional[str] = None
    analytics_period_diem: Optional[float] = None
    analytics_period_usd: Optional[float] = None
    analytics_top_models: tuple[str, ...] = ()
    rate_limit_logs: tuple[VeniceRateLimitLog, ...] = ()
    model_traits: tuple[str, ...] = ()
    compatibility_mappings: tuple[str, ...] = ()
    extended_errors: tuple[str, ...] = ()
    if extended_scope != "none":
        extended_timeout = max(timeout, _EXTENDED_FETCH_TIMEOUT_SECONDS)
        extended = _fetch_venice_extended_parallel(
            api_root, headers, timeout=extended_timeout, scope=extended_scope
        )
        usage_entries = extended.usage_entries
        usage_total_count = extended.usage_total_count
        usage_warning = extended.usage_warning
        analytics_lookback = extended.analytics_lookback
        analytics_period_diem = extended.analytics_period_diem
        analytics_period_usd = extended.analytics_period_usd
        analytics_top_models = extended.analytics_top_models
        rate_limit_logs = extended.rate_limit_logs
        model_traits = extended.model_traits
        compatibility_mappings = extended.compatibility_mappings
        extended_errors = extended.errors

    if (
        diem_remaining is None
        and diem_epoch_allocation is None
        and usd_balance is None
        and not billing_available
    ):
        raise VeniceQuotaError(
            "Venice returned no balance data. /billing/balance may require an admin API key; "
            "check /api_keys/rate_limits at docs.venice.ai"
        )

    return VeniceQuotaReport(
        diem_remaining=diem_remaining,
        diem_epoch_allocation=diem_epoch_allocation,
        usd_balance=usd_balance,
        can_consume=can_consume,
        consumption_currency=consumption_currency,
        access_permitted=access_permitted,
        next_epoch_begins=next_epoch_begins,
        billing_available=billing_available,
        fetched_at=_utc_now(),
        usage_entries=usage_entries if extended_scope != "none" else (),
        usage_total_count=usage_total_count if extended_scope != "none" else None,
        usage_warning=usage_warning if extended_scope != "none" else None,
        analytics_lookback=analytics_lookback if extended_scope != "none" else None,
        analytics_period_diem=analytics_period_diem if extended_scope != "none" else None,
        analytics_period_usd=analytics_period_usd if extended_scope != "none" else None,
        analytics_top_models=analytics_top_models if extended_scope != "none" else (),
        rate_limit_logs=rate_limit_logs if extended_scope == "full" else (),
        model_traits=model_traits if extended_scope == "full" else (),
        compatibility_mappings=compatibility_mappings if extended_scope == "full" else (),
        extended_errors=extended_errors if extended_scope != "none" else (),
    )


def _render_style_dim(text: str, *, style: Literal["plain", "rich"]) -> str:
    if style == "rich":
        return f"[dim]{text}[/]"
    return text


def render_venice_quota_lines(
    report: VeniceQuotaReport,
    *,
    markdown: bool = False,
    include_rate_limits_note: bool = True,
    include_extended: Union[bool, VeniceExtendedScope] = False,
    include_epoch_bar: bool = False,
    style: Literal["plain", "rich"] = "plain",
    include_footer_docs: bool = False,
) -> list[str]:
    """Render Venice quota for CLI, ``/usage``, or markdown.

    Use ``include_extended="account"`` for fast account limits; ``"full"`` for ``/vquota``.
    ``include_epoch_bar`` + ``style=\"rich\"`` adds the ASCII bar (CLI only).
    """
    extended_scope = coerce_venice_extended_scope(include_extended)
    bold = "**" if markdown else ""
    if style == "rich":
        lines: list[str] = ["[bold]Venice quota[/]  (venice.ai · DIEM)"]
    else:
        lines = [
            f"📊 {bold}Venice quota (DIEM){bold}" if markdown else "📊 Venice quota (DIEM)"
        ]

    if report.diem_epoch_allocation and report.diem_remaining is not None:
        used = report.diem_used or 0.0
        if include_epoch_bar:
            bar_line = format_venice_epoch_bar_line(report, rich=(style == "rich"))
            if bar_line:
                lines.append(f"    {bar_line}" if style == "rich" else bar_line)
            lines.append(
                f"    {used:.2f} / {report.diem_epoch_allocation:.2f} used "
                f"({report.diem_remaining:.2f} remaining)"
                if style == "rich"
                else (
                    f"{used:.2f} / {report.diem_epoch_allocation:.2f} used "
                    f"({report.diem_remaining:.2f} remaining)"
                )
            )
        else:
            lines.append(
                f"DIEM epoch: {used:.2f} / {report.diem_epoch_allocation:.2f} used "
                f"({report.diem_remaining:.2f} remaining)"
            )
    elif report.diem_remaining is not None:
        lines.append(f"DIEM balance: {report.diem_remaining:.4f}")
        if not report.billing_available:
            if style == "rich":
                lines.append(
                    _render_style_dim(
                        "Epoch cap: /billing/balance needs admin API key "
                        "(rate_limits shows balance only)",
                        style=style,
                    )
                )
            else:
                lines.append(
                    "DIEM epoch cap: unavailable (GET /billing/balance requires admin API key — "
                    "see docs.venice.ai/api-reference/endpoint/billing/balance)"
                )

    if report.usd_balance is not None:
        lines.append(f"USD balance: ${report.usd_balance:.4f}")

    if report.consumption_currency:
        lines.append(f"Consumption currency: {report.consumption_currency}")
    if report.can_consume is not None:
        lines.append(f"Can consume: {'yes' if report.can_consume else 'no'}")
    if report.access_permitted is not None:
        lines.append(f"API access: {'permitted' if report.access_permitted else 'blocked'}")

    if report.next_epoch_begins:
        lines.append(f"Next epoch {_format_venice_reset_line(report.next_epoch_begins)}")

    if extended_scope != "none":
        analytics_suffix = _render_style_dim("(usage-analytics, beta)", style=style)
        if report.analytics_lookback is not None:
            diem = report.analytics_period_diem or 0.0
            usd = report.analytics_period_usd or 0.0
            lines.append(
                f"Usage ({report.analytics_lookback}): {diem:.4f} DIEM, ${usd:.4f} USD {analytics_suffix}"
            )
            for model_line in report.analytics_top_models:
                lines.append(f"  Top model: {model_line}")
        if report.usage_entries:
            lines.append(
                _render_style_dim("Recent charges (billing/usage, 7d)", style=style)
                if style == "rich"
                else "Recent charges (billing/usage, beta, last 7d):"
            )
            for entry in report.usage_entries:
                when = format_venice_local_timestamp(entry.timestamp)
                amount = abs(entry.amount)
                token_bits = []
                if entry.prompt_tokens is not None:
                    token_bits.append(f"in {entry.prompt_tokens}")
                if entry.completion_tokens is not None:
                    token_bits.append(f"out {entry.completion_tokens}")
                token_suffix = f" ({', '.join(token_bits)})" if token_bits else ""
                lines.append(
                    f"  {when} {entry.sku}: {amount:.4f} {entry.currency}{token_suffix}"
                )
            if report.usage_total_count is not None:
                lines.append(f"  … {report.usage_total_count} total rows in period")
        if report.usage_warning:
            lines.append(f"Note: {report.usage_warning}")
        if extended_scope == "full" and report.rate_limit_logs:
            lines.append(
                _render_style_dim("Recent rate-limit hits (api_keys/rate_limits/log)", style=style)
                if style == "rich"
                else "Recent rate-limit hits (last 50 max):"
            )
            for log in report.rate_limit_logs:
                lines.append(
                    f"  {format_venice_local_timestamp(log.timestamp)} "
                    f"{log.model_id} {log.rate_limit_type} ({log.rate_limit_tier})"
                )
        if report.extended_errors:
            for err in report.extended_errors:
                if style == "rich":
                    lines.append(_render_style_dim(err, style=style))
                else:
                    lines.append(f"Extended API: {err}")
        if extended_scope == "full" and report.model_traits:
            lines.append(_render_style_dim("Model traits (text)", style=style) if style == "rich" else "Model traits (text):")
            for trait_line in report.model_traits:
                lines.append(f"  {trait_line}")
        if extended_scope == "full" and report.compatibility_mappings:
            header = (
                _render_style_dim("OpenAI mapping (models/compatibility_mapping)", style=style)
                if style == "rich"
                else "OpenAI name mapping (text):"
            )
            lines.append(header)
            for mapping in report.compatibility_mappings:
                lines.append(f"  {mapping}")
        if extended_scope == "full":
            lines.append(
                "Venice chat options: set providers.venice.extra_body.venice_parameters in config "
                "(web search, character_slug, etc.)"
            )

    if include_rate_limits_note:
        lines.append(
            "Per-model RPM/TPM: GET /api_keys/rate_limits — "
            "https://docs.venice.ai/api-reference/endpoint/api_keys/rate_limits"
        )
    if include_footer_docs and style == "rich":
        lines.append(
            _render_style_dim(
                "Docs: billing/balance · billing/usage · usage-analytics · api_keys/rate_limits/log",
                style=style,
            )
        )
    return lines


def _format_venice_reset_line(dt: datetime) -> str:
    return f"{format_venice_reset(dt)} (epoch)"
