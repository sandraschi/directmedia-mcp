# Directmedia MCP

<p align="center">
  <a href="https://github.com/casey/just"><img src="https://img.shields.io/badge/just-ready_to_go-7c5cfc?style=flat-square&logo=just&logoColor=white" alt="Just"></a>
  <a href="https://github.com/astral-sh/ruff"><img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json" alt="Ruff"></a>
  <a href="https://python.org"><img src="https://img.shields.io/badge/Python-3.13+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python"></a>
  <a href="https://github.com/PrefectHQ/fastmcp"><img src="https://img.shields.io/badge/FastMCP-3.2-7c5cfc?style=flat-square" alt="FastMCP"></a>
</p>

> **Status (2026-10-12): `TEXT.DKI` decoded.** Book text is extracted from 72 of 73 text volumes; 2,281,483 of
> 2,281,484 records pass the full-library gate, and spot checks against TextGrid's independent transcription match at
> 98%. Still open: the table-of-contents tree (`TREE.DKI`), the Russian volume DB006's character mapping, and the
> `INDEX.*` search files.

> 📖 **[Installation Guide](INSTALL.md)** — quick start, manual setup, and troubleshooting

FastMCP server aimed at giving agents access to the Directmedia Publishing **"Digitale Bibliothek"** CD-ROM/DVD collection.

## What this wraps

The **Digitale Bibliothek** was Directmedia Publishing's German e-book series (1990s-2000s): ~100+ volumes of literature,
philosophy and reference works, read with the proprietary `Digibib5.exe` reader. Each volume stores its content in
undocumented binary files (`TEXT.DKI`, `TREE.DKI`, `INDEX.*`, ...).

The public-domain part of the same corpus lives on today as the **zeno.org** online library, which TextGrid licensed and
converted to TEI XML (see [Public-domain texts without the CDs](#public-domain-texts-without-the-cds)).

## Current state (honest)

| Area | State |
|------|-------|
| Volume discovery (`list_volumes`, `get_volume_info`) | Works on a local library folder |
| `TREE.DKI` (table of contents) | Partial — on some volumes it is plain CP1252 text and reads fine |
| `TEXT.DKI` (book body text) | **Decoded** ([format spec](docs/DKI_FORMAT.md)); 72/73 volumes, DB006 (Russian) needs a font map |
| `get_text_content` | Real text, paged by record (about one printed page), with print page numbers and source file |
| `search_text` | Real text, but a linear scan; slow across the biggest volumes |
| EPUB export | Real text, one EPUB per volume (not yet split into works) |
| `INDEX.*`, `LINKS.*`, images, audio | Not analysed |

An earlier version of this README claimed text extraction worked when it did not. The loose `reverse_engineer_*.py` /
`*huffman*.py` scripts in the repo root are from that failed attempt and are kept only for reference.

## How TEXT.DKI was cracked

`TEXT.DKI` is **not compressed**. Earlier attempts treated the ~400 KB offset table at the start of the file as packed
data. The records behind it are byte-coded token streams: words in CP1252, spacing, line breaks, layout and metadata
tokens. The exact token sizes came from `Digibib5.exe` itself: Ghidra headless decompilation of the line scanner
(`FUN_00614bb4`) led to an `int32` size table at VA `0x00763554`. With that table, every record of every volume parses
to its exact boundary. Full spec: [docs/DKI_FORMAT.md](docs/DKI_FORMAT.md). Re-run the gate any time:

```powershell
uv run python scripts/dki_gate.py "L:\Multimedia Files\Written Word\Digitale Bibliothek"
```

## Public-domain texts without the CDs

If you only need **public-domain** works, you do not need to crack DKI at all:

- **zeno.org** — the online library derived from the same corpus.
- **[TextGrid Repository — Digitale Bibliothek](https://textgridrep.org)** — the zeno.org corpus as TEI XML
  (literature ~690 authors, philosophy ~250 authors, plus smaller collections). Annotated data and metadata are
  CC-BY 3.0, plain texts are public domain; credit "TextGrid".
  - Bulk download (texts only, ~390 MB): `https://textgridlab.org/download/digitale-bibliothek/literatur-nur-texte-2.zip`
  - Per-object export: `https://textgridlab.org/1.0/aggregator/{text|epub}/textgrid:<id>`

Copyrighted CD content (lexika such as Killy, editorial commentary, modern translations) is **not** on TextGrid.
For that you need the CDs and the DKI decoder. TextGrid's Digibib project covers the **literature** collection
(Lessing, Goethe, Busch...); philosophers such as Kant or Nietzsche are not in it.

The `textgrid` tool searches, reads and exports these editions without the CDs.

## MCP tools

| Tool | Purpose |
|------|---------|
| `set_library_path(path)` | Point the server at the local Digitale Bibliothek folder |
| `list_volumes()` | Enumerate volumes (DBxxx, DBSKxx, DBSOxx) |
| `get_volume_info(volume_id)` | Volume metadata and file inventory |
| `analyze_volume_structure(volume_id)` | File-format overview of a volume |
| `get_navigation_tree(volume_id)` | TOC from `TREE.DKI` (partial) |
| `search_text(query, volume_id, limit)` | Substring search over decoded text; `position` = record index |
| `get_text_content(volume_id, start_pos, length)` | Decoded text from record `start_pos`; page on with `next_pos` |
| `convert_volume_to_epub_file(volume_id, output_dir)` | One EPUB per volume from decoded text |
| `batch_convert_to_epub(output_dir, volume_ids)` | Same, for several volumes |
| `textgrid(operation, ...)` | Public-domain editions from TextGrid: `search`, `get_text`, `export_epub` |

## Quick start

```powershell
git clone https://github.com/sandraschi/directmedia-mcp
cd directmedia-mcp
just              # list recipes
just bootstrap    # install dependencies
just serve        # start the MCP server
```

Claude Desktop (`claude_desktop_config.json`):

```json
"mcpServers": {
  "directmedia-mcp": {
    "command": "uv",
    "args": ["--directory", "D:/Dev/repos/directmedia-mcp", "run", "directmedia-mcp"]
  }
}
```

Run directly with a library path:

```powershell
uv run directmedia-mcp --library-path "L:\Multimedia Files\Written Word\Digitale Bibliothek"
```

## Volume file layout (per volume, `Data\`)

| File | Role | Decoded? |
|------|------|----------|
| `TEXT.DKI` | Book body text | No |
| `TREE.DKI` / `TREE.DKA` | Table of contents | Partly |
| `INDEX.HTX/PLX/SHX/SWX/TTX/WLX` | Search indices | No |
| `LINKS.*` | Cross-references | No |
| `SIGEL.DAT` | Abbreviation registry | No |
| `IMAGES\`, `WAVS\`, `TABLES\` | Media | Standard formats, not wired up |

## Webapp

Dashboard in `web_sota/`: frontend on port **10826**, backend API on **10827**. Start with `web_sota\start.ps1`.

## Legal

This tool is for **interoperability and preservation** with CD-ROMs you legally own. Directmedia content remains
under its original copyright; do not redistribute extracted text from copyrighted volumes. Public-domain texts via
TextGrid are subject to TextGrid's terms (CC-BY 3.0 for annotated data, credit "TextGrid").

## License

MIT — see [LICENSE](LICENSE).
