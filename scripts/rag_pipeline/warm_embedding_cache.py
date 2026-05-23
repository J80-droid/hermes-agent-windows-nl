"""Warm sentence-transformers model cache (idempotent; gebruikt door install_rag_extras)."""

from __future__ import annotations

import sys


def main() -> int:
    from rag_log_quiet import apply_torch_ingest_quiet
    from kb_schema import EMBEDDING_MODEL_NAME

    apply_torch_ingest_quiet()
    from sentence_transformers import SentenceTransformer

    SentenceTransformer(EMBEDDING_MODEL_NAME)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
