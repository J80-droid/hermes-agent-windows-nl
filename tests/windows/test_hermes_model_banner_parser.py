"""Guard: model banner must not use catastrophic (?ms).* regex on config.yaml."""
from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
HOME_PS1 = REPO / "windows/scripts/HermesHomeCommon.ps1"


def test_banner_does_not_use_catastrophic_model_regex():
    text = HOME_PS1.read_text(encoding="utf-8")
    assert "(?ms)^model:" not in text
    assert "Get-HermesModelFieldsFromConfigYaml" in text


def _parse_model_fields_line_scan(config_text: str) -> tuple[str, str]:
    provider = ""
    default = ""
    in_model = False
    for line in config_text.splitlines():
        if line.strip().startswith("#"):
            continue
        if re.match(r"^model:\s*$", line):
            in_model = True
            continue
        if in_model:
            if re.match(r"^[^\s#]", line):
                in_model = False
                continue
            m = re.match(r"^\s+provider:\s*(\S+)", line)
            if m:
                provider = m.group(1)
            m = re.match(r"^\s+default:\s*(\S+)", line)
            if m:
                default = m.group(1)
    return provider, default


def test_line_parser_finds_model_fields_on_fixture():
    fixture = REPO / "tests/windows/fixtures/minimal_model_config.yaml"
    if not fixture.is_file():
        sample = "model:\n  default: test/model\n  provider: test\n"
        provider, default = _parse_model_fields_line_scan(sample)
        assert provider == "test"
        assert default == "test/model"
        return
    text = fixture.read_text(encoding="utf-8")
    provider, default = _parse_model_fields_line_scan(text)
    assert provider
    assert default
