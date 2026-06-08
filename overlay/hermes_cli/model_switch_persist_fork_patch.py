"""Route global model switches through persist_model_runtime (root + auth sync)."""
from __future__ import annotations

import contextvars
import logging
from contextlib import contextmanager
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_APPLIED = False
_model_save_batch: contextvars.ContextVar[Optional[Dict[str, Any]]] = contextvars.ContextVar(
    "hermes_model_save_batch", default=None
)


def persist_global_model_switch(
    *,
    provider: str,
    default_model: str,
    base_url: str = "",
    api_mode: Optional[str] = None,
) -> None:
    from hermes_cli.model_runtime_config import persist_model_runtime

    provider = str(provider or "").strip()
    default_model = str(default_model or "").strip()
    if not provider or not default_model:
        raise ValueError("provider and default_model are required")

    extra = {"api_mode": api_mode} if api_mode else None
    persist_model_runtime(
        provider,
        default_model=default_model,
        inference_base_url=str(base_url or "").strip(),
        sync_auth=True,
        extra_model_fields=extra,
    )


def _flush_model_save_batch(batch: Dict[str, Any]) -> None:
    from hermes_cli.config import load_config
    from hermes_cli.model_runtime_config import _model_section_from_config

    cfg = load_config()
    model_cfg = dict(_model_section_from_config(cfg))
    if "default" in batch:
        model_cfg["default"] = batch["default"]
    if "provider" in batch:
        model_cfg["provider"] = batch["provider"]
    provider = str(model_cfg.get("provider") or "").strip()
    default = str(model_cfg.get("default") or model_cfg.get("model") or "").strip()
    if not provider or not default:
        raise ValueError("incomplete model batch for persist")
    persist_global_model_switch(
        provider=provider,
        default_model=default,
        base_url=str(model_cfg.get("base_url") or ""),
        api_mode=str(model_cfg.get("api_mode") or "") or None,
    )


@contextmanager
def _coalesce_model_config_saves():
    token = _model_save_batch.set({})
    try:
        yield
    finally:
        batch = _model_save_batch.get() or {}
        _model_save_batch.reset(token)
        if batch:
            try:
                _flush_model_save_batch(batch)
            except Exception:
                logger.exception("persist_model_runtime failed after batched save_config_value")
                raise


def apply_model_switch_persist_fork_patch() -> None:
    global _APPLIED
    if _APPLIED:
        return

    try:
        import cli as cli_mod
    except ImportError:
        return

    if getattr(cli_mod, "_fork_model_persist_patch_applied", False):
        _APPLIED = True
        return

    _orig_save = cli_mod.save_config_value

    def save_config_value(key_path: str, value: Any) -> bool:
        batch = _model_save_batch.get()
        if batch is not None and key_path in ("model.default", "model.provider"):
            batch[key_path.split(".", 1)[1]] = value
            return True
        return _orig_save(key_path, value)

    cli_mod.save_config_value = save_config_value  # type: ignore[assignment]

    cls = cli_mod.HermesCLI
    _orig_apply = cls._apply_model_switch_result
    _orig_handle = cls._handle_model_switch

    def _apply_model_switch_result(self, result, persist_global: bool) -> None:
        if persist_global and getattr(result, "success", False):
            with _coalesce_model_config_saves():
                _orig_apply(self, result, True)
            return
        _orig_apply(self, result, persist_global)

    def _handle_model_switch(self, cmd_original: str) -> None:
        from hermes_cli.model_switch import parse_model_flags

        parts = cmd_original.split(None, 1)
        raw_args = parts[1].strip() if len(parts) > 1 else ""
        _, _, persist_global, _ = parse_model_flags(raw_args)
        if persist_global:
            with _coalesce_model_config_saves():
                _orig_handle(self, cmd_original)
            return
        _orig_handle(self, cmd_original)

    cls._apply_model_switch_result = _apply_model_switch_result  # type: ignore[method-assign]
    cls._handle_model_switch = _handle_model_switch  # type: ignore[method-assign]
    cli_mod._fork_model_persist_patch_applied = True
    _APPLIED = True
