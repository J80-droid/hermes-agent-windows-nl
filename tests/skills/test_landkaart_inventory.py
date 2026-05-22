"""Tests voor landkaart inventory script."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "skills/productivity/landkaart/scripts/inventory_landkaart.py"


def test_inventory_lists_all_items():
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--json"],
        input="alpha\nbeta\ngamma\n",
        capture_output=True,
        text=True,
        check=False,
        cwd=str(REPO),
    )
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert data["count"] == 3
    assert [x["index"] for x in data["items"]] == [1, 2, 3]


def test_markdown_asks_which_first():
    proc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input="een\ntwee\n",
        capture_output=True,
        text=True,
        check=False,
        cwd=str(REPO),
    )
    assert proc.returncode == 0
    assert "1." in proc.stdout
    assert "2." in proc.stdout
    assert "Welk item" in proc.stdout
