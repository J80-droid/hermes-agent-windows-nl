#!/usr/bin/env python3
"""E2E: institutional pipeline hardening (normalize → render → score).

Covers single-normalize contract, compact_institutional_check, compact Controle peel,
finalize-only streaming invariants, render score verify, and pipeline contract pytest.
No live Hermes runtime or LLM.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from overlay.bootstrap import install

install()

FAILURES = 0
STEP = 0

_ROOKTEST_MD = (
    "<institutional_check>\n"
    "- Controle hyperbolen: [Uitgevoerd]\n"
    "- Controle stelligheden: [Uitgevoerd]\n"
    "</institutional_check>\n\n"
    "## Projectoverzicht\n"
    "Objectieve intro.\n\n"
    "**Dossierstatus:**\n"
    "Gereed voor controle.\n\n"
    "### Team Samenstelling\n"
    "| Naam | Rol | Status |\n| --- | --- | --- |\n| A | Lead | Actief |\n\n"
    "## Functionele requirements\n"
    "| ID | Requirement | Prioriteit |\n| --- | --- | --- |\n| FR-01 | Test | Hoog |\n"
)

_PROSE_CONTROLE_MD = (
    "## Projectoverzicht\nControle en verificatie van het plan.\n"
)


def _step(name: str, ok: bool, detail: str = "") -> None:
    global FAILURES, STEP
    STEP += 1
    suffix = f" - {detail}" if detail else ""
    if ok:
        print(f"[OK] E{STEP} {name}{suffix}", flush=True)
    else:
        print(f"[FAIL] E{STEP} {name}{suffix}", file=sys.stderr, flush=True)
        FAILURES += 1


def test_e1_repo_artifacts() -> None:
    required = [
        REPO_ROOT / "overlay" / "hermes_cli" / "institutional_render.py",
        REPO_ROOT / "overlay" / "hermes_cli" / "display_markdown.py",
        REPO_ROOT / "overlay" / "hermes_cli" / "markdown_output_normalize.py",
        REPO_ROOT / "scripts" / "score_institutional_render.py",
        REPO_ROOT / "scripts" / "bench_normalize_markdown.py",
        REPO_ROOT / "tests" / "hermes_cli" / "test_render_pipeline_contract.py",
        REPO_ROOT / "audits" / "InstitutionalPipelineE2E.harness.py",
        REPO_ROOT / "audits" / "RUN_INSTITUTIONAL_PIPELINE_E2E.bat",
    ]
    missing = [p.relative_to(REPO_ROOT) for p in required if not p.is_file()]
    _step("repo-artefacten pipeline hardening", not missing, ", ".join(map(str, missing)) or "OK")


def test_e2_compact_institutional_check_normalizer() -> None:
    from hermes_cli.markdown_output_normalize import normalize_assistant_markdown

    raw = (
        "<institutional_check>\n- Controle hyperbolen: [Uitgevoerd]\n</institutional_check>\n\n"
        "## Projectoverzicht\nTekst.\n"
    )
    out = normalize_assistant_markdown(raw)
    ok = (
        "<institutional_check>" not in out.lower()
        and "Controle  ·" in out
        and "hyperbolen" in out
        and "## Projectoverzicht" in out
    )
    _step("compact_institutional_check in normalize pipeline", ok)


def test_e3_single_normalize_on_format_response_ansi() -> None:
    from hermes_cli.display_markdown import format_response_ansi

    calls = 0

    def _counting_norm(text: str, **kwargs: object) -> str:
        nonlocal calls
        calls += 1
        from hermes_cli.markdown_output_normalize import normalize_assistant_markdown

        return normalize_assistant_markdown(text, **kwargs)  # type: ignore[arg-type]

    with patch("hermes_cli.display_markdown.normalize_assistant_markdown", side_effect=_counting_norm):
        out = format_response_ansi(_ROOKTEST_MD, cols=100)
    ok = calls == 1 and bool(out and out.strip())
    _step("format_response_ansi normaliseert exact één keer", ok, f"calls={calls}")


def test_e4_render_from_prepared_skips_normalize() -> None:
    from hermes_cli.institutional_render import render_institutional_from_prepared

    with patch("hermes_cli.institutional_render.normalize_assistant_markdown") as mock_norm:
        render_institutional_from_prepared("## Test\nBody.")
    ok = mock_norm.call_count == 0
    _step("render_institutional_from_prepared slaat normalize over", ok)


def test_e5_strict_render_contract() -> None:
    from hermes_cli.institutional_render import render_institutional_assistant

    try:
        with patch.dict(os.environ, {"HERMES_STRICT_RENDER": "1"}, clear=False):
            render_institutional_assistant("## Test\nBody", already_normalized=False)
        ok = False
        detail = "geen ValueError"
    except ValueError as exc:
        ok = "already_normalized" in str(exc)
        detail = "OK"
    except Exception as exc:
        ok = False
        detail = str(exc)
    _step("HERMES_STRICT_RENDER=1 weigert dubbele normalize", ok, detail)


def test_e6_render_compact_controle_no_xml() -> None:
    from hermes_cli.display_markdown import format_response_ansi
    from hermes_cli.markdown_output_normalize import normalize_assistant_markdown

    out = format_response_ansi(normalize_assistant_markdown(_ROOKTEST_MD), cols=100) or ""
    ok = (
        "Controle" in out
        and "institutional_check" not in out.lower()
        and "Projectoverzicht" in out
    )
    _step("render: compacte Controle, geen XML-tags", ok)


def test_e7_prose_controle_not_checklist() -> None:
    from hermes_cli.display_markdown import format_response_ansi
    from hermes_cli.institutional_render import _is_compact_check_block
    from hermes_cli.institutional_render import render_institutional_from_prepared
    from hermes_cli.markdown_output_normalize import normalize_assistant_markdown

    plain = normalize_assistant_markdown(_PROSE_CONTROLE_MD)
    renderable = render_institutional_from_prepared(plain)
    ansi = format_response_ansi(plain, cols=100) or ""
    ok = (
        not _is_compact_check_block(renderable)
        and "Controle" in ansi
        and "·" not in ansi.split("Controle", 1)[-1][:20]
    )
    _step("prose 'Controle en …' geen valse checklist", ok)


def test_e8_streaming_finalize_only() -> None:
    from hermes_cli.display_markdown import StreamingRenderer, format_response_ansi

    renderer = StreamingRenderer(cols=100)
    with patch("hermes_cli.display_markdown.format_response_ansi") as mock_fmt:
        for chunk in ("## Kop\n", "tekst\n"):
            assert renderer.feed(chunk) is None
        assert mock_fmt.call_count == 0
    with patch("hermes_cli.display_markdown.format_response_ansi", return_value="ok") as mock_fmt:
        renderer.feed("## Functionele\nBody.\n")
        out = renderer.finish()
    ok = mock_fmt.call_count == 1 and out == "ok"
    _step("StreamingRenderer: geen ANSI per chunk, één bij finish", ok)


def test_e9_score_verify() -> None:
    script = REPO_ROOT / "scripts" / "score_institutional_render.py"
    proc = subprocess.run(
        [sys.executable, str(script), "--verify"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        check=False,
    )
    combined = (proc.stdout or "") + (proc.stderr or "")
    score_ok = False
    for line in combined.splitlines():
        if "TOTAAL" in line:
            # e.g. "  TOTAAL               10.0/10"
            try:
                score_ok = float(line.split()[-1].split("/")[0]) >= 9.0
            except (ValueError, IndexError):
                score_ok = False
            break
    if not score_ok:
        score_ok = "10.0/10" in combined or "9." in combined
    ok = proc.returncode == 0 and score_ok
    detail = combined[:180] if not ok else "score >= 9.0"
    _step("score_institutional_render.py --verify", ok, detail)


def test_e10_pytest_pipeline_contract() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/hermes_cli/test_render_pipeline_contract.py",
            "-q",
            "--tb=short",
            "-o",
            "addopts=",
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        check=False,
    )
    ok = proc.returncode == 0
    detail = (proc.stderr or proc.stdout or "")[-200:] if not ok else "pytest OK"
    _step("pytest test_render_pipeline_contract", ok, detail)


def test_e11_ts_parity_institutional_check() -> None:
    runner = REPO_ROOT / "scripts" / "normalize_assistant_markdown_ts_runner.ts"
    npx = shutil.which("npx")
    if not runner.is_file():
        _step("TS parity institutional_check_compact", True, "SKIP runner ontbreekt")
        return
    if not npx:
        _step("TS parity institutional_check_compact", True, "SKIP npx niet op PATH")
        return

    from hermes_cli.markdown_output_normalize import normalize_assistant_markdown

    raw = (
        "<institutional_check>\n- Controle hyperbolen: [Uitgevoerd]\n</institutional_check>\n\n"
        "## Projectoverzicht\nTekst.\n"
    )
    py_out = normalize_assistant_markdown(raw)
    try:
        proc = subprocess.run(
            [npx, "--yes", "tsx", str(runner)],
            input=raw,
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=str(REPO_ROOT),
            timeout=120,
            check=False,
        )
    except Exception as exc:
        _step("TS parity institutional_check_compact", False, str(exc))
        return
    if proc.returncode != 0:
        _step(
            "TS parity institutional_check_compact",
            False,
            (proc.stderr or proc.stdout or "")[:200],
        )
        return
    ok = py_out.strip() == (proc.stdout or "").strip()
    _step("TS parity institutional_check_compact", ok)


def main() -> int:
    print("=== InstitutionalPipeline E2E ===", flush=True)
    test_e1_repo_artifacts()
    test_e2_compact_institutional_check_normalizer()
    test_e3_single_normalize_on_format_response_ansi()
    test_e4_render_from_prepared_skips_normalize()
    test_e5_strict_render_contract()
    test_e6_render_compact_controle_no_xml()
    test_e7_prose_controle_not_checklist()
    test_e8_streaming_finalize_only()
    test_e9_score_verify()
    test_e10_pytest_pipeline_contract()
    test_e11_ts_parity_institutional_check()
    if FAILURES:
        print(f"=== HARNESS: FAIL ({FAILURES}) ===", file=sys.stderr)
        return 1
    print(f"=== HARNESS: PASS ({STEP}/{STEP}) ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
