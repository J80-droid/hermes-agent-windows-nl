"""Unit tests for windows/scripts/summarize_pytest_junit.py."""

from __future__ import annotations

import importlib.util
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SUMMARIZER_PATH = REPO / "windows" / "scripts" / "summarize_pytest_junit.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("summarize_pytest_junit", SUMMARIZER_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def summarizer():
    return _load_module()


def _write_junit(path: Path, cases: list[tuple[str, str, str | None]]) -> None:
    """cases: (file, name, outcome) outcome None=pass, 'failure', 'error', 'skipped'."""
    suite = ET.Element("testsuite")
    for file_name, test_name, outcome in cases:
        case = ET.SubElement(suite, "testcase", {"file": file_name, "name": test_name})
        if outcome == "failure":
            ET.SubElement(case, "failure", {"message": "fail"})
        elif outcome == "error":
            ET.SubElement(case, "error", {"message": "err"})
        elif outcome == "skipped":
            ET.SubElement(case, "skipped")
    ET.ElementTree(suite).write(path, encoding="utf-8", xml_declaration=True)


def test_summarize_happy_path_counts(summarizer, tmp_path: Path) -> None:
    junit = tmp_path / "out.xml"
    _write_junit(
        junit,
        [
            ("tests/a.py", "test_ok", None),
            ("tests/a.py", "test_fail", "failure"),
            ("tests/b.py", "test_skip", "skipped"),
            ("tests/b.py", "test_err", "error"),
        ],
    )
    payload = summarizer.summarize(junit)
    assert payload["passed"] == 1
    assert payload["failed"] == 1
    assert payload["skipped"] == 1
    assert payload["errors"] == 1
    assert payload["failed_nodeids_count"] == 2


def test_canonical_nodeid_path_vs_dot(summarizer) -> None:
    path_style = "tests/agent/lsp/test_workspace.py::test_normalize_path_expands_tilde"
    dot_style = "tests.agent.lsp.test_workspace::test_normalize_path_expands_tilde"
    assert summarizer._canonical_nodeid(path_style) == summarizer._canonical_nodeid(dot_style)


def test_summarize_known_dot_matches_junit_path(summarizer, tmp_path: Path) -> None:
    junit = tmp_path / "out.xml"
    _write_junit(
        junit,
        [("tests/agent/lsp/test_workspace.py", "test_normalize_path_expands_tilde", "failure")],
    )
    known = {"tests.agent.lsp.test_workspace::test_normalize_path_expands_tilde"}
    payload = summarizer.summarize(junit, known)
    assert payload["new_failures_count"] == 0
    assert payload["known_failures_count"] == 1


def test_summarize_known_vs_new(summarizer, tmp_path: Path) -> None:
    junit = tmp_path / "out.xml"
    _write_junit(
        junit,
        [
            ("tests/a.py", "test_known", "failure"),
            ("tests/a.py", "test_new", "failure"),
        ],
    )
    known = {"tests/a.py::test_known"}
    payload = summarizer.summarize(junit, known)
    assert payload["new_failures_count"] == 1
    assert payload["known_failures_count"] == 1
    assert payload["new_failures"] == ["tests/a.py::test_new"]


def test_summarize_top_modules_limited_to_twenty(summarizer, tmp_path: Path) -> None:
    junit = tmp_path / "out.xml"
    cases = [(f"tests/mod{i}.py", "test_x", "failure") for i in range(25)]
    _write_junit(junit, cases)
    payload = summarizer.summarize(junit)
    assert len(payload["top_failure_modules"]) == 20


def test_summarize_invalid_xml_raises(summarizer, tmp_path: Path) -> None:
    bad = tmp_path / "bad.xml"
    bad.write_text("<testsuite><testcase", encoding="utf-8")
    with pytest.raises(ValueError, match="invalid junit xml"):
        summarizer.summarize(bad)


def test_load_known_fails_skips_comments_and_blanks(summarizer, tmp_path: Path) -> None:
    known_file = tmp_path / "known.txt"
    known_file.write_text(
        "# comment\n\n tests/a.py::test_one \n# tail\n",
        encoding="utf-8",
    )
    known = summarizer._load_known_fails(known_file)
    assert known == {"tests.a::test_one"}


def test_load_known_fails_missing_path_returns_empty(summarizer) -> None:
    assert summarizer._load_known_fails(None) == set()
    assert summarizer._load_known_fails(Path("/nonexistent/known.txt")) == set()


def test_main_missing_junit_exit_one(summarizer, tmp_path: Path, monkeypatch, capsys) -> None:
    out = tmp_path / "summary.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "summarize_pytest_junit.py",
            "--junit",
            str(tmp_path / "missing.xml"),
            "--output",
            str(out),
        ],
    )
    assert summarizer.main() == 1
    assert "junit missing" in capsys.readouterr().err


def test_nodeid_from_case_classname_fallback(summarizer) -> None:
    suite = ET.Element("testsuite")
    case = ET.SubElement(suite, "testcase", {"classname": "tests.mod", "name": "test_x"})
    ET.SubElement(case, "failure")
    nodeid = summarizer._nodeid_from_case(case)
    assert nodeid == "tests.mod::test_x"


def test_summarize_new_failures_capped_at_fifty(summarizer, tmp_path: Path) -> None:
    junit = tmp_path / "out.xml"
    cases = [(f"tests/m{i}.py", "test_fail", "failure") for i in range(60)]
    _write_junit(junit, cases)
    payload = summarizer.summarize(junit)
    assert len(payload["new_failures"]) == 50
    assert payload["new_failures_count"] == 60


def test_main_writes_summary_json(summarizer, tmp_path: Path, monkeypatch, capsys) -> None:
    junit = tmp_path / "out.xml"
    _write_junit(junit, [("tests/a.py", "test_ok", None)])
    out = tmp_path / "summary.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "summarize_pytest_junit.py",
            "--junit",
            str(junit),
            "--output",
            str(out),
        ],
    )
    assert summarizer.main() == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["passed"] == 1
    assert "Wrote" in capsys.readouterr().out
