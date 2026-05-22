"""Institutioneel: één canoniek setup-PS1; windows/setup_hermes_windows.ps1 blijft wrapper."""

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CANON = REPO / "scripts/windows/setup_hermes_windows.ps1"
WRAPPER = REPO / "windows/setup_hermes_windows.ps1"
POLICY = REPO / "windows/HermesSetupScriptPolicy.ps1"

FORBIDDEN_IN_WRAPPER = (
    "function Write-LogoBat",
    "function Write-MinimalLaunchBat",
    "Copy-Item -LiteralPath $PSCommandPath",
)


def test_canonical_setup_exists():
    assert CANON.is_file(), "canoniek setup ontbreekt"


def test_wrapper_exists_and_is_thin():
    assert WRAPPER.is_file()
    lines = WRAPPER.read_text(encoding="utf-8").splitlines()
    assert len(lines) <= 40, "wrapper groeit — geen volledige kopie in windows/"
    text = WRAPPER.read_text(encoding="utf-8")
    assert "@PSBoundParameters" in text
    for needle in FORBIDDEN_IN_WRAPPER:
        assert needle not in text, f"wrapper bevat canonieke logica: {needle}"


def test_canonical_has_no_self_mirror():
    text = CANON.read_text(encoding="utf-8")
    assert "Copy-Item -LiteralPath $PSCommandPath" not in text


def test_setup_policy_script_in_repo():
    assert POLICY.is_file()


def test_setup_bats_do_not_pass_batch_flags_to_ps1():
    for rel in (
        "windows/setup_hermes_windows.bat",
        "windows/SETUP_HERMES.bat",
        "scripts/windows/setup_hermes_windows.bat",
        "scripts/windows/bat-templates/setup_hermes_windows.bat.template",
    ):
        path = REPO / rel
        assert path.is_file(), rel
        text = path.read_text(encoding="utf-8")
        assert "PSARGS:--full-setup" not in text, f"{rel} gebruikt nog CMD :replace"
        assert "setup_hermes_windows.ps1\" !PSARGS!" not in text.replace("'", '"'), rel
