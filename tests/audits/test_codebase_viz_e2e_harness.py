"""Unit tests voor ``audits/CodebaseVizE2E.harness.py``."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

REPO = Path(__file__).resolve().parents[2]
HARNESS_PATH = REPO / "audits" / "CodebaseVizE2E.harness.py"


def _load_harness() -> ModuleType:
    spec = importlib.util.spec_from_file_location("codebase_viz_e2e_harness", HARNESS_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def harness() -> ModuleType:
    assert HARNESS_PATH.is_file()
    return _load_harness()


@pytest.fixture(autouse=True)
def _reset_counters(harness: ModuleType):
    harness.FAILURES = 0
    harness.STEP = 0
    yield
    harness.FAILURES = 0
    harness.STEP = 0


def test_step_ok(harness: ModuleType) -> None:
    harness._step("x", True)
    assert harness.STEP == 1
    assert harness.FAILURES == 0


def test_step_fail(harness: ModuleType) -> None:
    harness._step("x", False, "detail")
    assert harness.FAILURES == 1


def test_v3_parse_pygount_3x(harness: ModuleType) -> None:
    harness.test_v3_parse_pygount_3x()
    assert harness.FAILURES == 0


def test_v4_invalid_json(harness: ModuleType) -> None:
    harness.test_v4_parse_invalid_json()
    assert harness.FAILURES == 0


def test_manifest_version(harness: ModuleType) -> None:
    data = json.loads((harness.MANIFEST).read_text(encoding="utf-8"))
    assert data["name"] == "codebase-viz"
    assert data["version"] == "2.3.0"
