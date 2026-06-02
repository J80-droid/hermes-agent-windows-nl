"""Jatevo account quota via ``GET /v1/usage`` (dashboard-style display)."""

from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from hermes_cli.runtime_provider import resolve_runtime_provider
from utils import base_url_host_matches

JATEVO_429_HINT = (
    " Jatevo dagquota op — /jquota voor 0/N, reset 00:00 UTC, "
    "of verhoog $JTVO op jatevo.ai/dashboard."
)

_STATUS_BAR_CACHE: dict[str, tuple["JatevoQuotaReport", float]] = {}
_STATUS_BAR_CACHE_TTL_SECONDS = 90.0
_STATUS_BAR_CACHE_MAX_ENTRIES = 32
_STATUS_BAR_FETCH_TIMEOUT_SECONDS = 12.0
_STATUS_BAR_QUICK_TIMEOUT_SECONDS = 3.0

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
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), tz=timezone.utc)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(text)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


def format_jatevo_reset(dt: Optional[datetime]) -> str:
    """Human-readable reset time for CLI / usage output."""
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


# Backward-compatible alias for internal callers.
_format_reset = format_jatevo_reset


def is_jatevo_runtime(provider: Optional[str], base_url: Optional[str] = None) -> bool:
    normalized = str(provider or "").strip().lower()
    if normalized in {"jatevo", "custom:jatevo"}:
        return True
    if normalized.startswith("custom:"):
        slug = normalized.split(":", 1)[1].strip()
        if slug == "jatevo":
            return True
    if base_url and base_url_host_matches(str(base_url), "jatevo.ai"):
        return True
    return False


def is_jatevo_daily_quota_http_error(
    error: Exception,
    *,
    provider: Optional[str] = None,
    base_url: Optional[str] = None,
) -> bool:
    if _http_status_from_error(error) != 429:
        return False
    if provider or base_url:
        return is_jatevo_runtime(provider, base_url)
    blob = f"{error} {getattr(error, 'body', '')}".lower()
    return "jatevo" in blob or "daily request quota" in blob


def append_jatevo_429_hint_if_needed(
    summary: str,
    error: Exception,
    *,
    provider: Optional[str] = None,
    base_url: Optional[str] = None,
) -> str:
    if "/jquota" in summary:
        return summary
    if not is_jatevo_daily_quota_http_error(error, provider=provider, base_url=base_url):
        return summary
    return f"{summary.rstrip()}{JATEVO_429_HINT}"


def format_jatevo_status_bar_quota(report: JatevoQuotaReport) -> str:
    return f"JV {report.daily_used}/{report.daily_max}"


def jatevo_status_bar_used_percent(report: JatevoQuotaReport) -> int:
    return max(0, min(100, round(report.used_fraction * 100)))


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


def resolve_status_bar_jatevo_quota(
    *,
    provider: Optional[str],
    base_url: Optional[str],
    api_key: Optional[str],
    cache_bucket: str = "default",
) -> Optional[tuple[str, int]]:
    """Return ``(label, used_percent)`` for the TUI status bar, with TTL cache."""
    if not is_jatevo_runtime(provider, base_url):
        return None
    now = time.monotonic()
    cache_key = f"{cache_bucket}:{provider}:{base_url}"
    cached = _STATUS_BAR_CACHE.get(cache_key)
    if cached and (now - cached[1]) < _STATUS_BAR_CACHE_TTL_SECONDS:
        report = cached[0]
        return format_jatevo_status_bar_quota(report), jatevo_status_bar_used_percent(report)

    with _STATUS_BAR_LOCK:
        if cache_key in _STATUS_BAR_INFLIGHT:
            if cached:
                report = cached[0]
                return format_jatevo_status_bar_quota(report), jatevo_status_bar_used_percent(report)
            return "JV …", 0
        _STATUS_BAR_INFLIGHT.add(cache_key)

    try:
        report = fetch_jatevo_quota(
            base_url=base_url,
            api_key=api_key,
            requested_provider=provider or "jatevo",
            timeout=_STATUS_BAR_QUICK_TIMEOUT_SECONDS,
        )
        with _STATUS_BAR_LOCK:
            _STATUS_BAR_CACHE[cache_key] = (report, now)
            _prune_status_bar_cache(now)
        return format_jatevo_status_bar_quota(report), jatevo_status_bar_used_percent(report)
    except Exception:
        if cached:
            report = cached[0]
            return format_jatevo_status_bar_quota(report), jatevo_status_bar_used_percent(report)
        return "JV —", 0
    finally:
        with _STATUS_BAR_LOCK:
            _STATUS_BAR_INFLIGHT.discard(cache_key)


def _resolve_usage_url(base_url: str) -> str:
    normalized = str(base_url or "").strip().rstrip("/")
    if not normalized:
        normalized = "https://jatevo.ai/v1"
    if normalized.endswith("/usage"):
        return normalized
    if normalized.endswith("/v1"):
        return f"{normalized}/usage"
    return f"{normalized}/v1/usage"


def _daily_request_limit(payload: dict[str, Any]) -> Optional[dict[str, Any]]:
    for limit in payload.get("limits") or []:
        if not isinstance(limit, dict):
            continue
        if (
            str(limit.get("limit_type") or "").strip().lower() == "requests"
            and str(limit.get("limit_window") or "").strip().lower() == "daily"
        ):
            return limit
    return None


