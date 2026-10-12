"""Hermetic tests for TOC parsing, the FTS index and the reader REST API (synthetic volume)."""

import struct
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from directmedia_mcp import reader_api
from directmedia_mcp.dki_text import find_text_dki
from directmedia_mcp.dki_tree import breadcrumb, entry_for_record, load_toc
from directmedia_mcp.library import DirectmediaLibrary
from directmedia_mcp.search_index import HIT_END, HIT_START, SearchIndex, to_match_query
from tests.test_dki_text import END, build_a, word

PAGES = [
    "Werke",
    "Die Leiden des jungen Werther",
    "Lotte stand an der Tür",
    "Faust Der Tragödie erster Teil",
    "Habe nun ach Philosophie",
]
TOC_LINES = ["Goethe", " Werke", "  Werther", "  Faust"]
# 1-based END records of lines 1..3 (Werke ends at 1, Werther at 3, Faust at 5)
TOC_ENDS = [1, 3, 5]


def page(text: str) -> bytes:
    body = b""
    for i, w in enumerate(text.split()):
        body += word(w) + (b"\x00\x01" if i < len(text.split()) - 1 else b"")
    return body + END


@pytest.fixture
def library(tmp_path: Path) -> Path:
    data = tmp_path / "DB004" / "Data"
    data.mkdir(parents=True)
    (data / "TEXT.DKI").write_bytes(build_a([page(p) for p in PAGES]))
    (data / "TREE.DKI").write_bytes("\r\n".join(TOC_LINES).encode("cp1252") + b"\r\n")
    dka = struct.pack("<HI2I", 2, 2, 5, 9)  # an unrelated level block first
    dka += struct.pack(f"<HI{len(TOC_ENDS)}I", len(TOC_ENDS), 2, *TOC_ENDS)
    (data / "TREE.DKA").write_bytes(dka)
    (data / "DIGIBIB.TXT").write_bytes(b"[Default]\r\nCaption=Digitale Bibliothek Band 4: Goethe\r\n")
    return tmp_path


def test_toc_records_parents_and_breadcrumb(library: Path):
    toc = load_toc(library / "DB004")
    assert [(e.title, e.level, e.record, e.parent) for e in toc] == [
        ("Goethe", 0, 0, None),
        ("Werke", 1, 0, 0),
        ("Werther", 2, 0, 1),  # line 2 starts at TOC_ENDS[0] - 1
        ("Faust", 2, 2, 1),
    ]
    assert toc[1].child_count == 2
    here = entry_for_record(toc, 4)
    assert [e.title for e in breadcrumb(toc, here)] == ["Goethe", "Werke", "Faust"]


def test_short_title_derived_from_caption(library: Path):
    assert DirectmediaLibrary(str(library)).get_volume_info("DB004").short_title == "Goethe"


def test_match_query_quotes_words_and_keeps_phrases_and_prefixes():
    assert to_match_query('Werther "junge Leiden" tugend*') == '"Werther" "junge Leiden" "tugend"*'
    assert to_match_query('"') == ""


def test_index_build_and_search(library: Path, tmp_path: Path):
    ix = SearchIndex(tmp_path / "idx")
    dki = find_text_dki(library / "DB004")
    assert ix.status("DB004", dki).state == "missing"
    ix.start_build("DB004", dki)
    for _ in range(100):
        if ix.status("DB004", dki).state != "building":
            break
        time.sleep(0.05)
    assert ix.status("DB004", dki).state == "ready"
    res = ix.search("DB004", "lotte")
    assert res["total"] == 1
    assert res["hits"][0]["record"] == 2
    assert f"{HIT_START}Lotte{HIT_END}" in res["hits"][0]["snippet"]
    assert ix.search("DB004", "philo*")["hits"][0]["record"] == 4


def test_reader_api_end_to_end(library: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from directmedia_mcp.server import app  # importing server registers its own provider; override after

    lib = DirectmediaLibrary(str(library))
    monkeypatch.setattr(reader_api, "index", SearchIndex(tmp_path / "idx"))
    monkeypatch.setattr(reader_api, "_library_provider", lambda: lib)
    reader_api._toc.cache_clear()

    client = TestClient(app)
    vols = client.get("/api/v1/reader/volumes").json()
    assert vols[0]["id"] == "DB004" and vols[0]["records"] == 5 and vols[0]["index_state"] == "missing"

    top = client.get("/api/v1/reader/volumes/DB004/toc").json()
    assert top["parent"] == 0  # the single root line is skipped
    assert [e["title"] for e in top["entries"]] == ["Werke"]
    kids = client.get("/api/v1/reader/volumes/DB004/toc", params={"parent": 1}).json()
    assert [(e["title"], e["record"]) for e in kids["entries"]] == [("Werther", 0), ("Faust", 2)]

    rec = client.get("/api/v1/reader/volumes/DB004/records/3").json()
    assert rec["text"] == "Faust Der Tragödie erster Teil"
    assert (rec["prev"], rec["next"], rec["total"]) == (2, 4, 5)
    assert [b["title"] for b in rec["breadcrumb"]] == ["Goethe", "Werke", "Faust"]

    assert client.get("/api/v1/reader/volumes/DB004/records/99").status_code == 404
    assert client.get("/api/v1/reader/volumes/nope!/toc").status_code == 400

    not_yet = client.get("/api/v1/reader/search", params={"q": "Lotte"}).json()
    assert not_yet["not_indexed"] == ["DB004"] and not_yet["total"] == 0

    client.post("/api/v1/reader/index/DB004")
    for _ in range(100):
        if client.get("/api/v1/reader/index").json()[0]["state"] == "ready":
            break
        time.sleep(0.05)
    found = client.get("/api/v1/reader/search", params={"q": "Lotte"}).json()
    assert found["total"] == 1
    assert found["hits"][0]["record"] == 2
    assert found["hits"][0]["breadcrumb"] == ["Werke", "Faust"]
