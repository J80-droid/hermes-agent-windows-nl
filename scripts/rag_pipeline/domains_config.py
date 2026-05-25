"""Laad domeinen uit ~/data/domains.yaml (enige bron van waarheid voor RAG-ingest)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass(frozen=True)
class DomainSpec:
    name: str
    source_dir: str
    lancedb_path: str
    profile_name: str
    mcp_name: str = ""
    description: str = ""
    ingest_env: dict[str, str] = field(default_factory=dict)
    # sidecar_or_skip (default) | whisper_when_missing
    media_policy: str = "sidecar_or_skip"
    media_ingest_env: dict[str, str] = field(default_factory=dict)
    # bestandsnaam in _PROBLEMATISCHE_BESTANDEN -> relatieve doelmap onder bronmap
    quarantine_restore: dict[str, str] = field(default_factory=dict)

    def resolved_mcp_name(self) -> str:
        return (self.mcp_name or f"lancedb-{self.name}").strip()


def _expand(path: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(path))).resolve()


def default_domains_yaml() -> Path:
    override = (os.environ.get("HERMES_DOMAINS_YAML") or "").strip()
    if override:
        return _expand(override)
    return _expand(os.path.join(os.environ.get("USERPROFILE", "~"), "data", "domains.yaml"))


def default_raw_root() -> Path:
    override = (os.environ.get("HERMES_RAG_RAW_ROOT") or "").strip()
    if override:
        return _expand(override)
    return _expand(os.path.join(os.environ.get("USERPROFILE", "~"), "data", "raw_source_files"))


def load_domains(path: Path | None = None) -> list[DomainSpec]:
    yaml_path = path or default_domains_yaml()
    if not yaml_path.is_file():
        raise FileNotFoundError(f"domains.yaml niet gevonden: {yaml_path}")

    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Ongeldige domains.yaml: {yaml_path}")

    out: list[DomainSpec] = []

    core = data.get("core_domain")
    if isinstance(core, dict) and core.get("name"):
        out.append(_spec_from_entry(core, ingest_env=core.get("ingest_env") or {}))

    for entry in data.get("domains") or []:
        if isinstance(entry, dict) and entry.get("name"):
            out.append(_spec_from_entry(entry, ingest_env=entry.get("ingest_env") or {}))

    if not out:
        raise ValueError(f"Geen domeinen in {yaml_path}")

    names = [d.name for d in out]
    if len(names) != len(set(names)):
        raise ValueError(f"Dubbele domeinnamen in {yaml_path}")

    return out


def _string_dict(raw: object) -> dict[str, str]:
    out: dict[str, str] = {}
    if isinstance(raw, dict):
        for k, v in raw.items():
            if k and v is not None:
                out[str(k)] = str(v)
    return out


def _spec_from_entry(entry: dict, *, ingest_env: dict) -> DomainSpec:
    env = _string_dict(ingest_env)
    name = str(entry["name"]).strip()
    return DomainSpec(
        name=name,
        source_dir=str(entry.get("source_dir", "")).strip(),
        lancedb_path=str(entry.get("lancedb_path", "")).strip(),
        profile_name=str(entry.get("profile_name", name)).strip(),
        mcp_name=str(entry.get("mcp_name", f"lancedb-{name}")).strip(),
        description=str(entry.get("description", "")).strip(),
        ingest_env=env,
        media_policy=str(entry.get("media_policy", "sidecar_or_skip")).strip(),
        media_ingest_env=_string_dict(entry.get("media_ingest_env")),
        quarantine_restore=_string_dict(entry.get("quarantine_restore")),
    )


def default_lancedb_path_for_domain(domain_name: str) -> Path:
    """Recommended absolute LanceDB path for a domain (Windows: LOCALAPPDATA\\hermes\\VectorStore)."""
    from lancedb_storage import resolve_lancedb_path

    return Path(resolve_lancedb_path(domain=domain_name))


def resolve_domain_paths(spec: DomainSpec, *, raw_root: Path | None = None) -> tuple[Path, Path, Path]:
    root = raw_root or default_raw_root()
    raw_path = str(spec.lancedb_path or "").strip()
    if raw_path:
        ldb = _expand(raw_path)
    else:
        ldb = default_lancedb_path_for_domain(spec.name)
    raw = root / spec.source_dir if spec.source_dir else root
    profile = Path(
        os.path.expandvars(
            os.path.join(
                os.environ.get("LOCALAPPDATA", ""),
                "hermes",
                "profiles",
                spec.profile_name,
            )
        )
    )
    return ldb, raw.resolve(), profile.resolve()


def get_domain(name: str, path: Path | None = None) -> DomainSpec:
    key = name.strip().lower()
    for spec in load_domains(path):
        if spec.name.lower() == key:
            return spec
    known = ", ".join(d.name for d in load_domains(path))
    raise KeyError(f"Domein '{name}' niet in domains.yaml. Bekend: {known}")