@dataclass(frozen=True)
class JatevoQuotaReport:
    daily_used: int
    daily_max: int
    reset_at: Optional[datetime] = None
    request_count: Optional[int] = None
    total_tokens: Optional[int] = None
    total_cost_usd: Optional[float] = None
    fetched_at: datetime = field(default_factory=_utc_now)

    @property
    def remaining(self) -> int:
        return max(0, self.daily_max - self.daily_used)

    @property
    def used_fraction(self) -> float:
        if self.daily_max <= 0:
            return 0.0
        return max(0.0, min(1.0, self.daily_used / self.daily_max))


class JatevoQuotaError(Exception):
    pass


def fetch_jatevo_quota(
    *,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    requested_provider: str = "jatevo",
    timeout: float = _STATUS_BAR_FETCH_TIMEOUT_SECONDS,
) -> JatevoQuotaReport:
    """Load dashboard-style daily quota from Jatevo ``GET /v1/usage``."""
    requested = (
        "custom:jatevo"
        if str(requested_provider or "").strip().lower().startswith("custom:")
        else "jatevo"
    )
    runtime = resolve_runtime_provider(
        requested=requested,
        explicit_base_url=base_url,
        explicit_api_key=api_key,
    )
    token = str(runtime.get("api_key", "") or "").strip()
    if not token or token == "no-key-required":
        token = str(os.getenv("JATEVO_API_KEY", "") or "").strip()
    if not token:
        raise JatevoQuotaError(
            "Set JATEVO_API_KEY (sk-clb-…) — sync via SYNC_HERMES_API_ENV.bat or jatevo.ai/dashboard"
        )
    resolved_base = str(runtime.get("base_url", "") or base_url or "https://jatevo.ai/v1").rstrip("/")
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "User-Agent": "hermes-cli",
    }
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(_resolve_usage_url(resolved_base), headers=headers)
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        if status == 401:
            raise JatevoQuotaError(
                "Jatevo API key rejected (401) — check sk-clb-… and base_url https://jatevo.ai/v1"
            ) from exc
        raise JatevoQuotaError(f"Jatevo usage API HTTP {status}") from exc
    except httpx.RequestError as exc:
        raise JatevoQuotaError(f"Jatevo usage API unreachable: {exc}") from exc

    try:
        payload = response.json() or {}
    except ValueError as exc:
        raise JatevoQuotaError("Jatevo usage API returned invalid JSON") from exc
    if not isinstance(payload, dict):
        raise JatevoQuotaError("Jatevo usage API returned unexpected payload")

    daily = _daily_request_limit(payload)
    if not daily:
        raise JatevoQuotaError("Jatevo usage API returned no daily request limit.")
    max_value = daily.get("max_value")
    if not isinstance(max_value, (int, float)) or int(max_value) <= 0:
        raise JatevoQuotaError("Jatevo daily quota max_value missing or invalid.")
    daily_max = int(max_value)
    if isinstance(daily.get("current_value"), (int, float)):
        daily_used = int(daily["current_value"])
    elif isinstance(daily.get("remaining_value"), (int, float)):
        daily_used = max(0, daily_max - int(daily["remaining_value"]))
    elif isinstance(payload.get("request_count"), (int, float)):
        daily_used = int(payload["request_count"])
    else:
        daily_used = 0
    daily_used = min(max(0, daily_used), daily_max)

    request_count = (
        int(payload["request_count"])
        if isinstance(payload.get("request_count"), (int, float))
        else None
    )
    total_tokens = (
        int(payload["total_tokens"])
        if isinstance(payload.get("total_tokens"), (int, float))
        else None
    )
    total_cost = (
        float(payload["total_cost_usd"])
        if isinstance(payload.get("total_cost_usd"), (int, float))
        else None
    )
    return JatevoQuotaReport(
        daily_used=daily_used,
        daily_max=daily_max,
        reset_at=_parse_dt(daily.get("reset_at")),
        request_count=request_count,
        total_tokens=total_tokens,
        total_cost_usd=total_cost,
        fetched_at=_utc_now(),
    )


def render_jatevo_quota_lines(
    report: JatevoQuotaReport,
    *,
    markdown: bool = False,
    include_usage_stats: bool = False,
) -> list[str]:
    """Lines matching jatevo.ai dashboard cards (daily requests + daily quota)."""
    bold = "**" if markdown else ""
    lines = [f"📊 {bold}Jatevo quota{bold}"]
    lines.append(
        f"Daily requests: {report.daily_used} / {report.daily_max} (current key usage)"
    )
    lines.append(f"Daily quota: {report.daily_max} requests/day")
    if report.reset_at:
        lines.append(f"Resets {format_jatevo_reset(report.reset_at)} (00:00 UTC)")
    if include_usage_stats:
        if report.total_tokens is not None and report.total_tokens > 0:
            lines.append(f"Tokens today: {report.total_tokens:,}")
        if report.total_cost_usd is not None:
            lines.append(f"Cost today: ${report.total_cost_usd:.4f}")
    lines.append("JTVO balance: see jatevo.ai/dashboard (not exposed on /v1 API)")
    return lines
