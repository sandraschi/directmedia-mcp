# Directmedia MCP

<p align="center">
  <a href="https://github.com/casey/just"><img src="https://img.shields.io/badge/just-ready_to_go-7c5cfc?style=flat-square&logo=just&logoColor=white" alt="Just"></a>
  <a href="https://github.com/astral-sh/ruff"><img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json" alt="Ruff"></a>
  <a href="https://python.org"><img src="https://img.shields.io/badge/Python-3.13+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python"></a>
  <a href="https://github.com/PrefectHQ/fastmcp"><img src="https://img.shields.io/badge/FastMCP-3.2-7c5cfc?style=flat-square" alt="FastMCP"></a>
</p>

> **Status: experimental / mission ongoing.** The Directmedia `TEXT.DKI` body-text format is **not cracked yet**.
> This server can enumerate volumes and read some metadata, but it **cannot reliably extract book text** from the CDs.

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
| `TEXT.DKI` (book body text) | **Not decoded.** Header and offset table understood; the packed payload codec is unknown |
| `search_text`, `get_text_content` | Return heuristic byte scrapes, not faithful text — do not trust the output |
| EPUB export | Wraps whatever the heuristic produced; not usable as real books yet |
| `INDEX.*`, `LINKS.*`, images, audio | Not analysed |

An earlier version of this README claimed "TEXT.DKI decompression working" and "101 volumes accessible". **That was
wrong** — the "structured records, not compressed" theory did not survive contact with real volumes. The loose
`reverse_engineer_*.py` / `*huffman*.py` scripts in the repo root are from that failed attempt and are kept only for
reference.

## What we know about TEXT.DKI

The reversing work happens in **[reversing-mcp](https://github.com/sandraschi/reversing-mcp)** (Ghidra + ReVa against
`Digibib5.exe`). Its running notes are the source of truth:
`reversing-mcp/docs/status.md` and `reversing-mcp/docs/DIGIBIB_DECOMPILE_PLAN.md`.

Summary of findings so far:

- **Two on-disk families.** DB006-style files start with magic `0x001924CC`, then `0x00000004`, then a dword count;
  DB002/DB008-style files have a per-volume first dword and `0x00067200` at offset 4, followed by an ascending dword
  offset table.
- **Loader identified.** `FUN_00616af0` in `Digibib5.exe` reads the 12-byte header and a `uint32[count]` offset table.
  Line layout goes through `FUN_00613458` → `FUN_00616dc0` / `FUN_00614bb4`.
- **Not zlib.** The embedded zlib is only used for PNG decoding; nothing traced connects it to `TEXT.DKI`.
- **Open:** the payload codec itself, and why no traced loader in this `Digibib5.exe` build accepts the `0x67200`
  family at all (possibly a different reader build).

Next planned steps: use TextGrid plain text of the same works as **known plaintext** against `TEXT.DKI` records, and do a
dynamic pass (hook the decoded line buffer in `Digibib5.exe`) instead of more static archaeology.

## Public-domain texts without the CDs

If you only need **public-domain** works, you do not need to crack DKI at all:

- **zeno.org** — the online library derived from the same corpus.
- **[TextGrid Repository — Digitale Bibliothek](https://textgridrep.org)** — the zeno.org corpus as TEI XML
  (literature ~690 authors, philosophy ~250 authors, plus smaller collections). Annotated data and metadata are
  CC-BY 3.0, plain texts are public domain; credit "TextGrid".
  - Bulk download (texts only, ~390 MB): `https://textgridlab.org/download/digitale-bibliothek/literatur-nur-texte-2.zip`
  - Per-object export: `https://textgridlab.org/1.0/aggregator/{text|epub}/textgrid:<id>`

Copyrighted CD content (lexika such as Killy, editorial commentary, modern translations) is **not** on TextGrid —
that is what the DKI reversing is still for.

A TextGrid-backed source for this server is planned, not implemented.

## MCP tools

All tools exist; see the status table above for what their output is worth.

| Tool | Purpose |
|------|---------|
| `set_library_path(path)` | Point the server at the local Digitale Bibliothek folder |
| `list_volumes()` | Enumerate volumes (DBxxx, DBSKxx, DBSOxx) |
| `get_volume_info(volume_id)` | Volume metadata and file inventory |
| `analyze_volume_structure(volume_id)` | File-format overview of a volume |
| `get_navigation_tree(volume_id)` | TOC from `TREE.DKI` (partial) |
| `search_text(query, volume_id, limit)` | Experimental — heuristic, unreliable |
| `get_text_content(volume_id, start_pos, length)` | Experimental — heuristic, unreliable |
| `convert_volume_to_epub_file(volume_id, output_dir)` | Experimental |
| `batch_convert_to_epub(output_dir, volume_ids)` | Experimental |

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
