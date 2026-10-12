# TEXT.DKI format (Directmedia Digitale Bibliothek)

Status: **decoded and verified** (2026-10-12). Reference implementation: `src/directmedia_mcp/dki_text.py`.
Verification: `scripts/dki_gate.py` parses every record of a mounted library.

## Summary

`TEXT.DKI` holds a volume's full text. It is **not compressed and not encrypted**: an offset table, followed by
records that are byte-coded token streams. Words are stored as plain CP1252 strings.

Earlier attempts in this repo failed because they treated the first ~400-700 KB of the file, which is the offset table
plus zero padding, as packed data.

## File layout

Two header families exist. Family A is used by the oldest volumes; family M by everything from about DB013 onward.

| Family | Header | Offset table | Record header |
|--------|--------|--------------|---------------|
| A ("v0") | `u32 count` | `u32 offsets[count]` at byte 4 | `u16 total_len` (includes these 2 bytes) |
| M ("v2" / "v4") | `u32 0x001924CC`, `u32 version`, `u32 count` | `u32 offsets[count]` at byte 12 | `u16 body_len`, `u16 ?`, `u16 ?` (6 bytes) |

- All integers are little-endian.
- Offsets are absolute file positions and ascending. The table is zero-padded up to the first record, which sits at a
  fixed position (`0x67200` / `0x67204`, `0xAFC84`, ...).
- There is no sentinel: the last record runs to end of file.
- Every record ends with token `0x03`.
- A record is roughly one printed page of the source edition.

Volumes on the reference library: family A = DB002-DB011 (9 volumes); M v2 = DB013-DB031 (11); M v4 = the rest (53).

## Tokens

Each token starts with an opcode byte `op` (valid range `0x00`-`0xB4`). Its total size is `SIZE[op]`, the `int32[0xB5]`
table at VA `0x00763554` in `Digibib5.exe` (see `SIZE` in `dki_text.py`). Variable-length tokens also carry a length
byte `L` at a fixed position; their size is `SIZE[op] + L + 1`. This is exactly how the reader's line scanner
`FUN_00614bb4` advances.

| Length byte at | Opcodes |
|----------------|---------|
| +1 | `01`, `AA` (words), `AB`, `87`, `0B` (image file), `0E` (source path), `13` (sigil), `14`, `96`, `A2` |
| +2 | `A0` |
| +5 | `0A`, `86` (embedded object), `80` (anchor + label), `B3` |
| +6 | `A5` |

For word tokens (`01`, `AA`), bit 7 of `L` is a **"space after this word"** flag (family M); the length is `L & 0x7F`.

### Semantics needed for plain text

| Op | Meaning |
|----|---------|
| `01` / `AA` | Word (CP1252). Family M: bit 7 of length means a trailing space |
| `00 xx` | Horizontal spacing; an indent when it appears at the start of a line, otherwise a space (family A uses `00 01` between words) |
| `1B` | Space |
| `02` | End of line / paragraph |
| `8B` | Line break inside a paragraph (verse, family M) |
| `15`, `AC` | The preceding word ends in a print hyphenation `-`: drop the hyphen and join it with the next word across the line break |
| `03` | End of record |

### Metadata tokens (not text)

| Op | Meaning |
|----|---------|
| `0E` + string | Source file of the original text (e.g. `q:\digibib\5less\texte\less+001.txt`) |
| `13` + string | Sigil of the print edition (e.g. `rororo-Lessing`, `Nietzsche-W Bd. 3`) |
| `0F u16` | Page number in the print edition (the "Seitenkonkordanz") |
| `10 u16`, `AF u32`, `89 xx` | Structure / section ids (not fully mapped) |
| `80 u32 + string` | Anchor with label (illustration or footnote target); `11 ... 12` brackets the visible footnote mark |
| `0B` + string, `0A`/`86` | Image reference / embedded object |
| `08 xx`, `98`/`99`, `9C`/`9D`, `A1`, `A6`, `A7` ... | Formatting (bold, centred, font, alignment) |

Opcodes `0x20`-`0x7F` are defined in the size table but never occur in the text of any volume checked.

## Known gaps

- **DB006** (Russian chronicle volume, `CDMajor=1003`): Cyrillic letters are stored as `cp1251 byte - 0xAA` inside a
  font-switched run, so plain CP1252 decoding yields Latin gibberish. Needs the font-switch tokens mapped.
- **DBSO06**, record 881: a word longer than 127 bytes collides with the space flag; one record fails.
- Structure tokens (`10`, `AF`, `89`, `A1`, ...) are skipped. `TREE.DKI` (the table of contents) is a separate file and
  not decoded yet.

## Verification

1. **Full-library gate:** 2,281,483 of 2,281,484 records across 73 volumes parse to their exact boundary.
2. **Known-plaintext check** against TextGrid's independent TEI transcription (6-word shingle recall, speaker labels
   excluded):
   - DB005 (family A) vs *Minna von Barnhelm* `textgrid:rjhb.0`: **98.12%**.
   - DB074 (family M v4) vs *Max und Moritz* `textgrid:106p1.0`: **97.90%**.
   - The remaining misses are headings TextGrid adds or duplicates, plus TextGrid's own typos.

## How it was found

1. Reading the hexdump of the first record past the offset table showed plain words: `01 0b "Philosophie"`.
2. Ghidra 12 headless (`analyzeHeadless` + a `DecompileList.java` postScript, now in reversing-mcp `ghidra_scripts/`)
   decompiled `FUN_00614bb4`. Its advance logic indexes `DAT_00763554[op]` and adds length bytes for a fixed set of
   opcodes.
3. The table was read straight from the EXE's `DATA` section and validated by the full-library gate.
