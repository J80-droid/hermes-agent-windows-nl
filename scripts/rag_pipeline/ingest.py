import hashlib
import os
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional

import lancedb
import pyarrow as pa
from markitdown import MarkItDown


def _env_truthy(name: str) -> bool:
    v = os.environ.get(name)
    if v is None or str(v).strip() == "":
        return False
    return str(v).strip().lower() not in ("0", "false", "no", "n", "off")


def _int_env_positive(name: str, default: int, *, cap: int | None = None) -> int:
    raw = (os.environ.get(name) or str(default)).strip()
    try:
        v = int(raw)
    except ValueError:
        v = default
    v = max(1, v)
    if cap is not None:
        v = min(v, cap)
    return v


def _float_env_nonnegative(name: str, default: float) -> float:
    raw = (os.environ.get(name) or str(default)).strip()
    try:
        v = float(raw)
    except ValueError:
        v = default
    return max(0.0, v)


from ingest_ui import (
    C_CYAN,
    C_DIM,
    C_GREEN,
    C_RED,
    C_RESET,
    C_YELLOW,
    LOG_IO as _LOG_IO,
    TTY_PROGRESS as _TTY_PROGRESS,
    compact_ok_line,
    create_file_progress,
    info as _ui_info,
    log_during_progress,
    ok as _ui_ok,
    print_banner,
    print_phase,
    set_progress_file,
    set_progress_phase_count,
    warn as _ui_warn,
)

from kb_schema import DB_PATH, TABLE_NAME, KnowledgeSchema, list_all_table_names

try:
    from audio_transcriber import transcribe_media_file, write_transcript_to_temp

    _HAS_AUDIO_TRANSCRIBER = True
except ImportError:
    _HAS_AUDIO_TRANSCRIBER = False

from ingest_config import filter_ingest_candidates, max_file_bytes
from ingest_handlers import convert_document
from ingest_state import (
    IngestState,
    checkpoint_interval,
    incremental_ingest_enabled,
    normalize_relative_source,
    orphan_cleanup_enabled,
    state_file_path,
)
from orphan_cleanup import delete_all_chunks_for_source, delete_orphan_chunks_for_source
from source_formats import MARKITDOWN_SUFFIXES, MEDIA_SUFFIXES, supported_extension_globs
from subtitle_sidecar import filter_subtitles_indexed_via_media, read_media_text_via_sidecar

# Semantische chunking: kleinere, coherentere stukken dan vaste woordvensters.
DEFAULT_MAX_WORDS = 400

_MARKITDOWN_SUFFIXES = MARKITDOWN_SUFFIXES
_MEDIA_SUFFIXES = MEDIA_SUFFIXES

# Fenced code (``` ... ```): als éénheid behouden waar mogelijk; anders op \n\n binnen het blok.
_CODE_FENCE = re.compile(r"```[a-zA-Z0-9_+-]*\s*\n?([\s\S]*?)```", re.MULTILINE)
# Markdown koppen ## t/m ######
_MD_HEADING_SPLIT = re.compile(r"(?m)^(?=(?:#{2,6}\s))")
# Zin-einde (incl. ellipsis) gevolgd door witruimte
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?…])\s+")


def _word_count(text: str) -> int:
    return len(text.split())


def _iter_fenced_and_prose(text: str):
    """Wisselt tussen ruwe tekst (False) en volledige ```-fence inclusief backticks (True)."""
    last = 0
    for m in _CODE_FENCE.finditer(text):
        if m.start() > last:
            yield text[last:m.start()], False
        yield m.group(0), True
        last = m.end()
    if last < len(text):
        yield text[last:], False


def _pack_units(
    units: list[str],
    max_words: int,
    joiner: str,
) -> list[str]:
    """Voeg opeenvolgende eenheden samen tot max_words; te grote eenheid apart opsplitsen."""
    out: list[str] = []
    buf: list[str] = []
    wc = 0
    for u in units:
        u = u.strip()
        if not u:
            continue
        uw = _word_count(u)
        if uw > max_words:
            if buf:
                out.append(joiner.join(buf))
                buf = []
                wc = 0
            out.extend(_split_oversized(u, max_words))
        elif wc + uw > max_words:
            if buf:
                out.append(joiner.join(buf))
            buf = [u]
            wc = uw
        else:
            buf.append(u)
            wc += uw
    if buf:
        out.append(joiner.join(buf))
    return out


