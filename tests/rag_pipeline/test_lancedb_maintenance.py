"""Unit tests for lancedb_maintenance helpers (no live user DB required)."""

from pathlib import Path

import lancedb_maintenance as maint

REPO = Path(__file__).resolve().parents[2]


def test_schema_has_id_true():
    import pyarrow as pa

    schema = pa.schema([("id", pa.string()), ("text", pa.string())])
    assert maint._schema_has_id(schema) is True


def test_schema_has_id_false():
    import pyarrow as pa

    schema = pa.schema([("text", pa.string())])
    assert maint._schema_has_id(schema) is False


def test_format_bytes():
    assert "KB" in maint._format_bytes(2048)


def test_maintenance_module_paths():
    assert (REPO / "scripts" / "rag_pipeline" / "lancedb_maintenance.py").is_file()
    assert (REPO / "windows" / "LANCEDB_MAINTENANCE.bat").is_file()


def test_lancedb_bat_forwards_list_arg():
    import subprocess

    proc = subprocess.run(
        ["cmd", "/c", "windows\\LANCEDB_MAINTENANCE.bat", "--list"],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert "Domeinen:" in (proc.stdout or "")
