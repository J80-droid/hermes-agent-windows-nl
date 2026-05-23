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


def test_init_missing_domain_creates_empty_table(tmp_path, monkeypatch):
    import domains_config as dc

    spec = dc.DomainSpec(
        name="testdom",
        source_dir="99_Test",
        description="test",
        lancedb_path=str(tmp_path / "ldb"),
        mcp_name="lancedb-testdom",
        profile_name="testdom",
    )
    monkeypatch.setattr(
        maint,
        "resolve_domain_paths",
        lambda s: (tmp_path / "ldb", tmp_path / "raw", tmp_path / "prof"),
    )
    note = maint.init_missing_domain(spec, dry_run=False)
    assert "aangemaakt" in note or "aanwezig" in note
    rep = maint.inspect_domain(spec)
    assert rep.exists
    assert rep.schema_ok is True


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
