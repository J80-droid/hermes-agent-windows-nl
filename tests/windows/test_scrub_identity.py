"""Unit tests for identity scrub patterns (no J. false positives)."""
import re

IDENTITY_PATTERN = r"(?i)\bJamel\s+el\s+Mourif\b|\bJamel\b|\bel\s+Mourif\b"


def scrub(text: str) -> str:
    out = re.sub(r"(?i)\bJamel\s+el\s+Mourif\b", "J.", text)
    out = re.sub(r"(?i)\bJamel\b", "J.", out)
    out = re.sub(r"(?i)\bel\s+Mourif\b", "", out)
    return out


def test_scrub_full_name():
    assert scrub("Jamel el Mourif") == "J."


def test_scrub_does_not_match_legal_word():
    assert not re.search(IDENTITY_PATTERN, "legal domain")
    assert scrub("legal domain") == "legal domain"


def test_scrub_j_dot_unchanged():
    assert scrub("J. demands trust") == "J. demands trust"
