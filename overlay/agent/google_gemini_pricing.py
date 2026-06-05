"""Fork Google Gemini pricing (overlay; Tier A agent/usage_pricing.py unchanged)."""
from __future__ import annotations

from decimal import Decimal
from typing import Dict, Optional

from agent.usage_pricing import PricingEntry

_GOOGLE_PRICING_SOURCE_URL = "https://ai.google.dev/gemini-api/docs/pricing"
_GOOGLE_PRICING_VERSION = "google-pricing-2026-05-23"

_GOOGLE_GEMINI_PRICING: Dict[str, Dict[str, Decimal]] = {
    "gemini-3.5-flash": {
        "input": Decimal("1.50"),
        "output": Decimal("9.00"),
        "cache_read": Decimal("0.15"),
    },
    "gemini-3.1-flash-lite": {
        "input": Decimal("0.25"),
        "output": Decimal("1.50"),
        "cache_read": Decimal("0.025"),
    },
    "gemini-2.5-pro": {
        "input": Decimal("1.25"),
        "output": Decimal("10.00"),
        "cache_read": Decimal("0.125"),
    },
    "gemini-2.5-flash": {
        "input": Decimal("0.30"),
        "output": Decimal("2.50"),
        "cache_read": Decimal("0.03"),
    },
    "gemini-2.5-flash-lite": {
        "input": Decimal("0.10"),
        "output": Decimal("0.40"),
        "cache_read": Decimal("0.01"),
    },
    "gemini-2.0-flash": {
        "input": Decimal("0.10"),
        "output": Decimal("0.40"),
        "cache_read": Decimal("0.025"),
    },
}


def _normalize_google_model_name(model: str) -> str:
    """Map Gemini preview ids to the nearest priced catalog entry."""
    name = model.lower().strip()
    if name.startswith("google/"):
        name = name.split("/", 1)[1]
    if name in _GOOGLE_GEMINI_PRICING:
        return name
    aliases = {
        "gemini-3-flash-preview": "gemini-3.5-flash",
        "gemini-3-flash": "gemini-3.5-flash",
        "gemini-3-pro-preview": "gemini-2.5-pro",
        "gemini-3.1-pro-preview": "gemini-2.5-pro",
        "gemini-3.1-flash-lite-preview": "gemini-3.1-flash-lite",
    }
    if name in aliases:
        return aliases[name]
    if "flash-lite" in name and name.startswith("gemini-3"):
        return "gemini-3.1-flash-lite"
    if "flash-lite" in name and name.startswith("gemini-2"):
        return "gemini-2.5-flash-lite"
    if name.startswith("gemini-3") and "flash" in name:
        return "gemini-3.5-flash"
    if name.startswith("gemini-3") and "pro" in name:
        return "gemini-2.5-pro"
    return name

def _google_pricing_entry(model: str) -> Optional[PricingEntry]:
    """Build a Google Gemini PricingEntry from the catalog table."""
    normalized = _normalize_google_model_name(model)
    row = _GOOGLE_GEMINI_PRICING.get(normalized)
    if not row:
        return None

    input_rate = row["input"]
    cache_read = row.get("cache_read")
    cache_write = row.get("cache_write", input_rate)

    return PricingEntry(
        input_cost_per_million=input_rate,
        output_cost_per_million=row["output"],
        cache_read_cost_per_million=cache_read,
        cache_write_cost_per_million=cache_write,
        source="official_docs_snapshot",
        source_url=_GOOGLE_PRICING_SOURCE_URL,
        pricing_version=_GOOGLE_PRICING_VERSION,
    )


def try_google_pricing_entry(
    model_name: str,
    *args: object,
    provider: Optional[str] = None,
    base_url: Optional[str] = None,
    **kwargs: object,
) -> Optional[PricingEntry]:
    prov = (provider or "").strip().lower()
    host = (base_url or "").lower()
    if prov not in {"gemini", "google", "google-gemini-cli"} and "generativelanguage.googleapis.com" not in host:
        if "gemini" not in (model_name or "").lower():
            return None
    return _google_pricing_entry(model_name)
