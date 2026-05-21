"""Preflight: bronmappen uit domains.yaml vóór bulk-ingest (P1)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from domains_config import default_domains_yaml, load_domains, resolve_domain_paths  # noqa: E402


def _count_source_files(raw: Path) -> int:
    if not raw.is_dir():
        return -1
    return sum(1 for p in raw.rglob("*") if p.is_file())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Preflight RAG bronmappen")
    parser.add_argument("--domains-yaml", type=Path, default=None)
    parser.add_argument(
        "--only",
        nargs="*",
        default=[],
        help="Alleen deze domeinen (default: alle uit yaml)",
    )
    parser.add_argument(
        "--skip-empty",
        action="store_true",
        help="Exit 1 als een geselecteerd domein 0 bronbestanden heeft",
    )
    args = parser.parse_args(argv)

    yaml_path = args.domains_yaml or default_domains_yaml()
    specs = load_domains(yaml_path)
    if args.only:
        wanted = {d.strip().lower() for d in args.only}
        specs = [s for s in specs if s.name in wanted]

    empty: list[str] = []
    ok_count = 0
    print(f"[INFO] Preflight bronmappen ({yaml_path})")
    for spec in specs:
        _, raw, _ = resolve_domain_paths(spec)
        n = _count_source_files(raw)
        if n < 0:
            print(f"  [MISS] {spec.name}: bronmap ontbreekt ({raw})")
            empty.append(spec.name)
        elif n == 0:
            print(f"  [EMPTY] {spec.name}: 0 bestanden in {raw}")
            empty.append(spec.name)
        else:
            print(f"  [OK] {spec.name}: {n} bestand(en) in {raw}")
            ok_count += 1

    if empty:
        print(
            f"[WARN] {len(empty)} domein(en) zonder bronnen: {', '.join(empty)}",
            file=sys.stderr,
        )
        print(
            "[INFO] Vul %USERPROFILE%\\data\\raw_source_files\\<source_dir> of pas domains.yaml aan.",
            file=sys.stderr,
        )
        return 1 if args.skip_empty else 0
    print(f"[OK] Alle {ok_count} domein(en) hebben bronbestanden.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
