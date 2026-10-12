"""Decoder for Directmedia Digitale Bibliothek TEXT.DKI files.

TEXT.DKI is not compressed. It is an offset table followed by records; each record is a
stream of byte-coded tokens (words, spacing, line breaks, layout and metadata ops).
Token sizes come from Digibib5.exe's own table (int32[0xB5] at VA 0x00763554, used by the
line scanner FUN_00614bb4). See docs/DKI_FORMAT.md for the full specification.

File layouts:
- family "A" (v0, oldest volumes):  u32 count, u32 offsets[count]; record = u16 len + tokens
- family "M" (v2 / v4):             u32 0x001924CC, u32 version, u32 count, u32 offsets[count];
                                    record = u16 body_len, u16, u16 + tokens
Every record ends with token 0x03. The last record runs to end of file.
"""

import mmap
import re
import struct
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

MAGIC = 0x001924CC

# Token sizes (opcode byte included) for opcodes 0x00..0xB4; higher bytes are not opcodes.
SIZE: tuple[int, ...] = (
    (2, 1, 1, 1, 1, 1, 1, 1, 2, 1, 5, 1, 1, 2, 1, 3, 3, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 1, 3, 1, 1, 1)
    + (1,) * 32
    + (2,) * 64
    + (5, 2, 2, 1, 1, 2, 5, 1, 2, 2, 5, 1, 1, 1, 1, 1, 1, 1, 1, 1, 3, 9, 1, 1, 1, 1, 1, 1, 3, 1, 5, 1)
    + (2, 4, 1, 1, 1, 5, 1, 1, 1, 1, 1, 1, 1, 1, 1, 5, 1, 1, 3, 5, 1)
)
# Variable-length tokens: offset of the length byte. Total size = SIZE[op] + length + 1.
LENPOS: dict[int, int] = {
    0x01: 1, 0xAA: 1, 0xAB: 1, 0x87: 1, 0x0B: 1, 0x0E: 1, 0x13: 1, 0x14: 1, 0x96: 1, 0xA2: 1,
    0x0A: 5, 0x86: 5, 0x80: 5, 0xB3: 5, 0xA0: 2, 0xA5: 6,
}  # fmt: skip
WORD_OPS = frozenset({0x01, 0xAA})  # length bit 7 = "space after this word"

OP_SPACING = 0x00  # 1 arg: horizontal space; at line start it is an indent
OP_LINE_END = 0x02
OP_END = 0x03
OP_PAGE = 0x0F  # u16 print-edition page number
OP_SOURCE = 0x0E  # length-prefixed source file path of the original text
OP_HYPHEN = (0x15, 0xAC)  # word before it ends in a print hyphenation
OP_SPACE = 0x1B
OP_LINE_BREAK = 0x8B

_MULTI_NL = re.compile(r"\n{3,}")
_TRAIL_WS = re.compile(r"[ \t]+\n")


class DkiFormatError(ValueError):
    """Raised when a TEXT.DKI file or record does not match the known format."""


@dataclass
class DecodedRecord:
    """Plain text of one record plus the metadata tokens found in it."""

    index: int
    text: str
    source: str | None = None
    pages: list[int] = field(default_factory=list)


def find_text_dki(volume_dir: Path) -> Path | None:
    """Locate Data/TEXT.DKI case-insensitively (volumes mix 'TEXT.DKI' and 'Text.dki')."""
    if not volume_dir.is_dir():
        return None
    for data in volume_dir.iterdir():
        if data.is_dir() and data.name.lower() == "data":
            for f in data.iterdir():
                if f.name.lower() == "text.dki":
                    return f
    return None


def iter_tokens(rec: bytes | memoryview, start: int) -> Iterator[tuple[int, int, int]]:
    """Yield (opcode, offset, size) for each token from start; raises on malformed input."""
    i, end = start, len(rec)
    while i < end:
        op = rec[i]
        if op >= len(SIZE):
            raise DkiFormatError(f"invalid opcode 0x{op:02x} at {i}")
        size = SIZE[op]
        lp = LENPOS.get(op)
        if lp is not None:
            if i + lp >= end:
                raise DkiFormatError(f"truncated token 0x{op:02x} at {i}")
            ln = rec[i + lp]
            if op in WORD_OPS:
                ln &= 0x7F
            size += ln + 1
        yield op, i, size
        i += size


class TextDki:
    """Random access to the records of one TEXT.DKI file (memory-mapped, read-only)."""

    def __init__(self, path: str | Path, encoding: str = "cp1252"):
        self.path = Path(path)
        self.encoding = encoding
        self._fh = self.path.open("rb")
        try:
            self._mm = mmap.mmap(self._fh.fileno(), 0, access=mmap.ACCESS_READ)
        except ValueError as exc:  # empty file
            self._fh.close()
            raise DkiFormatError(f"{self.path} is empty") from exc
        d0, d1 = struct.unpack_from("<2I", self._mm, 0)
        if d0 == MAGIC:
            self.family, self.version = "M", d1
            self.count = struct.unpack_from("<I", self._mm, 8)[0]
            table, self.header_size = 12, 6
        else:
            self.family, self.version = "A", 0
            self.count, table, self.header_size = d0, 4, 2
        if table + 4 * self.count > len(self._mm):
            self.close()
            raise DkiFormatError(f"{self.path}: offset table ({self.count} entries) exceeds file size")
        self._offsets = struct.unpack_from(f"<{self.count}I", self._mm, table)

    def close(self) -> None:
        self._mm.close()
        self._fh.close()

    def __enter__(self) -> "TextDki":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def raw_record(self, index: int) -> bytes:
        if not 0 <= index < self.count:
            raise IndexError(f"record {index} out of range 0..{self.count - 1}")
        start = self._offsets[index]
        end = self._offsets[index + 1] if index + 1 < self.count else len(self._mm)
        return self._mm[start:end]

    def decode_record(self, index: int) -> DecodedRecord:
        rec = self.raw_record(index)
        out: list[str] = []
        source: str | None = None
        pages: list[int] = []
        line_start = True
        pending_space = False
        joining = False  # inside a print hyphenation: swallow the break and indent

        for op, i, size in iter_tokens(rec, self.header_size):
            if op in WORD_OPS:
                if pending_space and not line_start:
                    out.append(" ")
                ln_byte = rec[i + 1]
                out.append(rec[i + 2 : i + size].decode(self.encoding, "replace"))
                pending_space = bool(ln_byte & 0x80) and self.family == "M"
                line_start = joining = False
            elif op in OP_HYPHEN:
                if out and out[-1].endswith("-"):
                    out[-1] = out[-1][:-1]
                    joining = True
                pending_space = False
            elif op in (OP_LINE_END, OP_LINE_BREAK):
                if not joining:
                    out.append("\n")
                    line_start = True
                pending_space = False
            elif op in (OP_SPACE, OP_SPACING):
                if not line_start and not joining:
                    pending_space = True
            elif op == OP_PAGE:
                pages.append(struct.unpack_from("<H", rec, i + 1)[0])
            elif op == OP_SOURCE and source is None:
                source = rec[i + 2 : i + size].decode(self.encoding, "replace")
            elif op == OP_END:
                break

        text = _TRAIL_WS.sub("\n", "".join(out))
        text = _MULTI_NL.sub("\n\n", text).strip("\n")
        return DecodedRecord(index=index, text=text, source=source, pages=pages)
