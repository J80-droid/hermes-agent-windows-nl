"""Tests for merge_legacy_providers_config.py."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

_repo = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_repo))
sys.path.insert(0, str(_repo / "windows" / "scripts"))

from merge_legacy_providers_config import merge_legacy_into_runtime


def test_merge_venice_provider_only_when_missing(tmp_path):
    legacy = {
        "providers": {
            "venice": {
                "base_url": "https://api.venice.ai/api/v1",
                "provider": "custom",
                "api_key_env": "VENICE_API_KEY",
            }
        }
    }
    runtime = {"providers": {}, "model": {"default": "gemini-3.5-flash"}}
    merged, changes = merge_legacy_into_runtime(legacy=legacy, runtime=runtime)
    assert "venice" in merged["providers"]
    assert any("providers.venice" in c for c in changes)
    assert merged["model"]["default"] == "gemini-3.5-flash"


def test_merge_skips_existing_provider(tmp_path):
    legacy = {"providers": {"venice": {"base_url": "https://old"}}}
    runtime = {"providers": {"venice": {"base_url": "https://api.venice.ai/api/v1"}}}
    merged, changes = merge_legacy_into_runtime(legacy=legacy, runtime=runtime)
    assert merged["providers"]["venice"]["base_url"] == "https://api.venice.ai/api/v1"
    assert changes == []


def test_merge_jatevo_provider_only_when_missing(tmp_path):
    legacy = {
        "providers": {
            "jatevo": {
                "base_url": "https://jatevo.ai/v1",
                "provider": "custom",
                "api_key_env": "JATEVO_API_KEY",
            }
        }
    }
    runtime = {"providers": {}, "model": {"default": "gemini-3.1-pro-preview"}}
    merged, changes = merge_legacy_into_runtime(legacy=legacy, runtime=runtime)
    assert "jatevo" in merged["providers"]
    assert any("providers.jatevo" in c for c in changes)
