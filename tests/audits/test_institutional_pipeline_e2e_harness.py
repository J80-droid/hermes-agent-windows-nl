"""Unit tests voor ``audits/InstitutionalPipelineE2E.harness.py``.

Piramide:
  - Unit (hier): helpers + scenario's met mocks (geen subprocess score/pytest in E9/E10)
  - Integratie: ``test_institutional_pipeline_e2e_harness_runs`` (volledige harness)

Conventie: importlib-laden zoals ``tests/audits/test_creative_domain_e2e_harness.py``.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

REPO = Path(__file__).resolve().parents[2]
HARNESS_PATH = REPO / "audits" / "InstitutionalPipelineE2E.harness.py"


def _load_harness() -> ModuleType:
    spec = importlib.util.spec_from_file_location("institutional_pipeline_e2e_harness", HARNESS_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def harness() -> ModuleType:
    assert HARNESS_PATH.is_file(), "InstitutionalPipelineE2E.harness.py ontbreekt"
    return _load_harness()


@pytest.fixture(autouse=True)
def _reset_harness_counters(harness: ModuleType) -> None:
    harness.FAILURES = 0
    harness.STEP = 0
    yield
    harness.FAILURES = 0
    harness.STEP = 0


# ---------------------------------------------------------------------------
# _step
# ---------------------------------------------------------------------------


class TestStep:
    def test_ok_increments_step_only(self, harness: ModuleType) -> None:
        harness._step("naam", True, "detail")
        assert harness.STEP == 1
        assert harness.FAILURES == 0

    def test_fail_increments_failures(self, harness: ModuleType) -> None:
        harness._step("naam", False, "fout")
        assert harness.STEP == 1
        assert harness.FAILURES == 1

    def test_empty_detail(self, harness: ModuleType) -> None:
        harness._step("zonder-detail", True)
        assert harness.STEP == 1


# ---------------------------------------------------------------------------
# E1 repo artifacts
# ---------------------------------------------------------------------------


class TestE1RepoArtifacts:
    def test_happy_path_all_present(self, harness: ModuleType) -> None:
        harness.test_e1_repo_artifacts()
        assert harness.FAILURES == 0
        assert harness.STEP == 1

    def test_missing_file_fails(self, harness: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
        fake_root = REPO / "nonexistent_repo_root_for_test"
        monkeypatch.setattr(harness, "REPO_ROOT", fake_root)
        harness.test_e1_repo_artifacts()
        assert harness.FAILURES == 1


# ---------------------------------------------------------------------------
# E2 compact check
# ---------------------------------------------------------------------------


class TestE2CompactCheck:
    def test_happy_path(self, harness: ModuleType) -> None:
        harness.test_e2_compact_institutional_check_normalizer()
        assert harness.FAILURES == 0

    def test_normalize_without_compact_fails(self, harness: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
        def _passthrough(text: str, **_kwargs: object) -> str:
            return text

        monkeypatch.setattr(
            "hermes_cli.markdown_output_normalize.normalize_assistant_markdown",
            _passthrough,
        )
        harness.test_e2_compact_institutional_check_normalizer()
        assert harness.FAILURES == 1


# ---------------------------------------------------------------------------
# E3 single normalize
# ---------------------------------------------------------------------------


class TestE3SingleNormalize:
    def test_happy_path(self, harness: ModuleType) -> None:
        harness.test_e3_single_normalize_on_format_response_ansi()
        assert harness.FAILURES == 0

    def test_double_normalize_fails(self, harness: ModuleType) -> None:
        def _fmt_double(md: str, cols: int = 100) -> str:
            from hermes_cli.display_markdown import normalize_assistant_markdown

            normalize_assistant_markdown(md)
            normalize_assistant_markdown(md)
            return "ok"

        with patch(
            "hermes_cli.display_markdown.format_response_ansi",
            side_effect=_fmt_double,
        ):
            harness.test_e3_single_normalize_on_format_response_ansi()
        assert harness.FAILURES == 1

    def test_empty_render_output_fails(self, harness: ModuleType) -> None:
        with patch(
            "hermes_cli.display_markdown.normalize_assistant_markdown",
            side_effect=lambda text, **_: text,
        ):
            with patch("hermes_cli.display_markdown.format_response_ansi", return_value="   "):
                harness.test_e3_single_normalize_on_format_response_ansi()
        assert harness.FAILURES == 1


# ---------------------------------------------------------------------------
# E4 prepared render
# ---------------------------------------------------------------------------


class TestE4PreparedRender:
    def test_happy_path(self, harness: ModuleType) -> None:
        harness.test_e4_render_from_prepared_skips_normalize()
        assert harness.FAILURES == 0

    def test_normalize_called_fails(self, harness: ModuleType) -> None:
        import hermes_cli.institutional_render as ir

        real_prepared = ir.render_institutional_from_prepared

        def _calls_normalize_first(plain: str, **kwargs: object) -> object:
            ir.normalize_assistant_markdown(plain)
            return real_prepared(plain, **kwargs)  # type: ignore[arg-type]

        with patch.object(ir, "render_institutional_from_prepared", _calls_normalize_first):
            harness.test_e4_render_from_prepared_skips_normalize()
        assert harness.FAILURES == 1


# ---------------------------------------------------------------------------
# E5 strict render
# ---------------------------------------------------------------------------


class TestE5StrictRender:
    def test_happy_path_raises_value_error(self, harness: ModuleType) -> None:
        harness.test_e5_strict_render_contract()
        assert harness.FAILURES == 0

    def test_no_exception_fails(self, harness: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "hermes_cli.institutional_render.render_institutional_assistant",
            lambda *a, **k: MagicMock(),
        )
        harness.test_e5_strict_render_contract()
        assert harness.FAILURES == 1

    def test_wrong_exception_fails(self, harness: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
        def _boom(*_a: object, **_k: object) -> None:
            raise RuntimeError("niet normalize")

        monkeypatch.setattr(
            "hermes_cli.institutional_render.render_institutional_assistant",
            _boom,
        )
        harness.test_e5_strict_render_contract()
        assert harness.FAILURES == 1


# ---------------------------------------------------------------------------
# E6 render no XML
# ---------------------------------------------------------------------------


class TestE6RenderNoXml:
    def test_happy_path(self, harness: ModuleType) -> None:
        with patch(
            "hermes_cli.display_markdown.format_response_ansi",
            return_value="Controle ok\nProjectoverzicht",
        ):
            with patch(
                "hermes_cli.markdown_output_normalize.normalize_assistant_markdown",
                side_effect=lambda t, **_: "Controle  · x\n\n## Projectoverzicht",
            ):
                harness.test_e6_render_compact_controle_no_xml()
        assert harness.FAILURES == 0

    def test_xml_in_output_fails(self, harness: ModuleType) -> None:
        with patch(
            "hermes_cli.display_markdown.format_response_ansi",
            return_value="<institutional_check>leak",
        ):
            with patch(
                "hermes_cli.markdown_output_normalize.normalize_assistant_markdown",
                side_effect=lambda t, **_: t,
            ):
                harness.test_e6_render_compact_controle_no_xml()
        assert harness.FAILURES == 1


# ---------------------------------------------------------------------------
# E7 prose controle
# ---------------------------------------------------------------------------


class TestE7ProseControle:
    def test_happy_path(self, harness: ModuleType) -> None:
        with patch(
            "hermes_cli.institutional_render._is_compact_check_block",
            return_value=False,
        ):
            with patch(
                "hermes_cli.display_markdown.format_response_ansi",
                return_value="Controle en verificatie",
            ):
                with patch(
                    "hermes_cli.institutional_render.render_institutional_from_prepared",
                    return_value=MagicMock(),
                ):
                    with patch(
                        "hermes_cli.markdown_output_normalize.normalize_assistant_markdown",
                        side_effect=lambda t, **_: t,
                    ):
                        harness.test_e7_prose_controle_not_checklist()
        assert harness.FAILURES == 0

    def test_false_compact_block_fails(self, harness: ModuleType) -> None:
        with patch(
            "hermes_cli.institutional_render._is_compact_check_block",
            return_value=True,
        ):
            with patch("hermes_cli.display_markdown.format_response_ansi", return_value="Controle · item"):
                with patch(
                    "hermes_cli.institutional_render.render_institutional_from_prepared",
                    return_value=MagicMock(),
                ):
                    with patch(
                        "hermes_cli.markdown_output_normalize.normalize_assistant_markdown",
                        side_effect=lambda t, **_: t,
                    ):
                        harness.test_e7_prose_controle_not_checklist()
        assert harness.FAILURES == 1


# ---------------------------------------------------------------------------
# E8 streaming
# ---------------------------------------------------------------------------


class TestE8Streaming:
    def test_happy_path(self, harness: ModuleType) -> None:
        harness.test_e8_streaming_finalize_only()
        assert harness.FAILURES == 0

    def test_feed_calls_format_fails(self, harness: ModuleType) -> None:
        with patch("hermes_cli.display_markdown.StreamingRenderer") as mock_cls:
            inst = MagicMock()
            inst.feed.return_value = None
            mock_cls.return_value = inst
            with patch("hermes_cli.display_markdown.format_response_ansi") as mock_fmt:
                mock_fmt.return_value = "leak"
                harness.test_e8_streaming_finalize_only()
        assert harness.FAILURES == 1


# ---------------------------------------------------------------------------
# E9 score verify (mock subprocess)
# ---------------------------------------------------------------------------


class TestE9ScoreVerify:
    def test_happy_path(self, harness: ModuleType) -> None:
        proc = MagicMock(returncode=0, stdout="TOTAAL 10.0/10\n", stderr="")
        with patch("subprocess.run", return_value=proc):
            harness.test_e9_score_verify()
        assert harness.FAILURES == 0

    def test_nonzero_exit_fails(self, harness: ModuleType) -> None:
        proc = MagicMock(returncode=1, stdout="8.0/10", stderr="low score")
        with patch("subprocess.run", return_value=proc):
            harness.test_e9_score_verify()
        assert harness.FAILURES == 1

    def test_subprocess_exception_fails(self, harness: ModuleType) -> None:
        with patch("subprocess.run", side_effect=OSError("spawn failed")):
            with pytest.raises(OSError):
                harness.test_e9_score_verify()


# ---------------------------------------------------------------------------
# E10 pytest contract (mock subprocess)
# ---------------------------------------------------------------------------


class TestE10PytestContract:
    def test_happy_path(self, harness: ModuleType) -> None:
        proc = MagicMock(returncode=0, stdout="5 passed", stderr="")
        with patch("subprocess.run", return_value=proc):
            harness.test_e10_pytest_pipeline_contract()
        assert harness.FAILURES == 0

    def test_pytest_failure(self, harness: ModuleType) -> None:
        proc = MagicMock(returncode=1, stdout="", stderr="FAILED")
        with patch("subprocess.run", return_value=proc):
            harness.test_e10_pytest_pipeline_contract()
        assert harness.FAILURES == 1


# ---------------------------------------------------------------------------
# E11 TS parity
# ---------------------------------------------------------------------------


class _RepoRootMissingRunner:
    """Minimal REPO_ROOT stand-in: TS runner path reports is_file() == False."""

    def __truediv__(self, other: str) -> object:
        base = REPO / other
        if str(base).endswith("normalize_assistant_markdown_ts_runner.ts"):

            class _Missing:
                def is_file(self) -> bool:
                    return False

            return _Missing()
        return _ChainedPath(base)


class _ChainedPath:
    def __init__(self, path: Path) -> None:
        self._path = path

    def __truediv__(self, other: str) -> object:
        nxt = self._path / other
        if str(nxt).endswith("normalize_assistant_markdown_ts_runner.ts"):

            class _Missing:
                def is_file(self) -> bool:
                    return False

            return _Missing()
        return _ChainedPath(nxt)

    def is_file(self) -> bool:
        return self._path.is_file()


class TestE11TsParity:
    def test_skip_when_runner_missing(self, harness: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(harness, "REPO_ROOT", _RepoRootMissingRunner())
        harness.test_e11_ts_parity_institutional_check()
        assert harness.FAILURES == 0

    def test_skip_when_npx_missing(self, harness: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(harness.shutil, "which", lambda _name: None)
        harness.test_e11_ts_parity_institutional_check()
        assert harness.FAILURES == 0

    def test_mismatch_fails(self, harness: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(harness.shutil, "which", lambda _name: "/usr/bin/npx")
        proc = MagicMock(returncode=0, stdout="anders\n", stderr="")
        with patch("subprocess.run", return_value=proc):
            with patch(
                "hermes_cli.markdown_output_normalize.normalize_assistant_markdown",
                return_value="python\n",
            ):
                harness.test_e11_ts_parity_institutional_check()
        assert harness.FAILURES == 1

    def test_runner_error_returncode(self, harness: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(harness.shutil, "which", lambda _name: "/usr/bin/npx")
        proc = MagicMock(returncode=1, stdout="", stderr="tsx error")
        with patch("subprocess.run", return_value=proc):
            harness.test_e11_ts_parity_institutional_check()
        assert harness.FAILURES == 1

    def test_subprocess_raises(self, harness: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(harness.shutil, "which", lambda _name: "/usr/bin/npx")
        with patch("subprocess.run", side_effect=TimeoutError("tsx timeout")):
            harness.test_e11_ts_parity_institutional_check()
        assert harness.FAILURES == 1


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------


class TestMain:
    def test_returns_zero_when_all_pass(self, harness: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
        for name in (
            "test_e1_repo_artifacts",
            "test_e2_compact_institutional_check_normalizer",
            "test_e3_single_normalize_on_format_response_ansi",
            "test_e4_render_from_prepared_skips_normalize",
            "test_e5_strict_render_contract",
            "test_e6_render_compact_controle_no_xml",
            "test_e7_prose_controle_not_checklist",
            "test_e8_streaming_finalize_only",
            "test_e9_score_verify",
            "test_e10_pytest_pipeline_contract",
            "test_e11_ts_parity_institutional_check",
        ):
            monkeypatch.setattr(harness, name, lambda: None)
        assert harness.main() == 0

    def test_returns_one_on_failure(self, harness: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
        def _fail() -> None:
            harness._step("forced", False)

        monkeypatch.setattr(harness, "test_e1_repo_artifacts", _fail)
        for name in (
            "test_e2_compact_institutional_check_normalizer",
            "test_e3_single_normalize_on_format_response_ansi",
            "test_e4_render_from_prepared_skips_normalize",
            "test_e5_strict_render_contract",
            "test_e6_render_compact_controle_no_xml",
            "test_e7_prose_controle_not_checklist",
            "test_e8_streaming_finalize_only",
            "test_e9_score_verify",
            "test_e10_pytest_pipeline_contract",
            "test_e11_ts_parity_institutional_check",
        ):
            monkeypatch.setattr(harness, name, lambda: None)
        assert harness.main() == 1
        assert harness.FAILURES >= 1


# ---------------------------------------------------------------------------
# Integratie (subprocess)
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_institutional_pipeline_e2e_harness_runs() -> None:
    """Volledige audits/InstitutionalPipelineE2E.harness.py."""
    proc = subprocess.run(
        [sys.executable, str(HARNESS_PATH)],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=180,
        check=False,
    )
    assert proc.returncode == 0, (proc.stderr or proc.stdout)[-4000:]
    assert "PASS" in (proc.stdout or "")
