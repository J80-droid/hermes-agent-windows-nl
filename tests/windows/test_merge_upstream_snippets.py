"""Merge upstream IDE prompt: git-diff snippets for -PromptOnly preview."""

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
MERGE_PS1 = REPO / "windows" / "merge_upstream_fork.ps1"


def test_merge_fork_exports_snippet_helpers():
    text = MERGE_PS1.read_text(encoding="utf-8")
    for name in (
        "Get-MergeTreeRawOutput",
        "Get-ConflictSnippetFromGitDiff",
        "Get-ConflictSnippetFromMergeTree",
        "Get-ConflictSnippetForPrompt",
    ):
        assert f"function {name}" in text, f"ontbreekt: {name}"


def test_new_ide_merge_prompt_accepts_merge_tree_output():
    text = MERGE_PS1.read_text(encoding="utf-8")
    assert "MergeTreeOutput" in text
    assert "PreferGitPreview" in text
    assert "Get-ConflictSnippetForPrompt" in text


def test_prompt_only_sets_git_preview_flag():
    text = MERGE_PS1.read_text(encoding="utf-8")
    assert "HermesMergePreferGitPreview" in text
    assert "HermesMergeTreeRaw" in text


def test_git_diff_snippet_returns_content():
    """Smoke: Get-ConflictSnippetFromGitDiff levert diff-regels voor bekend bestand."""
    import subprocess

    ps = f"""
. '{MERGE_PS1}'
$repo = '{REPO.as_posix()}'
$s = Get-ConflictSnippetFromGitDiff -Path 'memory-bank/activeContext.md' -RepoRoot $repo -MaxLines 8
if ($s -match 'geen diff') {{ exit 2 }}
if ($s.Length -lt 3) {{ exit 3 }}
exit 0
"""
    proc = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_lancedb_maintenance_bat_exists():
    assert (REPO / "windows" / "LANCEDB_MAINTENANCE.bat").is_file()
    bat = (REPO / "windows" / "LANCEDB_MAINTENANCE.bat").read_text(encoding="utf-8")
    assert "run_lancedb_maintenance.ps1" in bat
