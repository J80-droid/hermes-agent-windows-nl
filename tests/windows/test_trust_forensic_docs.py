"""Repo docs for Trust & Forensic protocol."""
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def test_trust_protocol_doc_exists():
    assert (REPO / "docs/TRUST_FORENSIC_PROTOCOL.md").is_file()


def test_shared_advisory_template_deprecated_smoke():
    """Legacy template; sync-compat only — governance lives in VALUES + TRUST_VERIFICATION."""
    path = REPO / "docs/templates/SOUL_SHARED_ADVISORY.md"
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert "Advisory" in text or "trust" in text.lower()


def test_shared_values_template():
    text = (REPO / "docs/templates/SOUL_SHARED_VALUES.md").read_text(encoding="utf-8")
    assert "Values" in text
    assert "pleaser" in text.lower()
    assert "eigen redenering" in text.lower() or "Ontbrekende informatie" in text


def test_shared_trust_verification_template():
    text = (REPO / "docs/templates/SOUL_SHARED_TRUST_VERIFICATION.md").read_text(
        encoding="utf-8"
    )
    assert "Trust & verification" in text
    assert "search_knowledge" in text or "RAG" in text
    assert "deel 1" in text.lower() or "1/N" in text


def test_legal_forensic_block():
    text = (REPO / "docs/templates/SOUL_LEGAL_DOMAIN.md").read_text(encoding="utf-8")
    assert "Forensic & trust (legal)" in text
    assert "search_knowledge" in text
    assert "geen compact modus" in text.lower()


def test_memory_canonical_seed():
    text = (REPO / "docs/templates/MEMORY_CANONICAL_SEED.md").read_text(encoding="utf-8")
    assert "Never compress" in text
    assert "Jamel el Mourif" not in text
    assert "J." in text


def test_memory_architecture_consolidation_section():
    text = (REPO / "docs/MEMORY_ARCHITECTURE.md").read_text(encoding="utf-8")
    assert "Consolidatie bij OVER" in text
    assert "CONSOLIDATE_ROOT_MEMORIES" in text
    assert "sync_profile_memories" in text


def test_memory_architecture_e2e_step_count():
    core = (REPO / "windows/audits/MemoryArchitectureE2E.core.ps1").read_text(encoding="utf-8")
    assert core.count("/18 ") >= 18
    assert "Test-MemoryConsolidationLayout" in core
    assert "Legacy root" in core or "legacy root" in core.lower()


def test_memory_audit_common_consolidation_helpers():
    text = (REPO / "windows/scripts/MemoryAuditCommon.ps1").read_text(encoding="utf-8")
    assert "Test-MemoryConsolidationLayout" in text
    assert "HermesMemoryMergeCommon.ps1" in text
    assert "legacy-root" in text


def test_output_format_pleaser_check():
    text = (REPO / "docs/templates/SOUL_SHARED_OUTPUT_FORMAT.md").read_text(encoding="utf-8")
    assert "pleaser-taal" in text
    assert "geen compact modus" in text.lower()


def test_trust_memory_user_snapshot_script():
    script = REPO / "windows/scripts/log_trust_memory_user_snapshot.ps1"
    assert script.is_file()
    text = script.read_text(encoding="utf-8")
    assert "pleaser-behavior" in text
    assert "[trust-memory]" in text


def test_sync_trust_runtime_chain():
    bat = (REPO / "windows/SYNC_TRUST_RUNTIME.bat").read_text(encoding="utf-8")
    assert "invoke_deduplicate_memories" in bat
    assert "Invoke-MemoryTrustPostSync" in bat
    post = (REPO / "windows/POST_GIT_PULL.bat").read_text(encoding="utf-8")
    assert "SYNC_TRUST_RUNTIME" in post


def test_institutional_new_chat_notice_module():
    from tests.overlay.fork_paths import fork_repo_path

    mod = fork_repo_path(REPO, "overlay/hermes_cli/institutional_new_chat_notice.py")
    assert mod.is_file()
    text = mod.read_text(encoding="utf-8")
    assert "institutional_new_chat_required.json" in text
    assert "acknowledge_new_chat_notice" in text


def test_tui_auto_new_session_files():
    from tests.overlay.fork_paths import fork_repo_path

    notice = fork_repo_path(REPO, "overlay/ui-tui/src/lib/newChatNotice.ts")
    watch = fork_repo_path(REPO, "overlay/ui-tui/src/app/useInstitutionalNewChatAutoReset.ts")
    gateway_ready = fork_repo_path(REPO, "overlay/ui-tui/src/app/gatewayReadyNewChatNotice.ts")
    assert notice.is_file() and watch.is_file() and gateway_ready.is_file()
    watch_text = watch.read_text(encoding="utf-8")
    ready_text = gateway_ready.read_text(encoding="utf-8")
    assert "hasPendingNewChatNotice" in watch_text
    assert "clearNewChatNotice" in watch_text
    assert "gateway.ready" in ready_text
