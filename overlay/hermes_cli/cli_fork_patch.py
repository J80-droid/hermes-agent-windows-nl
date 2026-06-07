"""Fork CLI status-bar integration (runtime patch; Tier A cli.py unchanged)."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Resolved from cli module at patch time (same symbols as upstream cli.py).
format_duration_compact = None  # type: ignore


class CliForkStatusBarMixin:
        def _format_prompt_elapsed(
            self,
            prompt_start_time: Optional[float],
            prompt_duration: float,
            live: bool = False,
        ) -> str:
            """Format per-prompt elapsed for the status bar (fork module; emoji off by default)."""
            from hermes_cli.status_bar_prompt_elapsed import format_prompt_elapsed_status_bar

            return format_prompt_elapsed_status_bar(
                prompt_start_time,
                prompt_duration,
                live=live,
                show_emoji=getattr(self, "_show_prompt_timer_emoji", False),
            )

        def _get_status_bar_snapshot(self) -> Dict[str, Any]:
            # Prefer the agent's model name â€” it updates on fallback.
            # self.model reflects the originally configured model and never
            # changes mid-session, so the TUI would show a stale name after
            # _try_activate_fallback() switches provider/model.
            agent = getattr(self, "agent", None)
            model_name = (getattr(agent, "model", None) or self.model or "unknown")
            model_short = model_name.split("/")[-1] if "/" in model_name else model_name
            if model_short.endswith(".gguf"):
                model_short = model_short[:-5]
            if len(model_short) > 26:
                model_short = f"{model_short[:23]}..."

            elapsed_seconds = max(0.0, (datetime.now() - self.session_start).total_seconds())
            snapshot = {
                "model_name": model_name,
                "model_short": model_short,
                "duration": format_duration_compact(elapsed_seconds),
                "prompt_elapsed": self._format_prompt_elapsed(
                    getattr(self, "_prompt_start_time", None),
                    getattr(self, "_prompt_duration", 0.0),
                    live=getattr(self, "_prompt_start_time", None) is not None,
                ),
                "context_tokens": 0,
                "context_length": None,
                "context_percent": None,
                "session_input_tokens": 0,
                "session_output_tokens": 0,
                "session_cache_read_tokens": 0,
                "session_cache_write_tokens": 0,
                "session_prompt_tokens": 0,
                "session_completion_tokens": 0,
                "session_total_tokens": 0,
                "session_api_calls": 0,
                "compressions": 0,
                "active_background_tasks": 0,
                "active_background_processes": 0,
            }

            # Count live /background tasks. The dict entry is removed in the
            # task thread's finally block, so len() reflects truly-running tasks.
            # len() on a CPython dict is atomic; safe to read without a lock.
            try:
                bg_tasks = getattr(self, "_background_tasks", None)
                if bg_tasks:
                    snapshot["active_background_tasks"] = len(bg_tasks)
            except Exception:
                pass

            # Count live background terminal processes (terminal tool background
            # sessions tracked by tools.process_registry). Cheap O(1) read.
            try:
                from tools.process_registry import process_registry
                snapshot["active_background_processes"] = process_registry.count_running()
            except Exception:
                pass


            if not agent:
                snapshot["usage"] = {"calls": 0}
                return snapshot

            snapshot["session_input_tokens"] = getattr(agent, "session_input_tokens", 0) or 0
            snapshot["session_output_tokens"] = getattr(agent, "session_output_tokens", 0) or 0
            snapshot["session_cache_read_tokens"] = getattr(agent, "session_cache_read_tokens", 0) or 0
            snapshot["session_cache_write_tokens"] = getattr(agent, "session_cache_write_tokens", 0) or 0
            snapshot["session_prompt_tokens"] = getattr(agent, "session_prompt_tokens", 0) or 0
            snapshot["session_completion_tokens"] = getattr(agent, "session_completion_tokens", 0) or 0
            snapshot["session_total_tokens"] = getattr(agent, "session_total_tokens", 0) or 0
            snapshot["session_api_calls"] = getattr(agent, "session_api_calls", 0) or 0

            compressor = getattr(agent, "context_compressor", None)
            if compressor:
                # last_prompt_tokens is parked at the -1 sentinel right after a
                # compression, until the next real API call reports a prompt count
                # (awaiting_real_usage_after_compression). The status bar must not
                # render that sentinel verbatim â€” it produced "-1/200K" / "-1%".
                # Clamp it to 0 so the one transitional turn reads as empty context.
                context_tokens = getattr(compressor, "last_prompt_tokens", 0) or 0
                if context_tokens < 0:
                    context_tokens = 0
                context_length = getattr(compressor, "context_length", 0) or 0
                if context_length < 0:
                    context_length = 0
                snapshot["context_tokens"] = context_tokens
                snapshot["context_length"] = context_length or None
                snapshot["compressions"] = getattr(compressor, "compression_count", 0) or 0
                if context_length:
                    snapshot["context_percent"] = max(0, min(100, round((context_tokens / context_length) * 100)))

            try:
                from hermes_cli.usage_snapshot import build_session_usage_snapshot

                snapshot["usage"] = build_session_usage_snapshot(agent) if agent else {"calls": 0}
            except Exception:
                snapshot["usage"] = {"calls": snapshot.get("session_api_calls", 0) or 0}

            try:
                from hermes_cli.status_bar_throughput import live_throughput_snapshot

                snapshot.update(
                    live_throughput_snapshot(
                        agent,
                        cli_started_at=self._stream_tps_started_at,
                        cli_tokens_est=self._stream_tps_tokens_est,
                        cli_last_call_tps=self._last_call_tps,
                    )
                )
            except Exception:
                snapshot["stream_tps"] = None
                snapshot["last_call_tps"] = None

            snapshot["jatevo_quota_label"] = None
            snapshot["jatevo_quota_percent"] = None
            snapshot["venice_quota_label"] = None
            snapshot["venice_quota_percent"] = None
            provider = getattr(agent, "provider", None) or getattr(self, "provider", None)
            base_url = getattr(agent, "base_url", None) or getattr(self, "base_url", None)
            api_key = getattr(agent, "api_key", None) or getattr(self, "api_key", None)
            cache_bucket = str(getattr(self, "session_id", "") or "cli")
            try:
                from agent.jatevo_usage import is_jatevo_runtime, resolve_status_bar_jatevo_quota
                from agent.venice_usage import is_venice_runtime, resolve_status_bar_venice_quota

                if is_jatevo_runtime(provider, base_url):
                    jatevo_quota = resolve_status_bar_jatevo_quota(
                        provider=provider,
                        base_url=base_url,
                        api_key=api_key,
                        cache_bucket=cache_bucket,
                    )
                    if jatevo_quota:
                        snapshot["jatevo_quota_label"], snapshot["jatevo_quota_percent"] = jatevo_quota
                elif is_venice_runtime(provider, base_url):
                    venice_quota = resolve_status_bar_venice_quota(
                        provider=provider,
                        base_url=base_url,
                        api_key=api_key,
                        cache_bucket=cache_bucket,
                    )
                    if venice_quota:
                        snapshot["venice_quota_label"], snapshot["venice_quota_percent"] = venice_quota
            except Exception:
                pass

            return snapshot

        def _status_bar_cost_format_width(self, terminal_width: int) -> int:
            if terminal_width < 76:
                return 40
            return max(40, terminal_width - 32)

        def _resolve_status_bar_cost_label(self, snapshot: Dict[str, Any], terminal_width: int) -> Optional[str]:
            if terminal_width < 52 or not getattr(self, "_show_cost", True):
                return None
            try:
                from hermes_cli.status_bar_cost import resolve_status_bar_cost_label

                usage = snapshot.get("usage") or {"calls": 0}
                return resolve_status_bar_cost_label(
                    usage,
                    show_cost=True,
                    cost_bar_mode=getattr(self, "_cost_bar_mode", "rich"),
                    width=self._status_bar_cost_format_width(terminal_width),
                )
            except Exception:
                return None

        def _append_status_bar_cost_fragments(
            self,
            frags: list,
            snapshot: Dict[str, Any],
            terminal_width: int,
            *,
            separator: str = " â”‚ ",
        ) -> None:
            label = self._resolve_status_bar_cost_label(snapshot, terminal_width)
            if not label:
                return
            frags.extend([
                ("class:status-bar-dim", separator),
                ("class:status-bar-cost", label),
            ])

        def _append_status_bar_cost_text_part(
            self,
            parts: list,
            snapshot: Dict[str, Any],
            terminal_width: int,
        ) -> None:
            label = self._resolve_status_bar_cost_label(snapshot, terminal_width)
            if label:
                parts.append(label)

        def _resolve_status_bar_throughput_label(
            self, snapshot: Dict[str, Any], terminal_width: int
        ) -> Optional[str]:
            try:
                from hermes_cli.status_bar_throughput import resolve_status_bar_throughput_label

                return resolve_status_bar_throughput_label(
                    snapshot,
                    show_tps=getattr(self, "_show_status_bar_tps", True),
                    width=terminal_width,
                )
            except Exception:
                return None

        def _append_status_bar_throughput_fragments(
            self,
            frags: list,
            snapshot: Dict[str, Any],
            terminal_width: int,
            *,
            separator: str = " â”‚ ",
        ) -> None:
            label = self._resolve_status_bar_throughput_label(snapshot, terminal_width)
            if not label:
                return
            frags.extend([
                ("class:status-bar-dim", separator),
                ("class:status-bar-tps", label),
            ])

        def _append_status_bar_throughput_text_part(
            self,
            parts: list,
            snapshot: Dict[str, Any],
            terminal_width: int,
        ) -> None:
            label = self._resolve_status_bar_throughput_label(snapshot, terminal_width)
            if label:
                parts.append(label)

        def _append_status_bar_jatevo_quota_text_part(
            self,
            parts: list,
            snapshot: Dict[str, Any],
        ) -> None:
            label = snapshot.get("jatevo_quota_label")
            if label:
                parts.append(label)

        def _append_status_bar_jatevo_quota_fragments(
            self,
            frags: list,
            snapshot: Dict[str, Any],
            *,
            separator: str = " â”‚ ",
        ) -> None:
            label = snapshot.get("jatevo_quota_label")
            if not label:
                return
            percent = snapshot.get("jatevo_quota_percent")
            frags.extend([
                ("class:status-bar-dim", separator),
                (self._status_bar_context_style(percent), label),
            ])

        def _append_status_bar_provider_quota_text_part(
            self,
            parts: list,
            snapshot: Dict[str, Any],
        ) -> None:
            self._append_status_bar_jatevo_quota_text_part(parts, snapshot)
            label = snapshot.get("venice_quota_label")
            if label:
                parts.append(label)

        def _append_status_bar_provider_quota_fragments(
            self,
            frags: list,
            snapshot: Dict[str, Any],
            *,
            separator: str = " â”‚ ",
        ) -> None:
            self._append_status_bar_jatevo_quota_fragments(frags, snapshot, separator=separator)
            label = snapshot.get("venice_quota_label")
            if not label:
                return
            percent = snapshot.get("venice_quota_percent")
            frags.extend([
                ("class:status-bar-dim", separator),
                (self._status_bar_context_style(percent), label),
            ])

        def _pack_status_bar_fragment_rows(self, header_frags, metric_frags, width: int):
            """Lay out status fragments on one or two rows (max ``STATUS_BAR_MAX_LINES``)."""
            from hermes_cli.status_bar_layout import (
                fragments_plain_text,
                should_use_status_bar_second_line,
            )

            width = max(1, int(width or 1))
            combined = list(header_frags) + list(metric_frags)
            metrics_plain = fragments_plain_text(metric_frags).strip()
            if not metrics_plain:
                self._status_bar_layout_lines = 1
                total_width = sum(self._status_bar_display_width(text) for _, text in combined)
                if total_width > width:
                    plain = fragments_plain_text(combined)
                    return [("class:status-bar", self._trim_status_bar_text(plain, width))]
                return combined

            line1_text = fragments_plain_text(header_frags)
            if not should_use_status_bar_second_line(
                line1_width=width,
                line1_text=line1_text,
                metrics_text=metrics_plain,
            ):
                self._status_bar_layout_lines = 1
                total_width = sum(self._status_bar_display_width(text) for _, text in combined)
                if total_width > width:
                    plain = fragments_plain_text(combined)
                    return [("class:status-bar", self._trim_status_bar_text(plain, width))]
                return combined

            line1_trim = self._trim_status_bar_text(line1_text, width)
            line2_trim = self._trim_status_bar_text(metrics_plain, width)
            self._status_bar_layout_lines = 2
            if line1_trim != line1_text or line2_trim != metrics_plain:
                return [("class:status-bar", f" {line1_trim}\n {line2_trim} ")]
            return list(header_frags) + [("class:status-bar", "\n")] + list(metric_frags)

        def _build_status_bar_text(self, width: Optional[int] = None) -> str:
            """Return a compact one-line session status string for the TUI footer."""
            try:
                snapshot = self._get_status_bar_snapshot()
                if width is None:
                    width = self._get_tui_terminal_width()
                percent = snapshot["context_percent"]
                percent_label = f"{percent}%" if percent is not None else "--"
                duration_label = snapshot["duration"]

                yolo_active = self._is_session_yolo_active()
                if width < 52:
                    text = f"âš• {snapshot['model_short']}"
                    if snapshot.get("jatevo_quota_label"):
                        text += f" Â· {snapshot['jatevo_quota_label']}"
                    if snapshot.get("venice_quota_label"):
                        text += f" Â· {snapshot['venice_quota_label']}"
                    text += f" Â· {duration_label}"
                    parts_narrow = []
                    self._append_pending_queue_status_part(parts_narrow)
                    if parts_narrow:
                        text += f" Â· {parts_narrow[0]}"
                    if yolo_active:
                        text += " Â· âš  YOLO"
                    return self._trim_status_bar_text(text, width)
                if width < 76:
                    parts = [f"âš• {snapshot['model_short']}"]
                    self._append_status_bar_provider_quota_text_part(parts, snapshot)
                    parts.append(percent_label)
                    compressions = snapshot.get("compressions", 0)
                    if compressions:
                        parts.append(f"ðŸ—œï¸� {compressions}")
                    bg_count = snapshot.get("active_background_tasks", 0)
                    if bg_count:
                        parts.append(f"â–¶ {bg_count}")
                    bg_proc_count = snapshot.get("active_background_processes", 0)
                    if bg_proc_count:
                        parts.append(f"âš™ {bg_proc_count}")
                    parts.append(duration_label)
                    self._append_status_bar_cost_text_part(parts, snapshot, width)
                    self._append_pending_queue_status_part(parts)
                    if yolo_active:
                        parts.append("âš  YOLO")
                    return self._trim_status_bar_text(" Â· ".join(parts), width)

                if snapshot["context_length"]:
                    ctx_total = _format_context_length(snapshot["context_length"])
                    ctx_used = format_token_count_compact(snapshot["context_tokens"])
                    context_label = f"{ctx_used}/{ctx_total}"
                else:
                    context_label = "ctx --"

                compressions = snapshot.get("compressions", 0)
                parts = [f"âš• {snapshot['model_short']}"]
                self._append_status_bar_provider_quota_text_part(parts, snapshot)
                parts.extend([context_label, percent_label])
                if compressions:
                    parts.append(f"ðŸ—œï¸� {compressions}")
                bg_count = snapshot.get("active_background_tasks", 0)
                if bg_count:
                    parts.append(f"â–¶ {bg_count}")
                bg_proc_count = snapshot.get("active_background_processes", 0)
                if bg_proc_count:
                    parts.append(f"âš™ {bg_proc_count}")
                parts.append(duration_label)
                prompt_elapsed = snapshot.get("prompt_elapsed")
                if prompt_elapsed:
                    parts.append(prompt_elapsed)
                self._append_status_bar_cost_text_part(parts, snapshot, width)
                self._append_status_bar_throughput_text_part(parts, snapshot, width)
                self._append_pending_queue_status_part(parts)
                if yolo_active:
                    parts.append("âš  YOLO")
                return self._trim_status_bar_text(" â”‚ ".join(parts), width)
            except Exception:
                return f"âš• {self.model if getattr(self, 'model', None) else 'Hermes'}"

        def _get_status_bar_fragments(self):
            if not self._status_bar_visible or getattr(self, '_model_picker_state', None):
                return []
            try:
                self._status_bar_layout_lines = 1
                snapshot = self._get_status_bar_snapshot()
                # Use prompt_toolkit's own terminal width when running inside the
                # TUI â€” shutil.get_terminal_size() can return stale or fallback
                # values (especially on SSH) that differ from what prompt_toolkit
                # actually renders, causing the fragments to overflow to a second
                # line and produce duplicated status bar rows over long sessions.
                width = self._get_tui_terminal_width()
                duration_label = snapshot["duration"]
                yolo_active = self._is_session_yolo_active()

                if width < 52:
                    frags = [
                        ("class:status-bar", " âš• "),
                        ("class:status-bar-strong", snapshot["model_short"]),
                    ]
                    self._append_status_bar_provider_quota_fragments(
                        frags, snapshot, separator=" Â· "
                    )
                    frags.extend([
                        ("class:status-bar-dim", " Â· "),
                        ("class:status-bar-dim", duration_label),
                    ])
                    self._append_pending_queue_status_fragments(frags, separator=" Â· ")
                    if yolo_active:
                        frags.append(("class:status-bar-dim", " Â· "))
                        frags.append(("class:status-bar-yolo", "âš  YOLO"))
                    frags.append(("class:status-bar", " "))
                else:
                    percent = snapshot["context_percent"]
                    percent_label = f"{percent}%" if percent is not None else "--"
                    if width < 76:
                        compressions = snapshot.get("compressions", 0)
                        bg_count = snapshot.get("active_background_tasks", 0)
                        bg_proc_count = snapshot.get("active_background_processes", 0)
                        frags = [
                            ("class:status-bar", " âš• "),
                            ("class:status-bar-strong", snapshot["model_short"]),
                        ]
                        self._append_status_bar_provider_quota_fragments(
                            frags, snapshot, separator=" Â· "
                        )
                        frags.extend([
                            ("class:status-bar-dim", " Â· "),
                            (self._status_bar_context_style(percent), percent_label),
                        ])
                        if compressions:
                            frags.append(("class:status-bar-dim", " Â· "))
                            frags.append((self._compression_count_style(compressions), f"ðŸ—œï¸� {compressions}"))
                        if bg_count:
                            frags.append(("class:status-bar-dim", " Â· "))
                            frags.append(("class:status-bar-strong", f"â–¶ {bg_count}"))
                        if bg_proc_count:
                            frags.append(("class:status-bar-dim", " Â· "))
                            frags.append(("class:status-bar-strong", f"âš™ {bg_proc_count}"))
                        frags.extend([
                            ("class:status-bar-dim", " Â· "),
                            ("class:status-bar-dim", duration_label),
                        ])
                        self._append_status_bar_cost_fragments(
                            frags, snapshot, width, separator=" Â· "
                        )
                        self._append_status_bar_throughput_fragments(
                            frags, snapshot, width, separator=" Â· "
                        )
                        self._append_pending_queue_status_fragments(frags, separator=" Â· ")
                        if yolo_active:
                            frags.append(("class:status-bar-dim", " Â· "))
                            frags.append(("class:status-bar-yolo", "âš  YOLO"))
                        frags.append(("class:status-bar", " "))
                    else:
                        if snapshot["context_length"]:
                            ctx_total = _format_context_length(snapshot["context_length"])
                            ctx_used = format_token_count_compact(snapshot["context_tokens"])
                            context_label = f"{ctx_used}/{ctx_total}"
                        else:
                            context_label = "ctx --"

                        bar_style = self._status_bar_context_style(percent)
                        compressions = snapshot.get("compressions", 0)
                        bg_count = snapshot.get("active_background_tasks", 0)
                        bg_proc_count = snapshot.get("active_background_processes", 0)
                        header_frags = [
                            ("class:status-bar", " âš• "),
                            ("class:status-bar-strong", snapshot["model_short"]),
                        ]
                        self._append_status_bar_provider_quota_fragments(
                            header_frags, snapshot, separator=" â”‚ "
                        )
                        metric_frags = [
                            ("class:status-bar-dim", " â”‚ "),
                            ("class:status-bar-dim", context_label),
                            ("class:status-bar-dim", " â”‚ "),
                            (bar_style, self._build_context_bar(percent)),
                            ("class:status-bar-dim", " "),
                            (bar_style, percent_label),
                        ]
                        if compressions:
                            metric_frags.append(("class:status-bar-dim", " â”‚ "))
                            metric_frags.append((self._compression_count_style(compressions), f"ðŸ—œï¸� {compressions}"))
                        if bg_count:
                            metric_frags.append(("class:status-bar-dim", " â”‚ "))
                            metric_frags.append(("class:status-bar-strong", f"â–¶ {bg_count}"))
                        if bg_proc_count:
                            metric_frags.append(("class:status-bar-dim", " â”‚ "))
                            metric_frags.append(("class:status-bar-strong", f"âš™ {bg_proc_count}"))
                        metric_frags.extend([
                            ("class:status-bar-dim", " â”‚ "),
                            ("class:status-bar-dim", duration_label),
                        ])
                        # Per-prompt elapsed timer (live or frozen) before cost segment
                        prompt_elapsed = snapshot.get("prompt_elapsed")
                        if prompt_elapsed:
                            metric_frags.append(("class:status-bar-dim", " â”‚ "))
                            metric_frags.append(("class:status-bar-dim", prompt_elapsed))
                        self._append_status_bar_cost_fragments(metric_frags, snapshot, width)
                        self._append_status_bar_throughput_fragments(metric_frags, snapshot, width)
                        self._append_pending_queue_status_fragments(metric_frags, separator=" â”‚ ")
                        if yolo_active:
                            metric_frags.append(("class:status-bar-dim", " â”‚ "))
                            metric_frags.append(("class:status-bar-yolo", "âš  YOLO"))
                        metric_frags.append(("class:status-bar", " "))
                        return self._pack_status_bar_fragment_rows(header_frags, metric_frags, width)

                total_width = sum(self._status_bar_display_width(text) for _, text in frags)
                if total_width > width:
                    plain_text = "".join(text for _, text in frags)
                    trimmed = self._trim_status_bar_text(plain_text, width)
                    return [("class:status-bar", trimmed)]
                return frags
            except Exception:
                return [("class:status-bar", f" {self._build_status_bar_text()} ")]

PATCH_METHOD_NAMES = ('_format_prompt_elapsed', '_get_status_bar_snapshot', '_status_bar_cost_format_width', '_resolve_status_bar_cost_label', '_append_status_bar_cost_fragments', '_append_status_bar_cost_text_part', '_resolve_status_bar_throughput_label', '_append_status_bar_throughput_fragments', '_append_status_bar_throughput_text_part', '_append_status_bar_jatevo_quota_text_part', '_append_status_bar_jatevo_quota_fragments', '_append_status_bar_provider_quota_text_part', '_append_status_bar_provider_quota_fragments', '_pack_status_bar_fragment_rows', '_build_status_bar_text', '_get_status_bar_fragments')

def apply_fork_display_attrs(cli_self: Any) -> None:
    # Fork display flags from config (no Tier A cli.py edit).
    try:
        import cli as cli_mod
    except ImportError:
        return
    cfg = getattr(cli_mod, "CLI_CONFIG", None) or {}
    _display = cfg.get("display") or {}
    is_truthy = getattr(cli_mod, "is_truthy_value", lambda v: bool(v))
    cli_self._show_cost = _display.get("show_cost", True) is not False
    cli_self._show_status_bar_tps = _display.get("show_status_bar_tps", True) is not False
    cli_self._show_prompt_timer_emoji = is_truthy(
        _display.get("show_prompt_timer_emoji", False)
    )
    _cost_mode = str(_display.get("cost_bar_mode") or "rich").strip().lower()
    cli_self._cost_bar_mode = _cost_mode if _cost_mode in {"rich", "minimal"} else "rich"
    if not hasattr(cli_self, "_status_bar_layout_lines"):
        cli_self._status_bar_layout_lines = 1


def apply_cli_fork_patch() -> None:
    global format_duration_compact
    import cli as cli_mod
    import overlay.hermes_cli.cli_fork_patch as patch_mod
    from hermes_cli.banner import _format_context_length

    format_duration_compact = cli_mod.format_duration_compact
    patch_mod.format_duration_compact = cli_mod.format_duration_compact
    patch_mod.format_token_count_compact = cli_mod.format_token_count_compact
    patch_mod._format_context_length = _format_context_length

    cls = cli_mod.HermesCLI
    if getattr(cls, "_fork_status_bar_patch_applied", False):
        return

    for name in PATCH_METHOD_NAMES:
        setattr(cls, name, getattr(CliForkStatusBarMixin, name))

    def _append_pending_queue_status_part(self, parts: list) -> None:
        from hermes_cli.cli_pending_queue import pending_queue_depth, queue_status_fragment

        frag = queue_status_fragment(pending_queue_depth(getattr(self, "_pending_input", None)))
        if frag:
            parts.append(frag)

    def _append_pending_queue_status_fragments(self, frags: list, *, separator: str = " │ ") -> None:
        from hermes_cli.cli_pending_queue import pending_queue_depth, queue_status_fragment

        frag = queue_status_fragment(pending_queue_depth(getattr(self, "_pending_input", None)))
        if frag:
            frags.append(("class:status-bar-dim", separator))
            frags.append(("class:status-bar-dim", frag))

    cls._append_pending_queue_status_part = _append_pending_queue_status_part  # type: ignore[attr-defined]
    cls._append_pending_queue_status_fragments = _append_pending_queue_status_fragments  # type: ignore[attr-defined]

    from overlay.hermes_cli.cli_tps_stream_hooks import (
        freeze_stream_tps_segment,
        record_stream_tps_delta,
    )

    cls._record_stream_tps_delta = record_stream_tps_delta  # type: ignore[attr-defined]
    cls._freeze_stream_tps_segment = freeze_stream_tps_segment  # type: ignore[attr-defined]

    if not getattr(cls, "_fork_stream_delta_wrapped", False):
        _orig_stream_delta = cls._stream_delta

        def _stream_delta(self, text: Optional[str]) -> Any:
            try:
                if text is None:
                    freeze_stream_tps_segment(self)
                elif text:
                    record_stream_tps_delta(self, text)
            except Exception:
                logger.debug("stream throughput hook failed", exc_info=True)
            return _orig_stream_delta(self, text)

        cls._stream_delta = _stream_delta  # type: ignore[method-assign]
        cls._fork_stream_delta_wrapped = True

    if not getattr(cls, "_fork_display_init_wrapped", False):
        _orig_init = cls.__init__

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            _orig_init(self, *args, **kwargs)
            apply_fork_display_attrs(self)

        cls.__init__ = __init__  # type: ignore[method-assign]
        cls._fork_display_init_wrapped = True

    if not hasattr(cls, "_apply_post_sync_new_chat_notice"):

        def _apply_post_sync_new_chat_notice(self):
            """Honor institutional_new_chat_required.json after sync/relaunch."""
            import os

            if os.environ.get("HERMES_SKIP_AUTO_NEW_AFTER_SYNC") == "1":
                return
            try:
                from hermes_cli.institutional_new_chat_notice import (
                    acknowledge_new_chat_notice,
                    read_new_chat_notice,
                )
            except Exception:
                return
            if not read_new_chat_notice():
                return
            history = getattr(self, "conversation_history", None) or []
            if not history:
                acknowledge_new_chat_notice()
                return
            try:
                self.new_session(silent=True)
            except Exception:
                pass

        cls._apply_post_sync_new_chat_notice = _apply_post_sync_new_chat_notice  # type: ignore[attr-defined]

    cls._fork_status_bar_patch_applied = True
