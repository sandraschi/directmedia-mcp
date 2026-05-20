# Directmedia MCP 

<p align="center">
  <a href="https://github.com/casey/just"><img src="https://img.shields.io/badge/just-ready_to_go-7c5cfc?style=flat-square&logo=just&logoColor=white" alt="Just"></a>
  <a href="https://github.com/astral-sh/ruff"><img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json" alt="Ruff"></a>
  <a href="https://python.org"><img src="https://img.shields.io/badge/Python-3.13+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python"></a>
  <a href="https://github.com/PrefectHQ/fastmcp"><img src="https://img.shields.io/badge/FastMCP-3.2-7c5cfc?style=flat-square" alt="FastMCP"></a>
</p>


> 📖 **[Installation Guide](INSTALL.md)** — quick start, manual setup, and troubleshooting

**FastMCP 3.1.0+ server for accessing Directmedia Publishing "Digitale Bibliothek" - TEXT EXTRACTION WORKING!**

## Quick Start

```powershell
git clone https://github.com/sandraschi/directmedia-mcp
cd directmedia-mcp
just
```

This opens an interactive dashboard showing all available commands. Run `just bootstrap` to install dependencies, then `just serve` or `just dev` to start.

### Manual Setup

If you don't have `just` installed:

##  Overview

The Directmedia Publishing "Digitale Bibliothek" was a pioneering German electronic book collection from the 1990s, containing extensive German literature and world literature. This MCP server provides programmatic access to these classic digital books.

###  **BREAKTHROUGH: Text Extraction Working!**

**MISSION ACCOMPLISHED**: We successfully reversed the Directmedia TEXT.DKI format!

- **Discovery**: TEXT.DKI files contain **structured binary records**, not compressed data
- **Decompressor**: Working Python implementation extracts readable German text
- **Access**: 101 volumes of 1990s literature now programmatically accessible
- **Preservation**: Digital cultural heritage unlocked for modern use

**What was thought to be "compression" was actually a structured record format with 2-byte length headers!**

###  Collection Status
- **101 volumes** discovered (DB002-DB161, DBSK01-DBSK05, DBSO01-DBSO28)
- **~14GB** total content across all volumes
- **Proprietary binary format** from 1990s German publishing
- **Latin-1 encoding** with special characters for German texts

###  **Legal Requirement**
**You must legally purchase the Directmedia CD-ROMs to use this tool. See Legal Notice section below.**

###  Sample Volumes
| Volume ID | Title | Size | Content Type |
|-----------|-------|------|--------------|
| DB002 | Philosophie von Platon bis Nietzsche | 389MB | Philosophy |
| DB003 | Geschichte der Philosophie | 113MB | Philosophy History |
| DB004 | Goethe | 360MB | Literature + Audio |
| DB005 | Lessing | 149MB | Literature |
| DB007 | Heine | 226MB | Literature |
| DB009 | Killy Literaturlexikon | 137MB | Reference |
| DB011 | Marx/Engels | 117MB | Political Philosophy |

###  Collection Analysis

**101 volumes** discovered with **~50GB** total content:
- **DB002-DB061**: Main literature collection (philosophy, literature, history)
- **DBSK01-DBSK05**: Schnellkurs (crash courses)
- **DBSO01-DBSO28**: Sonderausgaben (special editions)

###  File Format Structure

Each volume uses a proprietary binary format:

#### Core Files (Data/):
- **TEXT.DKI**: Main text database (structured binary records)
- **TREE.DK***: Navigation tree (table of contents)
- **INDEX.***: Multiple search indices (HTX, PLX, SHX, SWX, TTX, WLX)
- **LINKS.***: Hyperlinks and cross-references
- **SIGEL.DAT**: Abbreviations/signatures registry

