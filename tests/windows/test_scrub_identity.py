"""Unit tests for identity scrub patterns (no J. false positives)."""
import re

IDENTITY_PATTERN = r"(?i)\bJamel\s+el\s+Mourif\b|\bJamel\b|\bel\s+Mourif\b"

ALLOW_PATTERNS = [
    r"miniconda3[\\/]envs[\\/]hermes-env[\\/]python\.exe",
    r"Documents[\\/]Hermes Knowledge",
    r"Documents[\\/]Obsidian Vault",
    r"AppData[\\/]Local[\\/]hermes",
    r"[\\/]Users[\\/][^\\/]+[\\/]AppData",
    r"data[\\/]lancedb[\\/]",
]


def line_allowed(line: str) -> bool:
    if not line or not line.strip():
        return True
    return any(re.search(pat, line) for pat in ALLOW_PATTERNS)


def is_leak(line: str) -> bool:
    if line_allowed(line):
        return False
    return bool(re.search(IDENTITY_PATTERN, line))


def scrub_line(line: str) -> str:
    if not is_leak(line):
        return line
    out = re.sub(r"(?i)\bJamel\s+el\s+Mourif\b", "J.", line)
    out = re.sub(r"(?i)\bJamel\b", "J.", out)
    out = re.sub(r"(?i)\bel\s+Mourif\b", "", out)
    return re.sub(r"[ \t]{2,}", " ", out).strip()


def test_scrub_full_name():
    assert scrub_line("Jamel el Mourif") == "J."


def test_scrub_does_not_match_legal_word():
    assert not re.search(IDENTITY_PATTERN, "legal domain")
    assert scrub_line("legal domain") == "legal domain"


def test_scrub_j_dot_unchanged():
    assert scrub_line("J. demands trust") == "J. demands trust"


def test_path_with_localappdata_hermes_unchanged():
    path = r"Runtime: C:\Users\jamel\AppData\Local\hermes"
    assert not is_leak(path)
    assert scrub_line(path) == path


def test_prose_jamel_scrubbed():
    line = "Contact Jamel for follow-up."
    assert is_leak(line)
    assert "Jamel" not in scrub_line(line)
    assert "J." in scrub_line(line)


def test_users_appdata_path_allowed():
    line = r"Cfg: C:\Users\jamel\AppData\Roaming\foo"
    assert not is_leak(line)
    assert scrub_line(line) == line


def test_el_mourif_scrubbed():
    assert scrub_line("el Mourif noted") == "noted"


def test_legal_domain_not_leak():
    assert not is_leak("legal domain strategy")
