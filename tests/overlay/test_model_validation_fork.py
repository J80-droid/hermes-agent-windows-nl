"""Fork model_validation tests (startup catalog guard)."""
from unittest.mock import patch
import pytest
from overlay.bootstrap import install
from hermes_cli.models import model_default_passes_startup_catalog_guard, model_matches_provider_catalog

@pytest.fixture(autouse=True)
def _bootstrap():
    install()


class TestStartupCatalogGuard:
    def test_nous_free_suffix_matches_manifest_entry(self):
        catalog = ["stepfun/step-3.7-flash", "anthropic/claude-sonnet-4.6"]
        assert model_matches_provider_catalog("stepfun/step-3.7-flash:free", catalog)

    def test_exact_catalog_id_still_matches(self):
        catalog = ["anthropic/claude-opus-4.8"]
        assert model_matches_provider_catalog("anthropic/claude-opus-4.8", catalog)

    def test_unrelated_model_does_not_match(self):
        catalog = ["anthropic/claude-opus-4.8"]
        assert not model_matches_provider_catalog("kimi-k2-6", catalog)

    def test_cross_vendor_bare_tail_does_not_false_positive(self):
        catalog = ["openai/claude-opus-4.8"]
        assert not model_matches_provider_catalog("anthropic/claude-opus-4.8", catalog)

    def test_startup_guard_rejects_when_catalog_nonempty_and_validate_rejects(self):
        with patch(
            "hermes_cli.models.provider_model_ids",
            return_value=["anthropic/claude-sonnet-4.6"],
        ), patch(
            "hermes_cli.models.validate_requested_model",
            return_value={"accepted": False, "persist": False, "recognized": False},
        ):
            assert not model_default_passes_startup_catalog_guard(
                "nous",
                "totally-unknown-model",
            )

    def test_startup_guard_accepts_nous_free_variant_without_live_creds(self):
        with patch(
            "hermes_cli.models.provider_model_ids",
            return_value=["stepfun/step-3.7-flash"],
        ), patch(
            "hermes_cli.models.validate_requested_model",
            return_value={"accepted": True, "persist": True, "recognized": False},
        ):
            assert model_default_passes_startup_catalog_guard(
                "nous",
                "stepfun/step-3.7-flash:free",
            )
