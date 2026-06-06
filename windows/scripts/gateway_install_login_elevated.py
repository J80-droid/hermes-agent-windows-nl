"""Launch elevated Hermes gateway install (UAC). Used by GATEWAY_INSTALL_LOGIN.ps1."""
from __future__ import annotations

from hermes_cli.gateway_windows import _launch_elevated_install


def main() -> int:
    ok = _launch_elevated_install(start_now=True, start_on_login=True)
    if ok:
        print("UAC gestart. Keur goed in het Windows-dialoogvenster.")
        return 0
    print("UAC kon niet worden gestart (ShellExecuteW).")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
