"""Table of contents of a Digitale Bibliothek volume: TREE.DKI (titles) + TREE.DKA (record map).

TREE.DKI is CP1252 text, one entry per CRLF line; the number of leading spaces is the depth.
Line 0 is the volume root.

TREE.DKA is a sequence of blocks `u16 count, u32 tag, u32 values[count]`. The block whose
count equals (number of lines - 1) maps lines to TEXT.DKI records: values[j] is the 1-based
*end* record of line j+1, so line i (i >= 2) starts at record values[i-2] - 1 and line 1
starts at record 0. Verified by locating each heading in its predicted record: 92-98% on
DB005/DB031/DB074 (misses are headings worded differently in the text).

Very large trees (DB050 Brockhaus, DB125 Deutsche Literatur; > 65535 lines) use a different,
multi-level TREE.DKA layout that is not decoded yet; their entries get record=None.
"""

import struct
from dataclasses import dataclass
from pathlib import Path


@dataclass
class TocEntry:
    index: int
    title: str
    level: int
    record: int | None  # start record in TEXT.DKI, None when the volume has no usable map
    parent: int | None
    child_count: int = 0


def _find(volume_dir: Path, name: str) -> Path | None:
    for data in volume_dir.iterdir() if volume_dir.is_dir() else ():
        if data.is_dir() and data.name.lower() == "data":
            for f in data.iterdir():
                if f.name.lower() == name:
                    return f
    return None


def _record_map(dka: bytes, entries: int) -> tuple[int, ...] | None:
    pos = 0
    while pos + 6 <= len(dka):
        count, _tag = struct.unpack_from("<HI", dka, pos)
        end = pos + 6 + 4 * count
        if end > len(dka):
            return None
        if count in (entries, entries + 1):  # DB013 carries one extra trailing value
            return struct.unpack_from(f"<{entries}I", dka, pos + 6)
        pos = end
    return None


def load_toc(volume_dir: Path) -> list[TocEntry]:
    """Parse the volume's TOC; returns [] when TREE.DKI is missing."""
    tree = _find(volume_dir, "tree.dki")
    if tree is None:
        return []
    lines = [ln for ln in tree.read_bytes().decode("cp1252", "replace").split("\r\n") if ln.strip()]
    dka_path = _find(volume_dir, "tree.dka")
    # u16 count: the map only exists for TOCs with fewer than 65536 lines
    ends = _record_map(dka_path.read_bytes(), len(lines) - 1) if dka_path and len(lines) > 1 else None

    entries: list[TocEntry] = []
    stack: list[int] = []  # indexes of the current ancestors
    for i, line in enumerate(lines):
        level = len(line) - len(line.lstrip(" "))
        if ends is None:
            record = None
        elif i <= 1:
            record = 0
        else:
            record = ends[i - 2] - 1
        while stack and entries[stack[-1]].level >= level:
            stack.pop()
        parent = stack[-1] if stack else None
        if parent is not None:
            entries[parent].child_count += 1
        entries.append(TocEntry(index=i, title=line.strip(), level=level, record=record, parent=parent))
        stack.append(i)
    return entries


def subtree_end(entries: list[TocEntry], index: int) -> int:
    """Index of the first entry after the subtree rooted at index."""
    level = entries[index].level
    j = index + 1
    while j < len(entries) and entries[j].level > level:
        j += 1
    return j


def entry_for_record(entries: list[TocEntry], record: int) -> int | None:
    """Deepest-last TOC entry whose start record is <= record (the reader's 'you are here')."""
    best = None
    for e in entries:
        if e.record is not None and e.record <= record:
            best = e.index
        elif e.record is not None and e.record > record:
            break
    return best


def breadcrumb(entries: list[TocEntry], index: int | None) -> list[TocEntry]:
    out: list[TocEntry] = []
    while index is not None:
        out.append(entries[index])
        index = entries[index].parent
    return out[::-1]