def _split_oversized(unit: str, max_words: int) -> list[str]:
    parts = [p.strip() for p in _SENTENCE_SPLIT.split(unit) if p.strip()]
    if len(parts) <= 1:
        return _split_by_lines_or_words(unit, max_words)
    return _pack_units(parts, max_words, joiner=" ")


def _split_by_lines_or_words(unit: str, max_words: int) -> list[str]:
    lines = [ln.strip() for ln in unit.split("\n") if ln.strip()]
    if len(lines) > 1:
        return _pack_units(lines, max_words, joiner="\n")
    words = unit.split()
    if not words:
        return []
    out: list[str] = []
    for i in range(0, len(words), max_words):
        chunk = " ".join(words[i : i + max_words])
        if chunk.strip():
            out.append(chunk)
    return out


def _chunk_prose(text: str, max_words: int) -> list[str]:
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        return []
    units: list[str] = []
    for section in _MD_HEADING_SPLIT.split(text):
        section = section.strip()
        if not section:
            continue
        for para in re.split(r"\n{2,}", section):
            p = para.strip()
            if p:
                units.append(p)
    return _pack_units(units, max_words, joiner="\n\n")


def _chunk_code_fence(block: str, max_words: int) -> list[str]:
    block = block.strip()
    if not block:
        return []
    if _word_count(block) <= max_words:
        return [block]
    inner_parts = [p.strip() for p in block.split("\n\n") if p.strip()]
    if len(inner_parts) > 1:
        return _pack_units(inner_parts, max_words, joiner="\n\n")
    return _split_by_lines_or_words(block, max_words)


def _collect_rag_source_files(path: Path, extensions: list[str]) -> list[Path]:
    """Verzamelt bronbestanden, past uitsluitingen toe, sorteert voor stabiele volgorde."""
    seen: set[object] = set()
    out: list[Path] = []
    for ext in extensions:
        for file_path in path.rglob(ext):
            try:
                key = file_path.resolve()
            except OSError:
                key = file_path
            if key in seen:
                continue
            seen.add(key)
            out.append(file_path)
    out.sort(key=lambda p: str(p).casefold())
    filtered, skipped = filter_ingest_candidates(out)
    if skipped:
        parts = ", ".join(f"{k}={v}" for k, v in sorted(skipped.items()))
        print(f"{C_YELLOW}[WARN]{C_RESET} Overgeslagen na scan: {parts}")
    return filtered


def _chunk_row_id(relative_source: str, chunk_index: int) -> str:
    """Deterministische sleutel: zelfde bron + chunk-index => zelfde id (veilig voor upsert)."""
    rel = Path(relative_source).as_posix()
    return hashlib.sha256(f"{rel}\0#{chunk_index}".encode("utf-8")).hexdigest()


def _schema_has_id(schema: pa.Schema) -> bool:
    return "id" in schema.names


def _upsert_chunk_rows(table, rows: list[dict]) -> None:
    if not rows:
        return
    table.merge_insert("id").when_matched_update_all().when_not_matched_insert_all().execute(rows)


