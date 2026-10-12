"""Per-volume SQLite FTS5 full-text index over decoded TEXT.DKI records.

One database per volume (rowid = record index). Built on demand in a background thread;
written to a temp file and renamed into place, so a half-built index is never searched.
Index location: DIRECTMEDIA_INDEX_DIR, else %LOCALAPPDATA%/directmedia-mcp/index.
"""

import os
import re
import sqlite3
import threading
from contextlib import closing
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .dki_text import DkiFormatError, TextDki
from .logging_config import get_logger

logger = get_logger("directmedia_mcp.search_index")

INDEX_VERSION = 1
HIT_START, HIT_END = "\u0002", "\u0003"  # snippet highlight markers (split on these in the UI)
_BATCH = 2000
_WORD = re.compile(r"[^\s\"]+")


def default_index_dir() -> Path:
    env = os.getenv("DIRECTMEDIA_INDEX_DIR")
    if env:
        return Path(env)
    base = os.getenv("LOCALAPPDATA") or str(Path.home() / ".cache")
    return Path(base) / "directmedia-mcp" / "index"


def to_match_query(query: str) -> str:
    """User text -> FTS5 MATCH expression: every word must occur; "quoted phrases" kept; word* = prefix."""
    parts: list[str] = []
    for phrase, word in re.findall(r'"([^"]+)"|(\S+)', query):
        if phrase:
            parts.append('"' + phrase.replace('"', "") + '"')
        elif word:
            prefix = word.endswith("*")
            term = word.rstrip("*").replace('"', "")
            if term:
                parts.append(f'"{term}"' + ("*" if prefix else ""))
    return " ".join(parts)


@dataclass
class IndexStatus:
    volume_id: str
    state: str  # missing | building | ready | stale | error
    done: int = 0
    total: int = 0
    error: str | None = None


class SearchIndex:
    def __init__(self, index_dir: Path | None = None):
        self.dir = index_dir or default_index_dir()
        self._lock = threading.Lock()
        self._building: dict[str, IndexStatus] = {}
        self._errors: dict[str, IndexStatus] = {}  # last failed build per volume, cleared on retry

    def _db_path(self, volume_id: str) -> Path:
        return self.dir / f"{volume_id.upper()}.sqlite"

    @staticmethod
    def _fingerprint(dki_path: Path) -> str:
        st = dki_path.stat()
        return f"{INDEX_VERSION}:{st.st_size}:{int(st.st_mtime)}"

    def status(self, volume_id: str, dki_path: Path) -> IndexStatus:
        with self._lock:
            if volume_id in self._building:
                return IndexStatus(**asdict(self._building[volume_id]))
            failed = self._errors.get(volume_id)
        db = self._db_path(volume_id)
        if not db.exists():
            return IndexStatus(**asdict(failed)) if failed else IndexStatus(volume_id, "missing")
        try:
            with closing(sqlite3.connect(f"file:{db}?mode=ro", uri=True)) as con:
                fp, total = con.execute("SELECT fingerprint, records FROM meta").fetchone()
        except sqlite3.Error as exc:
            return IndexStatus(volume_id, "error", error=str(exc))
        state = "ready" if fp == self._fingerprint(dki_path) else "stale"
        return IndexStatus(volume_id, state, done=total, total=total)

    def start_build(self, volume_id: str, dki_path: Path) -> IndexStatus:
        """Start a background build unless one is already running for this volume."""
        with self._lock:
            if volume_id in self._building:
                return IndexStatus(**asdict(self._building[volume_id]))
            st = IndexStatus(volume_id, "building")
            self._building[volume_id] = st
            self._errors.pop(volume_id, None)
        threading.Thread(target=self._build, args=(volume_id, dki_path, st), daemon=True).start()
        return IndexStatus(**asdict(st))

    def _build(self, volume_id: str, dki_path: Path, st: IndexStatus) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        final = self._db_path(volume_id)
        tmp = final.with_suffix(".building")
        tmp.unlink(missing_ok=True)
        try:
            with TextDki(dki_path) as dki, closing(sqlite3.connect(tmp)) as con:
                st.total = dki.count
                con.execute("CREATE TABLE meta (fingerprint TEXT, records INTEGER)")
                con.execute("CREATE VIRTUAL TABLE pages USING fts5(text, tokenize='unicode61')")
                batch: list[tuple[int, str]] = []
                for k in range(dki.count):
                    try:
                        batch.append((k, dki.decode_record(k).text))
                    except DkiFormatError as exc:
                        logger.warning("index %s: skipping record %d: %s", volume_id, k, exc)
                    if len(batch) >= _BATCH:
                        con.executemany("INSERT INTO pages(rowid, text) VALUES (?, ?)", batch)
                        batch.clear()
                        st.done = k + 1
                con.executemany("INSERT INTO pages(rowid, text) VALUES (?, ?)", batch)
                con.execute("INSERT INTO meta VALUES (?, ?)", (self._fingerprint(dki_path), dki.count))
                con.execute("INSERT INTO pages(pages) VALUES ('optimize')")
                con.commit()
                st.done = dki.count
            os.replace(tmp, final)
            logger.info("index %s built: %d records -> %s", volume_id, st.total, final)
        except Exception as exc:
            logger.exception("index %s build failed", volume_id)
            st.state, st.error = "error", str(exc)
            tmp.unlink(missing_ok=True)
        finally:
            with self._lock:
                self._building.pop(volume_id, None)
                if st.state == "error":
                    self._errors[volume_id] = st

    def search(self, volume_id: str, query: str, limit: int = 20, offset: int = 0) -> dict[str, Any]:
        """Ranked hits in one ready volume: {total, hits: [{record, snippet, score}]}."""
        match = to_match_query(query)
        if not match:
            return {"total": 0, "hits": []}
        db = self._db_path(volume_id)
        with closing(sqlite3.connect(f"file:{db}?mode=ro", uri=True)) as con:
            total = con.execute("SELECT count(*) FROM pages WHERE pages MATCH ?", (match,)).fetchone()[0]
            rows = con.execute(
                "SELECT rowid, snippet(pages, 0, ?, ?, ' … ', 16), bm25(pages) FROM pages "
                "WHERE pages MATCH ? ORDER BY rank LIMIT ? OFFSET ?",
                (HIT_START, HIT_END, match, limit, offset),
            ).fetchall()
        return {
            "total": total,
            "hits": [{"record": r, "snippet": " ".join(s.split()), "score": round(-b, 3)} for r, s, b in rows],
        }
