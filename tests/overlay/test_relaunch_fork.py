"""Fork relaunch tests migrated from tests/hermes_cli/test_relaunch.py."""
import sys
import threading
import pytest
from overlay.bootstrap import install
from hermes_cli import relaunch as relaunch_mod

@pytest.fixture(autouse=True)
def _bootstrap():
    install()
class TestResolveHermesBinWindowsPyGuard:
    """On Windows, resolve_hermes_bin MUST NOT return a .py path.
    os.access(x, os.X_OK) returns True for .py files on Windows because
    PATHEXT includes .py when the Python launcher is installed â€” but
    subprocess.run can't actually exec a .py directly, so the relaunch
    would fail with the cryptic "%1 is not a valid Win32 application" error.
    """

    def test_windows_rejects_py_argv0_falls_through_to_path(self, monkeypatch, tmp_path):
        """On Windows, if sys.argv[0] is a .py file, we must skip the
        argv[0] fast-path and fall through to PATH / python -m."""
        # Build a fake .py script that "passes" the isfile + X_OK checks.
        script = tmp_path / "main.py"
        script.write_text("# stub")

        monkeypatch.setattr(relaunch_mod.sys, "platform", "win32")
        monkeypatch.setattr(relaunch_mod.sys, "argv", [str(script), "chat"])
        # Force PATH lookup to return a hermes.exe so the test doesn't
        # exercise the None-fallback path (that's a separate test).
        monkeypatch.setattr(
            relaunch_mod.shutil, "which",
            lambda name: r"C:\venv\Scripts\hermes.exe" if name == "hermes" else None,
        )

        bin_path = relaunch_mod.resolve_hermes_bin()
        # Must NOT be the .py â€” must be the hermes.exe PATH entry.
        assert bin_path == r"C:\venv\Scripts\hermes.exe"

    def test_posix_still_accepts_py_argv0(self, monkeypatch, tmp_path):
        """POSIX behaviour unchanged: argv[0] pointing at an executable
        script (including .py with a shebang + chmod +x) is fine to return
        because POSIX exec can route through the shebang line."""
        if sys.platform == "win32":
            pytest.skip("POSIX semantics")
        script = tmp_path / "hermes"
        script.write_text("#!/usr/bin/env python3\n")
        script.chmod(0o755)
        monkeypatch.setattr(relaunch_mod.sys, "argv", [str(script), "chat"])
        assert relaunch_mod.resolve_hermes_bin() == str(script)

    def test_windows_py_argv0_with_no_hermes_on_path_returns_none(self, monkeypatch, tmp_path):
        """Bulletproof fallback: if argv0 is .py on Windows AND hermes.exe
        isn't on PATH, return None so the caller falls back to
        python -m hermes_cli.main."""
        script = tmp_path / "main.py"
        script.write_text("# stub")

        monkeypatch.setattr(relaunch_mod.sys, "platform", "win32")
        monkeypatch.setattr(relaunch_mod.sys, "argv", [str(script), "chat"])
        monkeypatch.setattr(relaunch_mod.shutil, "which", lambda name: None)

        assert relaunch_mod.resolve_hermes_bin() is None


class TestStripProfileFlags:
    def test_strip_profile_flags_short_p(self):
        argv = ["chat", "-p", "core", "--tui"]
        assert relaunch_mod.strip_profile_flags(argv) == ["chat", "--tui"]

    def test_strip_profile_flags_long(self):
        argv = ["chat", "--profile", "legal", "--dev"]
        assert relaunch_mod.strip_profile_flags(argv) == ["chat", "--dev"]

    def test_strip_profile_flags_equals(self):
        argv = ["--profile=trading", "chat"]
        assert relaunch_mod.strip_profile_flags(argv) == ["chat"]

    def test_strip_profile_flags_none(self):
        argv = ["chat", "--tui"]
        assert relaunch_mod.strip_profile_flags(argv) == ["chat", "--tui"]

    def test_strip_profile_flags_empty_p(self):
        argv = ["chat", "-p"]
        assert relaunch_mod.strip_profile_flags(argv) == ["chat"]


