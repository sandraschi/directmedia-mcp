"""REST API for the web reader: volumes, table of contents, paged text and full-text search."""

import re
import sqlite3
from collections.abc import Callable
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from .dki_text import DkiFormatError, TextDki, find_text_dki
from .dki_tree import TocEntry, breadcrumb, entry_for_record, load_toc
from .library import DirectmediaLibrary
from .logging_config import get_logger
from .search_index import HIT_END, HIT_START, SearchIndex

logger = get_logger("directmedia_mcp.reader_api")

router = APIRouter(prefix="/api/v1/reader", tags=["reader"])
_VOLUME_ID = re.compile(r"^[A-Za-z0-9_-]{2,16}$")
_library_provider: Callable[[], DirectmediaLibrary | None] = lambda: None  # noqa: E731
index = SearchIndex()


def set_library_provider(provider: Callable[[], DirectmediaLibrary | None]) -> None:
    global _library_provider
    _library_provider = provider


def _library() -> DirectmediaLibrary:
    lib = _library_provider()
    if lib is None:
        raise HTTPException(status_code=409, detail="Library not initialized. Set the library path in Settings.")
    return lib


def _volume_dir(volume_id: str) -> Path:
    if not _VOLUME_ID.match(volume_id):
        raise HTTPException(status_code=400, detail=f"Invalid volume id {volume_id!r}")
    path = _library().library_path / volume_id
    if not path.is_dir():
        raise HTTPException(status_code=404, detail=f"Volume {volume_id} not found")
    return path


def _dki_path(volume_id: str) -> Path:
    path = find_text_dki(_volume_dir(volume_id))
    if path is None:
        raise HTTPException(status_code=404, detail=f"Volume {volume_id} has no TEXT.DKI")
    return path


@lru_cache(maxsize=8)
def _toc(volume_dir: str) -> list[TocEntry]:
    return load_toc(Path(volume_dir))


def _entry(e: TocEntry) -> dict[str, Any]:
    return {"index": e.index, "title": e.title, "level": e.level, "record": e.record, "child_count": e.child_count}


@router.get("/volumes")
def volumes() -> list[dict[str, Any]]:
    """All volumes with text: title, record count, format, TOC and index state."""
    lib = _library()
    out = []
    for vol in lib.list_volumes():
        path = find_text_dki(Path(vol.path))
        if path is None:
            continue
        try:
            with TextDki(path) as dki:
                records, fmt = dki.count, f"{dki.family}v{dki.version}"
        except (DkiFormatError, OSError) as exc:
            logger.warning("Skipping volume %s: %s", vol.id, exc)
            continue
        out.append(
            {
                "id": vol.id,
                "title": vol.title,
                "short_title": vol.short_title,
                "size_mb": vol.size_mb,
                "records": records,
                "format": fmt,
                "index_state": index.status(vol.id, path).state,
            }
        )
    return out


@router.get("/volumes/{volume_id}/toc")
def toc(volume_id: str, parent: int | None = Query(None, ge=0)) -> dict[str, Any]:
    """Children of a TOC node (parent omitted: the top level), plus the parent's breadcrumb."""
    entries = _toc(str(_volume_dir(volume_id)))
    if not entries:
        return {"volume_id": volume_id, "parent": None, "entries": [], "breadcrumb": [], "has_record_map": False}
    if parent is not None and parent >= len(entries):
        raise HTTPException(status_code=404, detail=f"TOC entry {parent} not found")
    children = [e for e in entries if e.parent == parent]
    # A single root line (the volume title) is skipped so the top level shows real sections.
    if parent is None and len(children) == 1 and children[0].child_count:
        parent = children[0].index
        children = [e for e in entries if e.parent == parent]
    return {
        "volume_id": volume_id,
        "parent": parent,
        "entries": [_entry(e) for e in children],
        "breadcrumb": [_entry(e) for e in breadcrumb(entries, parent)],
        "has_record_map": entries[0].record is not None,
    }


@router.get("/volumes/{volume_id}/records/{record}")
def read_record(volume_id: str, record: int) -> dict[str, Any]:
    """One record (about one printed page) of decoded text with navigation context."""
    path = _dki_path(volume_id)
    try:
        with TextDki(path) as dki:
            if not 0 <= record < dki.count:
                raise HTTPException(status_code=404, detail=f"Record {record} out of range 0..{dki.count - 1}")
            rec = dki.decode_record(record)
            total = dki.count
    except DkiFormatError as exc:
        raise HTTPException(status_code=422, detail=f"Record {record} could not be decoded: {exc}") from exc
    entries = _toc(str(_volume_dir(volume_id)))
    here = entry_for_record(entries, record) if entries and entries[0].record is not None else None
    return {
        "volume_id": volume_id,
        "record": record,
        "total": total,
        "text": rec.text,
        "print_pages": rec.pages,
        "source": rec.source,
        "prev": record - 1 if record > 0 else None,
        "next": record + 1 if record + 1 < total else None,
        "breadcrumb": [_entry(e) for e in breadcrumb(entries, here)],
    }


@router.get("/index")
def index_status() -> list[dict[str, Any]]:
    lib = _library()
    out = []
    for vol in lib.list_volumes():
        path = find_text_dki(Path(vol.path))
        if path is not None:
            st = index.status(vol.id, path)
            out.append({"volume_id": vol.id, "state": st.state, "done": st.done, "total": st.total, "error": st.error})
    return out


@router.post("/index/{volume_id}")
def build_index(volume_id: str) -> dict[str, Any]:
    """Start building the full-text index of one volume (background; poll GET /index)."""
    path = _dki_path(volume_id)
    st = index.status(volume_id, path)
    if st.state == "ready":
        return {"volume_id": volume_id, "state": "ready", "done": st.done, "total": st.total}
    st = index.start_build(volume_id, path)
    return {"volume_id": volume_id, "state": st.state, "done": st.done, "total": st.total}


@router.get("/search")
def search(
    q: str = Query(..., min_length=1, max_length=200),
    volumes: str | None = Query(None, description="Comma-separated volume ids; default: all indexed volumes"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    """Ranked full-text search over indexed volumes; unindexed requested volumes are reported, not scanned."""
    lib = _library()
    wanted = [v.strip() for v in volumes.split(",") if v.strip()] if volumes else [v.id for v in lib.list_volumes()]
    hits: list[dict[str, Any]] = []
    totals: dict[str, int] = {}
    not_indexed: list[str] = []
    for vid in wanted:
        path = _dki_path(vid) if volumes else find_text_dki(lib.library_path / vid)
        if path is None:
            continue
        if index.status(vid, path).state != "ready":
            not_indexed.append(vid)
            continue
        # fetch enough from each volume to fill the requested window after merging
        try:
            res = index.search(vid, q, limit=offset + limit)
        except sqlite3.OperationalError as exc:
            raise HTTPException(status_code=400, detail=f"Invalid search query: {exc}") from exc
        totals[vid] = res["total"]
        hits.extend({"volume_id": vid, **h} for h in res["hits"])
    hits.sort(key=lambda h: -h["score"])
    window = hits[offset : offset + limit]
    for h in window:
        entries = _toc(str(lib.library_path / h["volume_id"]))
        here = entry_for_record(entries, h["record"]) if entries and entries[0].record is not None else None
        h["breadcrumb"] = [e.title for e in breadcrumb(entries, here)][1:]
    return {
        "query": q,
        "total": sum(totals.values()),
        "totals": totals,
        "offset": offset,
        "hits": window,
        "not_indexed": not_indexed,
        "markers": [HIT_START, HIT_END],
    }
