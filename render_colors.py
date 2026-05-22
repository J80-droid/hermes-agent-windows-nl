"""DEPRECATED: use Hermes Rich markdown (display.final_response_markdown=render).

Legacy implementation: windows/scripts/institutional/render_colors_legacy.py
"""
import sys

if __name__ == "__main__":
    sys.stderr.write(
        "render_colors.py is deprecated. Use APPLY_TEAM_DISPLAY.bat and Rich markdown.\n"
        "Legacy: windows/scripts/institutional/render_colors_legacy.py\n"
    )
    if not sys.stdin.isatty():
        from pathlib import Path

        legacy = Path(__file__).resolve().parent / "windows" / "scripts" / "institutional" / "render_colors_legacy.py"
        if legacy.is_file():
            import runpy
            runpy.run_path(str(legacy), run_name="__main__")
        else:
            sys.stdout.write(sys.stdin.read())
    sys.exit(0)
