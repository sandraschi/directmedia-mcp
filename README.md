# Directmedia MCP 📚

[![Python](https://img.shields.io/badge/Python-3.10+-green)](https://python.org)
[![FastMCP](https://img.shields.io/badge/FastMCP-2.13+-blue)](https://github.com/jlowin/fastmcp)
[![Volumes](https://img.shields.io/badge/Volumes-101-orange)](README.md)
[![Size](https://img.shields.io/badge/Size-14GB-blue)](README.md)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)
[![GitHub](https://img.shields.io/badge/GitHub-sandraschi/directmedia--mcp-blue)](https://github.com/sandraschi/directmedia-mcp)

**FastMCP 2.13+ server for accessing Directmedia Publishing "Digitale Bibliothek"**

## 🎯 Overview

The Directmedia Publishing "Digitale Bibliothek" was a pioneering German electronic book collection from the 1990s, containing extensive German literature and world literature. This MCP server provides programmatic access to these classic digital books.

### 📊 Collection Status
- **101 volumes** discovered (DB002-DB161, DBSK01-DBSK05, DBSO01-DBSO28)
- **~14GB** total content across all volumes
- **Proprietary binary format** from 1990s German publishing
- **Latin-1 encoding** with special characters for German texts

### 🗂️ Sample Volumes
| Volume ID | Title | Size | Content Type |
|-----------|-------|------|--------------|
| DB002 | Philosophie von Platon bis Nietzsche | 389MB | Philosophy |
| DB003 | Geschichte der Philosophie | 113MB | Philosophy History |
| DB004 | Goethe | 360MB | Literature + Audio |
| DB005 | Lessing | 149MB | Literature |
| DB007 | Heine | 226MB | Literature |
| DB009 | Killy Literaturlexikon | 137MB | Reference |
| DB011 | Marx/Engels | 117MB | Political Philosophy |

### 📊 Collection Analysis

**101 volumes** discovered with **~50GB** total content:
- **DB002-DB061**: Main literature collection (philosophy, literature, history)
- **DBSK01-DBSK05**: Schnellkurs (crash courses)
- **DBSO01-DBSO28**: Sonderausgaben (special editions)

### 🗂️ File Format Structure

Each volume uses a proprietary binary format:

#### Core Files (Data/):
- **TEXT.DKI**: Main text database (compressed full text)
- **TREE.DK***: Navigation tree (table of contents)
- **INDEX.***: Multiple search indices (HTX, PLX, SHX, SWX, TTX, WLX)
- **LINKS.***: Hyperlinks and cross-references
- **SIGEL.DAT**: Abbreviations/signatures registry

#### Media Files:
- **IMAGES/**: BMP illustrations and diagrams
- **WAVS/**: Audio files (readings, lectures)
- **TABLES/**: Specialized content tables

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Access to Directmedia "Digitale Bibliothek" collection
- FastMCP 2.13+

### Installation
```bash
pip install -e .
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

## 🔧 MCP Tools

### Library Management
- `set_library_path(path)` - Configure library location
- `list_volumes()` - List all available volumes
- `get_volume_info(volume_id)` - Get volume metadata

### Content Access
- `search_text(query, volume_id, limit)` - Search across volumes
- `get_text_content(volume_id, start_pos, length)` - Extract text
- `get_navigation_tree(volume_id)` - Get table of contents

### Analysis
- `analyze_volume_structure(volume_id)` - File format analysis

## 📋 Volume Overview

| Volume ID | Title | Size | Content Type |
|-----------|-------|------|--------------|
| DB002 | Philosophie von Platon bis Nietzsche | 267MB | Philosophy |
| DB003 | Geschichte der Philosophie | 180MB | Philosophy |
| DB004 | Goethe | 150MB | Literature + Audio |
| DB005 | Lessing | 75MB | Literature |
| ... | ... | ... | ... |

## 🔍 Technical Details

### Binary Format Analysis

**TEXT.DKI Structure:**
- Header: 64 bytes with offset table
- Content: Compressed German text (Latin-1 encoding)
- Multiple sections with different compression

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
2. **Compression**: Text content uses unknown compression algorithm
3. **Encoding**: Primarily Latin-1 with some UTF-8 elements
4. **Navigation**: Tree structure not fully decoded yet

### Future Enhancements

- [ ] Full TEXT.DKI decompression algorithm
- [ ] Complete INDEX file parsing
- [ ] TREE.DK* structure decoding
- [ ] Cross-volume search optimization
- [ ] Image extraction and processing
- [ ] Audio file handling

## 🤝 Contributing

This is a research project to preserve and provide access to classic digital literature. Contributions welcome for:

- Binary format analysis
- Decompression algorithms
- Search optimization
- Documentation improvements

## 📜 License

MIT License - see LICENSE file for details.

## 🙏 Acknowledgments

- Directmedia Publishing for pioneering electronic literature in the 1990s
- The German digital humanities community
- FastMCP framework for MCP implementation