#### Media Files:
- **IMAGES/**: BMP illustrations and diagrams
- **WAVS/**: Audio files (readings, lectures)
- **TABLES/**: Specialized content tables

##  Quick Start

### Prerequisites
- Python 3.11+
- Access to Directmedia "Digitale Bibliothek" collection
- FastMCP 3.1.0+

##  Installation

### Prerequisites
- [uv](https://docs.astral.sh/uv/) installed (RECOMMENDED)
- Python 3.12+

###  Quick Start
Run immediately via `uvx`:
```bash
uvx directmedia-mcp
```

###  Claude Desktop Integration
Add to your `claude_desktop_config.json`:
```json
"mcpServers": {
  "directmedia-mcp": {
    "command": "uv",
    "args": ["--directory", "D:/Dev/repos/directmedia-mcp", "run", "directmedia-mcp"]
  }
}
```
### Basic Usage
```python
from directmedia_mcp import DirectmediaLibrary

# Initialize library
lib = DirectmediaLibrary(r"L:\Multimedia Files\Written Word\Digitale Bibliothek")

# List all volumes
volumes = lib.list_volumes()
print(f"Found {len(volumes)} volumes")

# Search for content
results = lib.search_text("Nietzsche", "DB002")  # Philosophy volume

# Extract text
content = lib.get_text_content("DB002", 0, 1000)
```

### MCP Server Usage
```bash
# Start MCP server
python -m directmedia_mcp.server --library-path "L:\Multimedia Files\Written Word\Digitale Bibliothek"

# Or run directly
directmedia-mcp --library-path "L:\Multimedia Files\Written Word\Digitale Bibliothek"
```

##  MCP Tools

### Library Management
- `set_library_path(path)` - Configure library location
- `list_volumes()` - List all available volumes
- `get_volume_info(volume_id)` - Get volume metadata

### Content Access
- `search_text(query, volume_id, limit)` - Search across volumes
- `get_text_content(volume_id, start_pos, length)` - Extract text
- `get_navigation_tree(volume_id)` - Get table of contents

### EPUB Conversion  **NEW**
- `convert_volume_to_epub_file(volume_id, output_dir)` - Convert single volume to EPUB
- `batch_convert_to_epub(output_dir, volume_ids)` - Convert multiple volumes to EPUB

### Analysis
- `analyze_volume_structure(volume_id)` - File format analysis

##  Volume Overview

| Volume ID | Title | Size | Content Type |
|-----------|-------|------|--------------|
| DB002 | Philosophie von Platon bis Nietzsche | 267MB | Philosophy |
| DB003 | Geschichte der Philosophie | 180MB | Philosophy |
| DB004 | Goethe | 150MB | Literature + Audio |
| DB005 | Lessing | 75MB | Literature |
| ... | ... | ... | ... |

##  Technical Details

### Binary Format Analysis

**TEXT.DKI Structure:**
- Header: 256 bytes with section offset table
- Content: Structured binary records (not compressed!)
- Each record: 2-byte length + 1-byte type + text content

**TREE.DK* Structure:**
- DKA: Navigation tree with entry counts and offsets
- DKI: Tree structure data

**INDEX Files:**
- HTX: Hypertext index for navigation
- PLX: Plaintext index for full-text search
- SHX/SWX: Specialized search indices
- TTX: Title index
- WLX: Word list index

### Known Limitations

1. **Proprietary Format**: No official documentation available
2. **Advanced Features**: Some INDEX and TREE.DK* structures still being analyzed
3. **Encoding**: Primarily Latin-1 with some UTF-8 elements
4. **Media Content**: Images and audio files not yet processed

### Recent Achievements 

- [x] **TEXT.DKI Decompression**: Successfully reversed structured binary record format
- [x] **Text Extraction**: Working decompressor extracts readable German text
- [x] **EPUB Conversion**: Convert volumes to modern e-book format
- [x] **MCP Integration**: Full programmatic access via FastMCP server
- [x] **Volume Management**: Complete 101-volume library access
- [x] **TREE.DKI Navigation**: Table of contents successfully parsed

##  **EPUB Conversion Feature**

Convert extracted Directmedia text content into modern EPUB format for e-book readers!

### **What It Does**
- **Extracts** readable text from Directmedia `.DKI` files
- **Formats** content with proper HTML structure and CSS styling
- **Creates** valid EPUB 3.0 files compatible with all e-book readers
- **Preserves** German text encoding and special characters
- **Adds** metadata including title, author, and volume information

### **EPUB Features**
- **Proper Structure**: Mimetype, container.xml, OPF package, navigation
- **German Typography**: Optimized for German text with proper quotes and spacing
- **Responsive Design**: CSS styling that works on all devices
- **Table of Contents**: Navigation structure for easy browsing
- **Metadata**: Complete Dublin Core metadata for library management

### **Usage Examples**

**Convert single volume:**
```bash
# Via MCP tool
convert_volume_to_epub_file("DB002", "./epub_output")
```

**Batch convert multiple volumes:**
```bash
# Via MCP tool
batch_convert_to_epub("./epub_library", ["DB002", "DB003", "DB004"])
```

### **Output Example**
```
epub_output/
 Goethe - Faust.epub          # Volume DB004
 Heine - Buch der Lieder.epub # Volume DB007
 ... (more volumes)
```

### **EPUB Reader Compatibility**
-  **Calibre** (recommended for library management)
-  **Apple Books** (iOS/macOS)
-  **Google Play Books**
-  **Kindle** (via conversion)
-  **Adobe Digital Editions**
-  **All major e-book readers**

### Future Enhancements

- [ ] Complete INDEX file parsing for full-text search
- [ ] TREE.DK* advanced structure decoding
- [ ] Cross-volume search optimization
- [ ] Image extraction and processing
- [ ] Audio file handling

##  Contributing

This is a research project to preserve and provide access to classic digital literature. Contributions welcome for:

- Binary format analysis
- Decompression algorithms
- Search optimization
- Documentation improvements

##  **Legal Notice & Copyright**

### **Important: Legal Use Required**

This software tool is designed to work with **legally purchased** copies of Directmedia Publishing's "Digitale Bibliothek" CD-ROM collection. **You must own legitimate copies of the CD-ROMs to use this tool legally.**

#### **Where to Purchase**
Directmedia Publishing still operates and offers their complete collection:

- **Official Website**: [https://www.directmedia-publishing.de/](https://www.directmedia-publishing.de/)
- **Product**: "Digitale Bibliothek" (Complete 101-volume collection)
- **Format**: Available as digital downloads and physical media
- **Languages**: German literature and philosophy collections

#### **Copyright Notice**
- **Copyright**:  Directmedia Publishing GmbH
- **Content**: All text, images, and multimedia content remain copyrighted
- **Usage**: Personal, educational, and research use permitted with legal copies
- **Redistribution**: Not permitted without explicit permission

#### **Disclaimer**
This tool is provided for **educational and research purposes** to access legally obtained digital content. The authors are not responsible for misuse of this software. Ensure you comply with all applicable copyright laws in your jurisdiction.

**Pirated or illegally obtained content is not supported and may violate copyright law.**


## 🛡️ Industrial Quality Stack

This project adheres to **SOTA 14.1** industrial standards for high-fidelity agentic orchestration:

- **Python (Core)**: [Ruff](https://astral.sh/ruff) for linting and formatting. Zero-tolerance for `print` statements in core handlers (`T201`).
- **Webapp (UI)**: [Biome](https://biomejs.dev/) for sub-millisecond linting. Strict `noConsoleLog` enforcement.
- **Protocol Compliance**: Hardened `stdout/stderr` isolation to ensure crash-resistant JSON-RPC communication.
- **Automation**: [Justfile](./justfile) recipes for all fleet operations (`just lint`, `just fix`, `just dev`).
- **Security**: Automated audits via `bandit` and `safety`.

##  License

MIT License - see LICENSE file for details.

##  Acknowledgments

- Directmedia Publishing for pioneering electronic literature in the 1990s
- The German digital humanities community
- FastMCP framework for MCP implementation


##  Webapp Dashboard

This MCP server includes a free, premium web interface for monitoring and control.
By default, the web dashboard runs on port **10826**.
*(Assigned ports: **10826** (Web dashboard frontend), **10827** (Web dashboard backend (API)))*

To start the webapp:
1. Navigate to the `webapp` (or `web`, `frontend`) directory.
2. Run `start.bat` (Windows) or `./start.ps1` (PowerShell).
3. Open `http://localhost:10826` in your browser.
