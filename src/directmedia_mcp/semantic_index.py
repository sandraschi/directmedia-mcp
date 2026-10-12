"""Semantic (embedding) search over decoded volumes: LanceDB + FastEmbed, built per volume on demand.

Fleet RAG stack (standards/ai-rag-2026.md) with one documented deviation: the corpus is German,
so the default model is a German/multilingual one instead of bge-small-en
(DIRECTMEDIA_EMBED_MODEL overrides it).

Layout under <index dir>/semantic/: a LanceDB database with one table per volume build
("DB004_<timestamp>") and a meta file per volume naming the active table. A rebuild writes a new
table and then swaps the meta file, so searches never see a half-built table.
"""

import json
import os
import queue
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .dki_text import DkiFormatError, TextDki
from .dki_tree import TocEntry, breadcrumb, entry_for_record, load_toc
from .logging_config import get_logger
from .search_index import default_index_dir

logger = get_logger("directmedia_mcp.semantic_index")

DEFAULT_MODEL = os.getenv(
    "DIRECTMEDIA_EMBED_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)
# e5-family models expect role prefixes
_PREFIXES = {"intfloat/multilingual-e5-large": ("query: ", "passage: ")}
# 600/120 instead of the fleet 1000/200: the default model reads only ~128 tokens (~550 German chars)
CHUNK_CHARS, CHUNK_OVERLAP, MIN_CHUNK = 600, 120, 80
_BATCH = 64


def chunk_text(text: str, size: int = CHUNK_CHARS, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split on whitespace into ~size-char chunks with ~overlap chars carried over."""
    text = " ".join(text.split())
    if len(text) <= size:
        return [text] if len(text) >= MIN_CHUNK else []
    chunks, start = [], 0
    while start < len(text):
        end = min(len(text), start + size)
        if end < len(text):
            cut = text.rfind(" ", start + size // 2, end)
            end = cut if cut > 0 else end
        chunk = text[start:end].strip()
        if len(chunk) >= MIN_CHUNK:
            chunks.append(chunk)
        if end >= len(text):
            break
        nxt = text.rfind(" ", start, end - overlap)
        start = nxt + 1 if nxt > start else end
    return chunks


def work_title(entries: list[TocEntry], record: int) -> str:
    """Location of a page in the volume, e.g. 'Werke > Romane und Novellen > Die Leiden des jungen Werther'."""
    if not entries or entries[0].record is None:
        return ""
    crumbs = [e.title for e in breadcrumb(entries, entry_for_record(entries, record))]
    return " > ".join(crumbs[1:])


@dataclass
class SemanticStatus:
    volume_id: str
    state: str  # missing | queued | building | ready | stale | error
    done: int = 0
    total: int = 0
    chunks: int = 0
    model: str = DEFAULT_MODEL
    error: str | None = None


class SemanticIndex:
    def __init__(self, index_dir: Path | None = None, model_name: str = DEFAULT_MODEL):
        self.dir = (index_dir or default_index_dir()) / "semantic"
        self.model_name = model_name
        self._model = None
        self._model_lock = threading.Lock()
        self._lock = threading.Lock()
        self._jobs: dict[str, SemanticStatus] = {}  # queued / building / failed
        self._queue: queue.Queue[tuple[str, Path, Path]] = queue.Queue()
        self._worker: threading.Thread | None = None

    # ---- model -------------------------------------------------------------------------------
    def _embedder(self):
        with self._model_lock:
            if self._model is None:
                from fastembed import TextEmbedding  # heavy import, only when actually used

                cache = self.dir.parent / "fastembed"
                self._model = TextEmbedding(self.model_name, cache_dir=str(cache))
            return self._model

    def embed(self, texts: list[str], is_query: bool = False) -> list[list[float]]:
        q, p = _PREFIXES.get(self.model_name, ("", ""))
        prefix = q if is_query else p
        model = self._embedder()
        with self._model_lock:
            return [v.tolist() for v in model.embed([prefix + t for t in texts], batch_size=_BATCH)]

    # ---- status ------------------------------------------------------------------------------
    def _meta_path(self, volume_id: str) -> Path:
        return self.dir / f"{volume_id.upper()}.json"

    def _read_meta(self, volume_id: str) -> dict[str, Any] | None:
        try:
            return json.loads(self._meta_path(volume_id).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None

    @staticmethod
    def _fingerprint(dki_path: Path) -> str:
        st = dki_path.stat()
        return f"{st.st_size}:{int(st.st_mtime)}"

    def status(self, volume_id: str, dki_path: Path) -> SemanticStatus:
        with self._lock:
            job = self._jobs.get(volume_id)
            if job is not None and job.state in ("queued", "building"):
                return SemanticStatus(**asdict(job))
        meta = self._read_meta(volume_id)
        if meta is None:
            if job is not None:  # failed build
                return SemanticStatus(**asdict(job))
            return SemanticStatus(volume_id, "missing", model=self.model_name)
        fresh = meta["fingerprint"] == self._fingerprint(dki_path) and meta["model"] == self.model_name
        return SemanticStatus(
            volume_id,
            "ready" if fresh else "stale",
            done=meta["records"],
            total=meta["records"],
            chunks=meta["chunks"],
            model=meta["model"],
        )

    # ---- build -------------------------------------------------------------------------------
    def start_build(self, volume_id: str, dki_path: Path, volume_dir: Path) -> SemanticStatus:
        with self._lock:
            job = self._jobs.get(volume_id)
            if job is not None and job.state in ("queued", "building"):
                return SemanticStatus(**asdict(job))
            self._jobs[volume_id] = SemanticStatus(volume_id, "queued", model=self.model_name)
            self._queue.put((volume_id, dki_path, volume_dir))
            if self._worker is None or not self._worker.is_alive():
                self._worker = threading.Thread(target=self._run, daemon=True, name="semantic-index")
                self._worker.start()
            return SemanticStatus(**asdict(self._jobs[volume_id]))

    def _run(self) -> None:
        while True:
            try:
                volume_id, dki_path, volume_dir = self._queue.get(timeout=30)
            except queue.Empty:
                return
            st = self._jobs[volume_id]
            st.state = "building"
            try:
                self._build(volume_id, dki_path, volume_dir, st)
                with self._lock:
                    self._jobs.pop(volume_id, None)
            except Exception as exc:
                logger.exception("semantic index %s failed", volume_id)
                st.state, st.error = "error", str(exc)

    def _build(self, volume_id: str, dki_path: Path, volume_dir: Path, st: SemanticStatus) -> None:
        import lancedb
        import pyarrow as pa

        self.dir.mkdir(parents=True, exist_ok=True)
        db = lancedb.connect(str(self.dir))
        entries = load_toc(volume_dir)
        dim = len(self.embed(["Probe"])[0])
        schema = pa.schema(
            [
                pa.field("id", pa.string()),
                pa.field("volume_id", pa.string()),
                pa.field("record", pa.int32()),
                pa.field("work", pa.string()),
                pa.field("text", pa.string()),
                pa.field("vector", pa.list_(pa.float32(), dim)),
            ]
        )
        table_name = f"{volume_id.upper()}_{int(time.time())}"
        table = db.create_table(table_name, schema=schema, mode="overwrite")
        pending: list[dict[str, Any]] = []
        chunks_total = 0

        def flush() -> None:
            nonlocal chunks_total
            if not pending:
                return
            vectors = self.embed([row["text"] for row in pending])
            for row, vec in zip(pending, vectors, strict=True):
                row["vector"] = vec
            table.add(pending)
            chunks_total += len(pending)
            st.chunks = chunks_total
            pending.clear()

        with TextDki(dki_path) as dki:
            st.total = dki.count
            for k in range(dki.count):
                try:
                    text = dki.decode_record(k).text
                except DkiFormatError as exc:
                    logger.warning("semantic %s: skipping record %d: %s", volume_id, k, exc)
                    continue
                work = work_title(entries, k)
                for n, chunk in enumerate(chunk_text(text)):
                    pending.append(
                        {"id": f"{volume_id}:{k}:{n}", "volume_id": volume_id, "record": k, "work": work, "text": chunk}
                    )
                if len(pending) >= 4 * _BATCH:
                    flush()
                st.done = k + 1
            flush()
            records = dki.count

        old = self._read_meta(volume_id)
        meta = {
            "table": table_name,
            "fingerprint": self._fingerprint(dki_path),
            "model": self.model_name,
            "records": records,
            "chunks": chunks_total,
        }
        tmp = self._meta_path(volume_id).with_suffix(".tmp")
        tmp.write_text(json.dumps(meta), encoding="utf-8")
        os.replace(tmp, self._meta_path(volume_id))
        if old and old.get("table") != table_name:
            try:
                db.drop_table(old["table"])
            except Exception as exc:  # stale table is only wasted disk
                logger.warning("could not drop old table %s: %s", old["table"], exc)
        logger.info("semantic index %s built: %d records, %d chunks", volume_id, records, chunks_total)

    # ---- search ------------------------------------------------------------------------------
    def search(self, query: str, volume_ids: list[str], limit: int = 10) -> list[dict[str, Any]]:
        """Nearest chunks across the given (ready) volumes, best first: score = cosine similarity."""
        import lancedb

        tables = [(v, m["table"]) for v in volume_ids if (m := self._read_meta(v)) and m["model"] == self.model_name]
        if not tables or not query.strip():
            return []
        db = lancedb.connect(str(self.dir))
        qv = self.embed([query], is_query=True)[0]
        hits: list[dict[str, Any]] = []
        for volume_id, table_name in tables:
            rows = db.open_table(table_name).search(qv).metric("cosine").limit(limit).to_list()
            for r in rows:
                hits.append(
                    {
                        "volume_id": volume_id,
                        "record": int(r["record"]),
                        "work": r["work"],
                        "text": r["text"],
                        "score": round(1.0 - float(r["_distance"]), 4),
                    }
                )
        hits.sort(key=lambda h: -h["score"])
        return hits[:limit]