class TestStartupSpinner:
    def test_chat_relaunch_skips_spinner_on_windows(self, monkeypatch):
        """Interactive chat must not write stderr spinner for the whole session."""
        monkeypatch.setattr(relaunch_mod.sys, "platform", "win32")

        import subprocess as _subprocess

        spinner_started = []

        def fake_run(argv, env=None, **kwargs):
            class _Result:
                returncode = 0

            return _Result()

        def fake_spinner_thread(target, **kwargs):
            spinner_started.append(True)
            return threading.Thread(target=target, **kwargs)

        monkeypatch.setattr(_subprocess, "run", fake_run)
        monkeypatch.setattr(relaunch_mod.threading, "Thread", fake_spinner_thread)

        relaunch_mod._run_subprocess_with_startup_spinner(
            [r"C:\hermes.exe", "chat", "-p", "legal"], {}
        )
        assert spinner_started == []

    def test_non_chat_still_uses_bounded_spinner_on_windows(self, monkeypatch):
        monkeypatch.setattr(relaunch_mod.sys, "platform", "win32")

        import subprocess as _subprocess

        class _Proc:
            def poll(self):
                return 0

            def wait(self):
                return 0

        monkeypatch.setattr(_subprocess, "Popen", lambda *a, **k: _Proc())
        spinner_started = []

        def fake_thread(target, **kwargs):
            spinner_started.append(True)
            stop = threading.Event()
            stop.set()

            class _T:
                def start(self):
                    pass

                def join(self, timeout=None):
                    pass

            return _T()

        monkeypatch.setattr(relaunch_mod.threading, "Thread", fake_thread)

        relaunch_mod._run_subprocess_with_startup_spinner(
            [r"C:\hermes.exe", "doctor"], {}
        )
        assert spinner_started == [True]


class TestRelaunchChatAfterProfileSwitch:
    def test_build_argv_includes_explicit_profile(self, monkeypatch):
        monkeypatch.setattr(relaunch_mod, "resolve_hermes_bin", lambda: "/usr/bin/hermes")
        original = ["chat", "-p", "core", "--tui"]
        argv = relaunch_mod.build_relaunch_argv(
            ["chat", "-p", "legal"],
            preserve_inherited=True,
            original_argv=relaunch_mod.strip_profile_flags(original),
        )
        assert "-p" in argv
        assert "legal" in argv
        assert "chat" in argv
        # Old profile must not survive via inherited flags
        assert argv.count("core") == 0

    def test_relaunch_passes_reset_hermes_home_on_win32(self, monkeypatch):
        monkeypatch.setattr(relaunch_mod.sys, "platform", "win32")
        monkeypatch.setattr(relaunch_mod, "resolve_hermes_bin", lambda: r"C:\hermes.exe")
        monkeypatch.setattr(
            relaunch_mod,
            "_hermes_root_for_profile_relaunch",
            lambda: r"C:\Users\test\AppData\Local\hermes",
        )

        import subprocess as _subprocess

        captured: dict = {}

        def fake_run(argv, env=None, **kwargs):
            captured["argv"] = list(argv)
            captured["env"] = dict(env) if env else None

            class _Result:
                returncode = 0

            return _Result()

        monkeypatch.setattr(_subprocess, "run", fake_run)
        monkeypatch.setattr(relaunch_mod, "_run_subprocess_with_startup_spinner", fake_run)
        monkeypatch.setattr(relaunch_mod.os, "execvp", lambda *a, **kw: None)

        with pytest.raises(SystemExit):
            relaunch_mod.relaunch(
                ["chat", "-p", "legal"],
                preserve_inherited=False,
                reset_hermes_home_to_root=True,
            )

        assert captured["argv"] == [r"C:\hermes.exe", "chat", "-p", "legal"]
        assert captured["env"]["HERMES_HOME"] == r"C:\Users\test\AppData\Local\hermes"

    def test_profile_switch_calls_relaunch_with_profile(self, monkeypatch):
        calls: list = []

        def fake_relaunch(*args, **kwargs):
            calls.append((args, kwargs))

        monkeypatch.setattr(relaunch_mod, "relaunch", fake_relaunch)
        monkeypatch.setattr(
            relaunch_mod, "_print_profile_relaunch_progress", lambda *a, **kw: None
        )

        relaunch_mod.relaunch_chat_after_profile_switch(
            "legal", original_argv=["chat", "-p", "core", "--tui"]
        )

        assert len(calls) == 1
        extra_args, kwargs = calls[0][0][0], calls[0][1]
        assert list(extra_args) == ["chat", "-p", "legal"]
        assert kwargs["reset_hermes_home_to_root"] is True
        assert kwargs["preserve_inherited"] is True
        assert relaunch_mod.strip_profile_flags(kwargs["original_argv"]) == [
            "chat",
            "--tui",
        ]
