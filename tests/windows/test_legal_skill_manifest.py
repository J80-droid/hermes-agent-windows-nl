"""fork_legal_skills paths exist under skills/legal/."""

from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]


def test_fork_legal_skills_paths_exist():
    data = yaml.safe_load((REPO / "docs/domain_toolsets.yaml").read_text(encoding="utf-8"))
    legal = (data.get("profiles") or {}).get("legal") or {}
    fork_skills = legal.get("fork_legal_skills") or {}
    assert fork_skills, "fork_legal_skills ontbreekt voor legal"
    for _key, desc in fork_skills.items():
        path_part = str(desc).split(" - ")[0].strip().rstrip("/")
        if path_part.startswith("skills/"):
            rel = path_part.replace("/", "\\") if False else path_part
            full = REPO / rel
            assert full.is_dir(), f"Skill map ontbreekt: {rel}"
