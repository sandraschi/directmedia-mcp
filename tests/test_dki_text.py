"""Tests for the TEXT.DKI decoder.

Hermetic tests build tiny synthetic files in both on-disk families. The integration test
runs only when the real library is mounted (DIRECTMEDIA_LIBRARY_PATH or the default L: path).
"""

import os
import struct
from pathlib import Path

import pytest

from directmedia_mcp.dki_text import MAGIC, SIZE, DkiFormatError, TextDki, find_text_dki, iter_tokens
from directmedia_mcp.library import DirectmediaLibrary


def word(text: str, space_after: bool = False) -> bytes:
    raw = text.encode("cp1252")
    return bytes([0x01, len(raw) | (0x80 if space_after else 0)]) + raw


def lstr(op: int, text: str) -> bytes:
    raw = text.encode("cp1252")
    return bytes([op, len(raw)]) + raw


SPACE_A = b"\x00\x01"  # family A spacing token used between words
END = b"\x03"


def build_a(records: list[bytes]) -> bytes:
    """Family A: u32 count, u32 offsets[], record = u16 total_len + body."""
    table = 4 + 4 * len(records)
    blobs = [struct.pack("<H", len(body) + 2) + body for body in records]
    offs, pos = [], table
    for b in blobs:
        offs.append(pos)
        pos += len(b)
    return struct.pack(f"<I{len(records)}I", len(records), *offs) + b"".join(blobs)


def build_m(records: list[bytes], version: int = 4) -> bytes:
    """Family M: magic, version, count, offsets[]; record = u16 body_len, u16, u16 + body."""
    table = 12 + 4 * len(records)
    blobs = [struct.pack("<3H", len(body), 0, 0) + body for body in records]
    offs, pos = [], table
    for b in blobs:
        offs.append(pos)
        pos += len(b)
    return struct.pack(f"<3I{len(records)}I", MAGIC, version, len(records), *offs) + b"".join(blobs)


def write_volume(tmp_path: Path, data: bytes, name: str = "Text.dki") -> Path:
    vol = tmp_path / "DB999"
    (vol / "Data").mkdir(parents=True)
    (vol / "Data" / name).write_bytes(data)
    return vol


def test_size_table_covers_opcodes_0_to_b4():
    assert len(SIZE) == 0xB5
    assert SIZE[0x01] == 1 and SIZE[0x0F] == 3 and SIZE[0xAF] == 5 and SIZE[0x95] == 9


def test_family_a_words_spaces_hyphenation_and_metadata(tmp_path):
    body = (
        lstr(0x0E, r"q:\digibib\5less\texte\less+001.txt")
        + b"\x0f\x20\x00"  # print page 32
        + word("Alles")
        + SPACE_A
        + word("voller")
        + SPACE_A
        + word("Ge-")
        + b"\x15\x02"  # hyphenation + line end: must join
        + word("stank.")
        + b"\x02\x00\x04"  # line end, then indent (not a space)
        + word("Neu")
        + END
    )
    vol = write_volume(tmp_path, build_a([body]), name="TEXT.DKI")
    with TextDki(find_text_dki(vol)) as d:
        assert (d.family, d.version, d.count) == ("A", 0, 1)
        rec = d.decode_record(0)
    assert rec.text == "Alles voller Gestank.\nNeu"
    assert rec.source == r"q:\digibib\5less\texte\less+001.txt"
    assert rec.pages == [32]


def test_family_m_trailing_space_flag_and_line_breaks(tmp_path):
    body = (
        word("Und", True)
        + word("aufgeschreckt", True)
        + word("aus")
        + b"\x8b"  # line break inside paragraph
        + b"\x00\x0c"  # indent at line start
        + word("halbem", True)
        + word("Schlummer")
        + b"\x02\x02\x02"  # paragraph end; runs of breaks collapse to one blank line
        + b"\xaf\x01\x00\x00\x00"  # fixed-size metadata op
        + b"\x80\x01\x00\x00\x00\x03I38"  # anchor: 4 bytes + length-prefixed label, not text
        + word("Ende")
        + END
    )  # fmt: skip
    vol = write_volume(tmp_path, build_m([body, word("zwei") + END]))
    with TextDki(find_text_dki(vol)) as d:
        assert (d.family, d.version, d.count) == ("M", 4, 2)
        assert d.decode_record(0).text == "Und aufgeschreckt aus\nhalbem Schlummer\n\nEnde"
        assert d.decode_record(1).text == "zwei"


def test_invalid_opcode_raises(tmp_path):
    vol = write_volume(tmp_path, build_m([word("ok") + b"\xdf" + END]))
    with TextDki(find_text_dki(vol)) as d, pytest.raises(DkiFormatError):
        d.decode_record(0)


def test_offset_table_larger_than_file_raises(tmp_path):
    vol = write_volume(tmp_path, struct.pack("<3I", MAGIC, 4, 10_000))
    with pytest.raises(DkiFormatError):
        TextDki(find_text_dki(vol))


def test_iter_tokens_sizes():
    rec = word("abc") + b"\x0f\x01\x00" + lstr(0x13, "Sigel") + END
    assert [(op, size) for op, _, size in iter_tokens(rec, 0)] == [(0x01, 5), (0x0F, 3), (0x13, 7), (0x03, 1)]


def test_library_get_text_content_pages_through_records(tmp_path):
    recs = [word(f"Seite{i}") + END for i in range(5)]
    write_volume(tmp_path, build_a(recs), name="TEXT.DKI")
    lib = DirectmediaLibrary(str(tmp_path))
    first = lib.get_text_content("DB999", 0, 10)
    assert first["content"].startswith("Seite0")
    assert first["total_records"] == 5
    nxt = lib.get_text_content("DB999", first["next_pos"], 10_000)
    assert nxt["next_pos"] is None
    assert nxt["content"].endswith("Seite4")
    assert "error" in lib.get_text_content("DB999", 99, 10)
    hits = lib.search_text("seite3", "DB999", 5)
    assert [h.position for h in hits] == [3]


LIBRARY = Path(os.getenv("DIRECTMEDIA_LIBRARY_PATH", r"L:\Multimedia Files\Written Word\Digitale Bibliothek"))


@pytest.mark.integration
@pytest.mark.skipif(not (LIBRARY / "DB005").is_dir(), reason="Digitale Bibliothek CDs not mounted")
@pytest.mark.parametrize(("volume", "needle"), [("DB005", "Minna von Barnhelm"), ("DB074", "Max und Moritz")])
def test_real_volume_decodes_every_record(volume, needle):
    with TextDki(find_text_dki(LIBRARY / volume)) as d:
        texts = [d.decode_record(k).text for k in range(d.count)]
    assert any(needle in t for t in texts)
