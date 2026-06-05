"""PYTHONSTARTUP hook for overlay bootstrap (see Invoke-HermesOverlayBootstrap.ps1).

Failures are logged via ``install_startup()``; the interpreter keeps starting so
Hermes can still run with upstream-only features.
"""
try:
    from overlay.bootstrap import install_startup as _run

    _run()
except Exception:
    pass