def _upsert_rows_with_embed_progress(
    table,
    rows: list[dict],
    relative_source: str,
    pbar: object,
    embed_batch: int,
) -> None:
    """Voert merge_insert uit; bij veel chunks tussenloggen zodat [EMBEDDEN] niet 'stil' voelt."""
    n = len(rows)
    if n == 0:
        return
    b = max(1, embed_batch)
    if n <= b:
        log_during_progress(
            f"{C_DIM}[INFO] [EMBEDDEN]{C_RESET} LanceDB + sentence-transformers: {n} chunk(s), "
            f"{relative_source}{C_DIM} …{C_RESET}",
            pbar,
        )
        log_during_progress(
            f"{C_CYAN}[INFO]{C_RESET} Upsert {n} chunk(s) voor bron: {relative_source} (merge_insert op id)...",
            pbar,
        )
        _upsert_chunk_rows(table, rows)
        return

    log_during_progress(
        f"{C_DIM}[INFO] [EMBEDDEN]{C_RESET} {n} chunk(s) in batches van {b}: {relative_source}{C_DIM} …{C_RESET}",
        pbar,
    )
    for i in range(0, n, b):
        part = rows[i : i + b]
        lo, hi = i + 1, i + len(part)
        log_during_progress(
            f"{C_DIM}[INFO] [EMBEDDEN]{C_RESET} batch {lo}–{hi} / {n} — {relative_source}{C_DIM} …{C_RESET}",
            pbar,
        )
        log_during_progress(
            f"{C_CYAN}[INFO]{C_RESET} Upsert {len(part)} chunk(s) (merge_insert op id)...",
            pbar,
        )
        _upsert_chunk_rows(table, part)


def _relative_source(file_path: Path, root: Path) -> str:
    return normalize_relative_source(str(file_path.relative_to(root)))


def _read_plain_utf8(file_path: Path, pbar: object) -> str | None:
    """Leest UTF-8 platte tekst; `None` bij fout (waarschuwing al gelogd)."""
    log_during_progress(
        f"{C_DIM}[INFO] [LEZEN]{C_RESET} UTF-8: {file_path.name}{C_DIM} …{C_RESET}",
        pbar,
    )
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except OSError as e:
        log_during_progress(
            f"{C_YELLOW}[WARN]{C_RESET} Bestand niet leesbaar (IO): {file_path}: {e}",
            pbar,
        )
        return None
    except UnicodeDecodeError as e:
        log_during_progress(
            f"{C_YELLOW}[WARN]{C_RESET} Geen geldige UTF-8: {file_path}: {e}",
            pbar,
        )
        return None


