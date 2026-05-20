"""Rapport van overgeslagen / OCR-pogingen tijdens RAG-ingest."""

from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from kb_schema import DB_PATH

REPORT_BASENAME = "rag_ingest_skipped_report.json"
LOG_SKIP_PATTERNS = [
    re.compile(
        r"Lege inhoud na inlezen/conversie, overslaan:\s*(.+)$", re.IGNORECASE
    ),
    re.compile(
        r"MarkItDown-conversie mislukt voor\s+(.+?):\s*(.+)$", re.IGNORECASE
    ),
]


@dataclass
class SkipEntry:
    relative_source: str
    reason: str
    detail: str = ""
    size_bytes: int | None = None
    ocr_attempted: bool = False
    ocr_method: str = ""


@dataclass
class SkipReport:
    entries: list[SkipEntry] = field(default_factory=list)

    def add(
        self,
        file_path: Path,
        root: Path,
        *,
        reason: str,
        detail: str = "",
        size_bytes: int | None = None,
        ocr_attempted: bool = False,
        ocr_method: str = "",
    ) -> None:
        try:
            rel = str(file_path.relative_to(root)).replace("\\", "/")
        except ValueError:
            rel = str(file_path)
        self.entries.append(
            SkipEntry(
                relative_source=rel,
                reason=reason,
                detail=detail[:2000],
                size_bytes=size_bytes,
                ocr_attempted=ocr_attempted,
                ocr_method=ocr_method,
            )
        )

    def write(self, dest: Path | None = None) -> Path:
        dest = dest or default_report_path()
        dest.parent.mkdir(parents=True, exist_ok=True)
        pdf_png = [
            e for e in self.entries
            if Path(e.relative_source).suffix.lower() in {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp"}
        ]
        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "db_path": DB_PATH,
            "total_skipped": len(self.entries),
            "pdf_png_skipped": len(pdf_png),
            "entries": [asdict(e) for e in self.entries],
            "pdf_png_only": [asdict(e) for e in pdf_png],
        }
        dest.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        md = dest.with_suffix(".md")
        md.write_text(_format_markdown(payload), encoding="utf-8")
        return dest

    def merge_from_log(self, log_path: Path, raw_root: Path) -> int:
        """Parse bestaand rag_ingest_run.log (achteraf). Returns aantal nieuwe regels."""
        if not log_path.is_file():
            return 0
        seen = {e.relative_source for e in self.entries}
        added = 0
        text = read_ingest_log_text(log_path)
        merged = _merge_wrapped_log_lines(text)
        for line in merged:
            for pat in LOG_SKIP_PATTERNS:
                m = pat.search(line)
                if not m:
                    continue
                full = m.group(1).strip()
                try:
                    fp = Path(full)
                    if fp.is_absolute():
                        try:
                            rel = str(fp.relative_to(raw_root.resolve())).replace("\\", "/")
                        except ValueError:
                            rel = full.replace("\\", "/")
                    else:
                        rel = full.replace("\\", "/")
                except Exception:
                    rel = full.replace("\\", "/")
                if rel in seen:
                    break
                reason = "empty_after_convert" if "Lege inhoud" in line else "convert_failed"
                detail = m.group(2).strip() if m.lastindex and m.lastindex >= 2 else ""
                self.entries.append(
                    SkipEntry(relative_source=rel, reason=reason, detail=detail)
                )
                seen.add(rel)
                added += 1
                break
        return added


def read_ingest_log_text(log_path: Path) -> str:
    """Lees ingest-log (UTF-8 zonder BOM, of legacy UTF-16 LE)."""
    raw = log_path.read_bytes()
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        return raw.decode("utf-16", errors="replace")
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw[3:].decode("utf-8", errors="replace")
    return raw.decode("utf-8", errors="replace")


def _merge_wrapped_log_lines(text: str) -> list[str]:
    """CMD-log breekt lange paden over meerdere regels — plak voortzettingen aan."""
    out: list[str] = []
    carry = ""
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("["):
            if carry:
                out.append(carry)
                carry = ""
            out.append(line)
        elif carry:
            carry += line
        elif out and "overslaan:" in out[-1]:
            out[-1] += line
        else:
            out.append(line)
    if carry:
        out.append(carry)
    return out


def default_report_path() -> Path:
    override = (os.environ.get("HERMES_RAG_SKIP_REPORT") or "").strip()
    if override:
        return Path(os.path.expanduser(os.path.expandvars(override)))
    return Path(DB_PATH) / REPORT_BASENAME


def _format_markdown(payload: dict) -> str:
    lines = [
        "# RAG ingest — overgeslagen bronnen",
        "",
        f"- Gegenereerd: {payload.get('generated_at', '')}",
        f"- Totaal overgeslagen: {payload.get('total_skipped', 0)}",
        f"- PDF/PNG (subset): {payload.get('pdf_png_skipped', 0)}",
        "",
        "## PDF en afbeeldingen (OCR-plan)",
        "",
    ]
    for e in payload.get("pdf_png_only") or []:
        lines.append(f"- `{e['relative_source']}` — **{e['reason']}** {e.get('detail', '')}")
    lines.extend(["", "## Alle overgeslagen", ""])
    for e in payload.get("entries") or []:
        lines.append(f"- `{e['relative_source']}` — {e['reason']}")
    return "\n".join(lines) + "\n"
