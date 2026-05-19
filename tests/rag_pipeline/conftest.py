"""Zet scripts/rag_pipeline op sys.path voor unit tests."""

from __future__ import annotations

import sys
from pathlib import Path

_RAG_DIR = Path(__file__).resolve().parents[2] / "scripts" / "rag_pipeline"
if str(_RAG_DIR) not in sys.path:
    sys.path.insert(0, str(_RAG_DIR))
