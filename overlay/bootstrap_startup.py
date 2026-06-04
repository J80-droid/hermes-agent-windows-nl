"""PYTHONSTARTUP hook — see Invoke-HermesOverlayBootstrap.ps1."""
try:
    from overlay.bootstrap import install_startup as _run

    _run()
except Exception:
    pass