def semantic_chunk_document(text: str, max_words: int = DEFAULT_MAX_WORDS) -> list[str]:
    """
    Splits tekst op natuurlijke grenzen: fenced code, Markdown-koppen (##+),
    alinea's (dubbele newline), zinnen en zo nodig regels/woorden — met max. ~max_words woorden per chunk.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    chunks: list[str] = []
    for segment, is_fence in _iter_fenced_and_prose(text):
        if is_fence:
            chunks.extend(_chunk_code_fence(segment, max_words))
        else:
            chunks.extend(_chunk_prose(segment, max_words))
    return [c for c in chunks if c.strip()]


def process_and_ingest(source_directory: str, max_words: int = DEFAULT_MAX_WORDS):
    """Scant de bronmap, verwerkt bestanden en schrijft naar LanceDB met idempotente upsert op `id`."""
    _ui_info(f"Initialiseren databaseverbinding op: {DB_PATH}")
    db = lancedb.connect(DB_PATH)

    if TABLE_NAME in list_all_table_names(db):
        table = db.open_table(TABLE_NAME)
        _ui_info(f"Bestaande tabel '{TABLE_NAME}' geopend.")
        if not _schema_has_id(table.schema):
            print(
                f"{C_RED}[ERROR]{C_RESET} De bestaande tabel mist de kolom 'id' (oud schema vóór upsert-architectuur)."
            )
            print(
                f"{C_RED}[ERROR]{C_RESET} Kies eenmalig 'J' / HERMES_RAG_FRESH=1, of: "
                "python scripts/rag_pipeline/schema_migrate.py --backup-and-reset"
            )
            sys.exit(2)
    else:
        table = db.create_table(TABLE_NAME, schema=KnowledgeSchema)
        _ui_info(f"Nieuwe tabel '{TABLE_NAME}' succesvol aangemaakt.")

    supported_extensions = supported_extension_globs()

    print_phase("Scan bronmap")
    _ui_info(f"Directory: {source_directory}")
    _max_b = max_file_bytes()
    if _max_b is not None:
        print(
            f"{C_CYAN}[INFO]{C_RESET} Max. bestandsgrootte: {_max_b // (1024 * 1024)} MB "
            f"(HERMES_RAG_MAX_FILE_MB; weglaten = onbeperkt)"
        )
    print(
        f"{C_CYAN}[INFO]{C_RESET} Semantische chunking actief (max. ca. {max_words} woorden per chunk)."
    )
    path = Path(source_directory)
    any_indexed = False

    all_files = _collect_rag_source_files(path, supported_extensions)
    all_files, subtitle_dup_skip = filter_subtitles_indexed_via_media(all_files)
    if subtitle_dup_skip:
        print(
            f"{C_CYAN}[INFO]{C_RESET} Ondertitels gekoppeld aan media (geen dubbele index): "
            f"{subtitle_dup_skip} bestand(en) overgeslagen."
        )

    current_sources = {normalize_relative_source(_relative_source(p, path)) for p in all_files}
    ingest_state = IngestState.load()
    to_process: list[Path] = []
    skipped_unchanged = 0
    if incremental_ingest_enabled():
        for fp in all_files:
            rel = _relative_source(fp, path)
            if ingest_state.needs_processing(rel, fp):
                to_process.append(fp)
            else:
                skipped_unchanged += 1
        if skipped_unchanged:
            print(
                f"{C_CYAN}[INFO]{C_RESET} Incrementele ingest: {skipped_unchanged} ongewijzigde "
                f"bron(nen) overgeslagen (`HERMES_RAG_INCREMENTAL=1`; volledige scan: "
                f"`HERMES_RAG_FORCE_FULL=1`)."
            )
    else:
        to_process = all_files

    _cpu = os.cpu_count() or 4
    conv_workers = _int_env_positive("HERMES_RAG_CONVERT_WORKERS", 1, cap=min(_cpu, 8))
    embed_batch = _int_env_positive("HERMES_RAG_EMBED_BATCH", 64, cap=512)
    hb_sec = _float_env_nonnegative("HERMES_RAG_CONVERT_HEARTBEAT_SEC", 3.0)
    print_banner(
        total_files=len(to_process),
        scan_total=len(all_files),
        db_path=DB_PATH,
        workers=conv_workers,
    )
    if conv_workers > 1:
        _ui_info(
            f"Parallel MarkItDown: max. {conv_workers} tegelijk | embed batch {embed_batch} | "
            f"heartbeat {hb_sec}s (0=uit) | detail: HERMES_RAG_VERBOSE=1"
        )

    print_phase("Indexeren")
    pbar = create_file_progress(len(to_process))

    parallel_conv = conv_workers > 1

    def _finalize_file(
        file_path: Path,
        content: str | None,
        md_err: str | None,
        temp_txt_path: Optional[Path] = None,
    ) -> None:
        nonlocal any_indexed
        set_progress_file(pbar, file_path, path)
        try:
            if md_err is not None:
                log_during_progress(
                    f"{C_YELLOW}[WARN]{C_RESET} MarkItDown-conversie mislukt voor {file_path}: {md_err}",
                    pbar,
                )
                return
            if content is None:
                return
            if not content.strip():
                log_during_progress(
                    f"{C_YELLOW}[WARN]{C_RESET} Lege inhoud na inlezen/conversie, overslaan: {file_path}",
                    pbar,
                )
                return

            try:
                chunks = semantic_chunk_document(content, max_words=max_words)
            except Exception as e:
                log_during_progress(
                    f"{C_YELLOW}[WARN]{C_RESET} Chunking mislukt voor {file_path} ({type(e).__name__}): {e}",
                    pbar,
                )
                return

            try:
                relative_source = _relative_source(file_path, path)
            except ValueError as e:
                log_during_progress(
                    f"{C_YELLOW}[WARN]{C_RESET} Pad relatief maken mislukt voor {file_path}: {e}",
                    pbar,
                )
                return

            rows: list[dict] = [
                {
                    "id": _chunk_row_id(str(relative_source), i),
                    "text": chunk,
                    "source": str(relative_source),
                }
                for i, chunk in enumerate(chunks)
            ]
            if not rows:
                log_during_progress(
                    f"{C_YELLOW}[WARN]{C_RESET} Geen chunk-output na chunking, overslaan: {relative_source}",
                    pbar,
                )
                return

            _upsert_rows_with_embed_progress(
                table, rows, str(relative_source), pbar, embed_batch=embed_batch
            )
            if orphan_cleanup_enabled():
                removed = delete_orphan_chunks_for_source(
                    table, str(relative_source), [r["id"] for r in rows]
                )
                if removed:
                    log_during_progress(
                        f"{C_DIM}[INFO]{C_RESET} Orphan cleanup: {removed} oude chunk(s) "
                        f"verwijderd voor {relative_source}",
                        pbar,
                    )
            ingest_state.record_success(
                str(relative_source), file_path, chunk_count=len(rows)
            )
            any_indexed = True
            log_during_progress(
                compact_ok_line(relative_source, len(rows)),
                pbar,
                force=True,
            )
        finally:
            if temp_txt_path is not None:
                temp_txt_path.unlink(missing_ok=True)
            upd = getattr(pbar, "update", None)
            if callable(upd):
                upd(1)

    def _process_media_file(file_path: Path) -> None:
        """Media: standaard Whisper (kwaliteit); ondertitel-sidecar alleen als fallback of expliciet."""
        temp_txt_path: Optional[Path] = None
        prefer_sidecar = _env_truthy("HERMES_RAG_PREFER_SIDECAR")

        if prefer_sidecar:
            sidecar_text, sidecar_path = read_media_text_via_sidecar(file_path)
            if sidecar_text is not None:
                log_during_progress(
                    f"{C_DIM}[INFO] [ONDERTITELS]{C_RESET} {sidecar_path.name} "
                    f"(HERMES_RAG_PREFER_SIDECAR=1) voor {file_path.name}{C_DIM} …{C_RESET}",
                    pbar,
                )
                _finalize_file(file_path, sidecar_text, None, None)
                return

        if _HAS_AUDIO_TRANSCRIBER:
            try:
                log_during_progress(
                    f"{C_DIM}[INFO] [TRANSCRIBEREN]{C_RESET} Whisper: {file_path.name}{C_DIM} …{C_RESET}",
                    pbar,
                )
                transcript = transcribe_media_file(file_path)
                temp_txt_path = write_transcript_to_temp(file_path, transcript)
                _finalize_file(file_path, transcript, None, temp_txt_path)
                return
            except Exception as e:
                if temp_txt_path is not None:
                    temp_txt_path.unlink(missing_ok=True)
                    temp_txt_path = None
                log_during_progress(
                    f"{C_YELLOW}[WARN]{C_RESET} Whisper mislukt voor {file_path} ({type(e).__name__}): {e}",
                    pbar,
                )
                sidecar_text, sidecar_path = read_media_text_via_sidecar(file_path)
                if sidecar_text is not None:
                    log_during_progress(
                        f"{C_DIM}[INFO] [ONDERTITELS]{C_RESET} fallback na Whisper-fout: "
                        f"{sidecar_path.name}{C_DIM} …{C_RESET}",
                        pbar,
                    )
                    _finalize_file(file_path, sidecar_text, None, None)
                    return
                _finalize_file(file_path, None, f"{type(e).__name__}: {e}", None)
                return

        sidecar_text, sidecar_path = read_media_text_via_sidecar(file_path)
        if sidecar_text is not None:
            log_during_progress(
                f"{C_DIM}[INFO] [ONDERTITELS]{C_RESET} {sidecar_path.name} "
                f"(geen Whisper) voor {file_path.name}{C_DIM} …{C_RESET}",
                pbar,
            )
            _finalize_file(file_path, sidecar_text, None, None)
            return

        log_during_progress(
            f"{C_YELLOW}[WARN]{C_RESET} Geen Whisper en geen ondertitel-sidecar voor {file_path}",
            pbar,
        )
        _finalize_file(file_path, None, "geen transcriptie beschikbaar", None)

    wave_i = 0
    n_all = len(to_process)

    try:
        while wave_i < n_all:
            wave = to_process[wave_i : wave_i + conv_workers]
            wave_i += len(wave)
            for file_path in wave:
                if file_path.suffix.lower() in _MEDIA_SUFFIXES:
                    _process_media_file(file_path)
            md_list = [p for p in wave if p.suffix.lower() in _MARKITDOWN_SUFFIXES]
            use_md_pool = parallel_conv and len(md_list) > 1
            pool_workers = max(1, min(conv_workers, len(md_list)))

            if use_md_pool:
                with ThreadPoolExecutor(max_workers=pool_workers) as ex:
                    pending: dict = {}
                    for file_path in wave:
                        suf = file_path.suffix.lower()
                        if suf in _MEDIA_SUFFIXES:
                            continue
                        if suf in _MARKITDOWN_SUFFIXES:
                            log_during_progress(
                                f"{C_DIM}[INFO] [CONVERTEREN]{C_RESET} MarkItDown: {file_path.name}{C_DIM} …{C_RESET}",
                                pbar,
                            )
                            pending[ex.submit(convert_document, file_path)] = file_path
                        else:
                            plain = _read_plain_utf8(file_path, pbar)
                            _finalize_file(file_path, plain, None, None)

                    if not pending:
                        continue

                    done_ev = threading.Event()
                    bt: threading.Thread | None = None
                    total_md_tasks = len(pending)
                    if hb_sec > 0:

                        def _heartbeat() -> None:
                            while not done_ev.wait(timeout=hb_sec):
                                alive = sum(1 for f in pending if not f.done())
                                if alive <= 0:
                                    break
                                set_progress_phase_count(
                                    pbar,
                                    "MarkItDown",
                                    total_md_tasks - alive,
                                    total_md_tasks,
                                )

                        bt = threading.Thread(target=_heartbeat, daemon=True)
                        bt.start()

                    try:
                        for fut in as_completed(pending):
                            fp = pending[fut]
                            try:
                                text, err = fut.result()
                            except Exception as e:
                                text, err = "", f"{type(e).__name__}: {e}"
                            _finalize_file(fp, text, err, None)
                    finally:
                        done_ev.set()
                        if bt is not None:
                            bt.join(timeout=1.0)
            else:
                for file_path in wave:
                    suf = file_path.suffix.lower()
                    if suf in _MEDIA_SUFFIXES:
                        continue
                    if suf in _MARKITDOWN_SUFFIXES:
                        log_during_progress(
                            f"{C_DIM}[INFO] [CONVERTEREN]{C_RESET} MarkItDown: {file_path.name}{C_DIM} …{C_RESET}",
                            pbar,
                        )
                        text, err = convert_document(file_path)
                        _finalize_file(file_path, text, err, None)
                    else:
                        plain = _read_plain_utf8(file_path, pbar)
                        _finalize_file(file_path, plain, None, None)

        removed_sources = ingest_state.prune_removed_sources(current_sources)
        for rel in removed_sources:
            if orphan_cleanup_enabled():
                n = delete_all_chunks_for_source(table, rel)
                if n:
                    print(
                        f"{C_CYAN}[INFO]{C_RESET} Verwijderd uit index (bron weg uit scan): {rel} "
                        f"({n} chunk(s))"
                    )
    finally:
        if ingest_state.entries:
            ingest_state.save()
            n_entries = len(ingest_state.entries)
            every = checkpoint_interval()
            if every > 0:
                print(
                    f"{C_CYAN}[INFO]{C_RESET} Ingest-staat opgeslagen ({n_entries} bronnen): "
                    f"{state_file_path()} (checkpoint elke {every} bronnen + bij afsluiten)."
                )

    if hasattr(pbar, "close"):
        pbar.close()
    if any_indexed or skipped_unchanged:
        _ui_ok("Ingestie-scan afgerond (upsert + orphan cleanup + ingest-staat).")
    else:
        _ui_warn("Geen compatibele data gevonden om te indexeren.")


if __name__ == "__main__":
    _raw = (os.getenv("HERMES_RAG_RAW_SOURCE") or "").strip()
    DATA_SRC = os.path.normpath(
        os.path.expanduser(os.path.expandvars(_raw if _raw else "~/data/raw_source_files"))
    )
    os.makedirs(DATA_SRC, exist_ok=True)
    process_and_ingest(DATA_SRC)
