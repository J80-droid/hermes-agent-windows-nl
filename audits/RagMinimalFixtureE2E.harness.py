#!/usr/bin/env python3
"""E2E: RAG minimal fixtures seed + preflight + single-domain ingest (temp dirs)."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PY = Path.home() / "miniconda3/envs/hermes-env/python.exe"
if not PY.is_file():
    PY = Path(sys.executable)

FAILURES = 0


def _step(name: str, ok: bool, detail: str = "") -> None:
    global FAILURES
    suffix = f" -- {detail}" if detail else ""
    if ok:
        print(f"[OK] {name}{suffix}")
    else:
        print(f"[FAIL] {name}{suffix}", file=sys.stderr)
        FAILURES += 1


def main() -> int:
    print("=" * 60)
    print("  RAG Minimal Fixture E2E")
    print("=" * 60)

    fixtures = REPO / "fixtures" / "rag_minimal"
    if not fixtures.is_dir():
        _step("fixtures/rag_minimal exists", False)
        return 1

    with tempfile.TemporaryDirectory(prefix="hermes_rag_e2e_") as tmp:
        tmp_path = Path(tmp)
        raw_root = tmp_path / "raw_source_files"
        ldb_root = tmp_path / "lancedb"
        raw_root.mkdir()
        ldb_root.mkdir()

        for sub in fixtures.iterdir():
            if sub.is_dir() and not sub.name.endswith(".yaml"):
                dest = raw_root / sub.name
                shutil.copytree(sub, dest)

        yaml_tpl = (fixtures / "domains_e2e.yaml").read_text(encoding="utf-8")
        yaml_path = tmp_path / "domains.yaml"
        yaml_path.write_text(
            yaml_tpl.replace("{lancedb_root}", str(ldb_root).replace("\\", "/")),
            encoding="utf-8",
        )

        env = os.environ.copy()
        env["HERMES_RAG_RAW_ROOT"] = str(raw_root)
        env["HERMES_DOMAINS_YAML"] = str(yaml_path)
        env["HERMES_RAG_SKIP_MCP_VERIFY"] = "1"
        env["HERMES_RAG_FRESH"] = "n"
        env["PYTHONPATH"] = str(REPO)

        preflight = subprocess.run(
            [
                str(PY),
                str(REPO / "scripts/rag_pipeline/ingest_preflight.py"),
                "--only",
                "academics",
                "--skip-empty",
                "--domains-yaml",
                str(yaml_path),
            ],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(REPO),
            env=env,
        )
        _step(
            "ingest_preflight academics --skip-empty",
            preflight.returncode == 0,
            f"exit={preflight.returncode}",
        )

        ingest = subprocess.run(
            [
                str(PY),
                str(REPO / "scripts/rag_pipeline/run_domains_ingest.py"),
                "--domain",
                "academics",
                "--skip-mcp-verify",
                "--domains-yaml",
                str(yaml_path),
            ],
            capture_output=True,
            text=True,
            timeout=300,
            cwd=str(REPO),
            env=env,
        )
        _step(
            "run_domains_ingest --domain academics",
            ingest.returncode == 0,
            f"exit={ingest.returncode}",
        )

        seed_ps = REPO / "windows/scripts/seed_rag_minimal_fixtures.ps1"
        if seed_ps.is_file():
            seed_dest = tmp_path / "seed_dest"
            seed_dest.mkdir()
            seed = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(seed_ps),
                    "-RepoRoot",
                    str(REPO),
                    "-DestRoot",
                    str(seed_dest),
                ],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(REPO),
            )
            has_academics = (seed_dest / "01_Academics_Beta" / "smoke.md").is_file()
            _step(
                "seed_rag_minimal_fixtures.ps1",
                seed.returncode == 0 and has_academics,
                f"exit={seed.returncode}",
            )

    print()
    if FAILURES:
        print(f"FAILURES: {FAILURES}")
        return 1
    print("ALL PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
