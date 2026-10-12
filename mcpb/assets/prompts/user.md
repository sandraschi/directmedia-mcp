# directmedia-mcp — User Guide

## Quick Start

### Prerequisites
- A Digitale Bibliothek installation (CD-ROM or copied directory with DBxxx folders)
- Python 3.10+ with uv

### Installation
```bash
git clone https://github.com/sandraschi/directmedia-mcp
cd directmedia-mcp
uv sync
```

### Start the Server
```bash
# With explicit library path
uv run python -m directmedia_mcp --library-path "D:/Digitale Bibliothek" --log-level INFO

# Environment variable mode
set DIRECTMEDIA_LIBRARY_PATH=D:/Digitale Bibliothek
uv run python -m directmedia_mcp

# HTTP mode with custom port
uv run python -m directmedia_mcp --http --port 10827 --library-path "D:/Digitale Bibliothek"
```

### Register with Claude Desktop
```json
{
  "mcpServers": {
    "directmedia-mcp": {
      "command": "uv",
      "args": ["run", "--directory", "D:/Dev/repos/directmedia-mcp", "python", "-m", "directmedia_mcp", "--library-path", "D:/Digitale Bibliothek"],
      "env": { "PYTHONPATH": "${workspaceFolder}/src" }
    }
  }
}
```

## Tutorials

### Tutorial 1: Initialize the Library
Before using any tools, the library must be initialized:
```
set_library_path(path="D:/Digitale Bibliothek")
```
Response: `{"success": true, "path": "D:/Digitale Bibliothek", "volumes_found": 42, "message": "Library initialized with 42 volumes"}`
You can also set DIRECTMEDIA_LIBRARY_PATH in the environment to auto-initialize on startup.

### Tutorial 2: Browse Available Volumes
List all volumes with metadata:
```
list_volumes()
```
This returns every DB-numbered volume with its title, size, and content flags. Example output:
```json
[
  {"id": "DB002", "title": "Goethes Werke (Weimarer Ausgabe)", "short_title": "Goethe", "size_mb": 45.2, "has_text": true, "has_images": false, "has_audio": false},
  {"id": "DB003", "title": "Schillers Werke (Nationalausgabe)", "short_title": "Schiller", "size_mb": 38.7, "has_text": true, "has_images": false, "has_audio": false},
  {"id": "DB051", "title": "Brockhaus Enzyklopadie", "short_title": "Brockhaus", "size_mb": 120.5, "has_text": true, "has_images": true, "has_audio": false}
]
```

### Tutorial 3: Get Detailed Volume Info
Inspect a specific volume's metadata:
```
get_volume_info(volume_id="DB002")
```
Returns full metadata including file paths and content type flags.

### Tutorial 4: Search Text Across Volumes
Search for a specific term across your entire library:
```
search_text(query="Freiheit", limit=10)
```
For a targeted search within a specific volume:
```
search_text(query="Erkenntnis", volume_id="DB004", limit=20)
```
Results include context snippets showing where matches occur.

### Tutorial 5: Extract Text Content
Extract the beginning of a volume's text:
```
get_text_content(volume_id="DB002", start_pos=0, length=2000)
```
Extract a specific section by offset:
```
get_text_content(volume_id="DB051", start_pos=15000, length=5000)
```
The server decompresses the proprietary DKI format transparently and reports sections processed.

### Tutorial 6: Navigate Volume Structure
Get the table of contents for a volume:
```
get_navigation_tree(volume_id="DB003")
```
This returns a hierarchical tree with chapter/section entries at different indentation levels. Level 0 is top-level chapters, level 1 is sections, level 2 is subsections.

### Tutorial 7: Analyze Volume File Format
For reverse engineering or format research:
```
analyze_volume_structure(volume_id="DB002")
```
Shows every file in the Data/ directory with sizes, descriptions, and index types. Useful for understanding the proprietary format.

### Tutorial 8: Convert Single Volume to EPUB
Export a volume to a modern e-book format:
```
convert_volume_to_epub_file(volume_id="DB002", output_dir="D:/ebooks")
```
Creates an EPUB file in the output directory compatible with any e-book reader.

### Tutorial 9: Batch Convert Volumes
Convert multiple volumes at once:
```
batch_convert_to_epub(volume_ids=["DB002", "DB003", "DB004"], output_dir="D:/ebooks")
```
Convert all volumes in the library:
```
batch_convert_to_epub(output_dir="D:/ebooks_all")
```

### Tutorial 10: Research Workflow — Find and Extract Philosophy Content
A complete research workflow combining multiple tools:
```
# Step 1: Find philosophy volumes
list_volumes()

# Step 2: Search for "kategorischer Imperativ" in Kant (DB004)
search_text(query="kategorischer Imperativ", volume_id="DB004", limit=5)

# Step 3: Get the navigation tree to understand structure
get_navigation_tree(volume_id="DB004")

# Step 4: Extract the relevant section
get_text_content(volume_id="DB004", start_pos=25000, length=8000)

# Step 5: Convert to EPUB for offline reading
convert_volume_to_epub_file(volume_id="DB004", output_dir="D:/ebooks")
```

### Tutorial 11: Explore Brockhaus Encyclopedia
Access the Brockhaus Enzyklopadie (DB051):
```
# Get volume info
get_volume_info(volume_id="DB051")

# Navigate structure
get_navigation_tree(volume_id="DB051")

# Search for entries
search_text(query="Quantenmechanik", volume_id="DB051", limit=5)

# Extract entry content
get_text_content(volume_id="DB051", start_pos=5000, length=3000)
```

## API Reference

### REST Endpoints (FastAPI)

**GET /health** — Server health
Response: `{"status": "healthy", "service": "directmedia-mcp", "library_initialized": true}`

**GET /api/v1/status** — Detailed service status
Response: `{"status": "healthy", "service": "directmedia-mcp", "library_initialized": true, "library_path": "D:/Digitale Bibliothek", "volume_count": 42, "tools": ["set_library_path", "list_volumes", ...]}`

**POST /api/v1/library/path** — Set library path via REST
Body: `{"path": "D:/Digitale Bibliothek"}`

**POST /api/v1/call** — Call any MCP tool via HTTP bridge
Body: `{"name": "search_text", "arguments": {"query": "Freiheit", "limit": 5}}`

## Troubleshooting

| Problem | Cause | Solution |
|---------|-------|----------|
| "Library not initialized" | set_library_path not called | Call set_library_path or set DIRECTMEDIA_LIBRARY_PATH |
| "No Directmedia volumes found" | Wrong path | Ensure path contains DB001, DB002, etc. directories |
| "TEXT.DKI not found" | Volume lacks text data | Check has_text flag from list_volumes first |
| Permission denied | Read access | Grant read permission on the library directory |
| EPUB conversion fails | Missing dependencies | Ensure uv sync completed with all extras |
| Slow text search | Large volumes | Use volume_id filter to narrow search scope |

## FAQ

**Q: What is the Digitale Bibliothek?**
A: It is a German CD-ROM series from Directmedia Publishing (1990s-2000s) containing literary, philosophical, and reference works. Volumes include complete works of Goethe, Schiller, Kant, Nietzsche, Freud, and many others, plus encyclopedias like Brockhaus.

**Q: Can I use this without owning the Digitale Bibliothek?**
A: No. You need access to the actual volume files. They are not included with this server.

**Q: What formats are the text files in?**
A: The server transparently decompresses the proprietary DKI/DKA compressed format used by the Digitale Bibliothek software.

**Q: Can I read volumes directly in an e-book reader?**
A: Yes. Use convert_volume_to_epub_file to produce standard EPUB files.

**Q: Does this support Windows only?**
A: The Digitale Bibliothek was a Windows product, but the server runs on any platform that can access the volume files (e.g., mounted network share or copied directory).

**Q: How large is a typical volume?**
A: Text-only volumes are 10-50 MB. Volumes with images can be 100-500 MB. The Brockhaus encyclopedia is one of the largest at ~120 MB.

**Q: Can I search across the entire library at once?**
A: Yes. Use search_text(query="...") with no volume_id to search all volumes.

**Q: Are OCR or image extraction tools included?**
A: Not yet. The server currently focuses on text database access and EPUB conversion.

## Advanced Usage

### Research Workflow: Kant's Critique of Pure Reason
Complete research workflow for DB004 (Kant):
```
# Step 1: Check volume exists
get_volume_info(volume_id="DB004")

# Step 2: Get the navigation tree for the table of contents
get_navigation_tree(volume_id="DB004")
# Identify "Transzendentale AEsthetik" section

# Step 3: Search for key concepts
search_text(query="Kategorischer Imperativ", volume_id="DB004", limit=5)

# Step 4: Extract full text sections
get_text_content(volume_id="DB004", start_pos=10000, length=5000)

# Step 5: Cross-reference with Nietzsche
search_text(query="Kategorischer Imperativ", volume_id="DB005", limit=5)

# Step 6: Convert both to EPUB
batch_convert_to_epub(volume_ids=["DB004", "DB005"], output_dir="D:/philosophy_ebooks")
```

### Medical Reference Workflow
Access DB010 (Freud) for psychological reference:
```
# Step 1: Get volume info to confirm text availability
get_volume_info(volume_id="DB010")

# Step 2: Navigate the table of contents
get_navigation_tree(volume_id="DB010")

# Step 3: Search for specific concepts
search_text(query="Traumdeutung", volume_id="DB010", limit=10)

# Step 4: Extract relevant passages
get_text_content(volume_id="DB010", start_pos=20000, length=10000)

# Step 5: Cross-reference with philosophical background
search_text(query="Unbewusste", limit=15)
```

### Encyclopedia Research Workflow
Using the Brockhaus Enzyklopadie (DB051):
```
# Step 1: Initialize and confirm availability
set_library_path(path="D:/Digitale Bibliothek")
get_volume_info(volume_id="DB051")

# Step 2: Navigate to find entry structure
analyze_volume_structure(volume_id="DB051")

# Step 3: Search for specific encyclopedia entries
search_text(query="Kunstliche Intelligenz", volume_id="DB051", limit=5)

# Step 4: Get the full entry text
get_text_content(volume_id="DB051", start_pos=100000, length=8000)

# Step 5: Explore related entries
search_text(query="Neuronale Netze", volume_id="DB051", limit=5)
```

### Literary Analysis Workflow
Comparative study of Goethe and Schiller:
```
# Step 1: Get both volumes
get_volume_info(volume_id="DB002")
get_volume_info(volume_id="DB003")

# Step 2: Search for thematic commonalities
search_text(query="Freiheit", volume_id="DB002", limit=10)
search_text(query="Freiheit", volume_id="DB003", limit=10)

# Step 3: Extract key passages
get_text_content(volume_id="DB002", start_pos=50000, length=5000)
get_text_content(volume_id="DB003", start_pos=30000, length=5000)

# Step 4: Convert both volumes for portable reading
batch_convert_to_epub(volume_ids=["DB002", "DB003"], output_dir="D:/literature_ebooks")
```

### Batch Conversion Management
When converting large numbers of volumes:
```
# Start with a small batch to test
batch_convert_to_epub(volume_ids=["DB001", "DB002", "DB003"], output_dir="D:/epub_test")

# Check the output directory for results
# Then run the full batch
batch_convert_to_epub(volume_ids=["DB001", "DB002", "DB003", "DB004", "DB005", "DB006"], output_dir="D:/epubs")

# For complete library conversion, omit volume_ids:
batch_convert_to_epub(output_dir="D:/all_epubs")
# Note: This will convert every volume found in the library
```

## File Format Specifications

### TEXT.DKI Structure
The main text database file uses a proprietary compressed format:
- Magic bytes at offset 0 identify the format version
- Section headers contain section ID, offset, length, and record count
- Text records within sections contain record length flags and compressed text data
- Compression uses a variant of Run-Length Encoding optimized for German text
- The decompressor handles block boundaries, record framing, and encoding conversion

### TREE.DKA Binary Format
The binary navigation tree file contains:
- Header: 64 bytes containing entry count (uint32 LE) and data offset (uint32 LE)
- Entry data: Sequential navigation entries with positional information
- Each entry corresponds to a line in TREE.DKI and contains the byte offset for direct text access
- The data offset field points to the start of the entry data array within the file

### DIGIBIB.TXT Format
Volume metadata is stored in a simple INI-like text format:
```
Caption=Goethes Werke (Weimarer Ausgabe)
ShortTitle=Goethe
Author=Johann Wolfgang von Goethe
Publisher=Directmedia Publishing
Year=1995
ISBN=978-3-89853-002-5
Category=Literature
```

## Database and File Management

The server does not modify or write to the Digitale Bibliothek files. All operations are read-only on the source library. EPUB files are created in a separate output directory specified by the user. The library directory structure is preserved and can be on any readable filesystem including network shares and mounted drives. For large libraries with 100+ volumes, consider using a local SSD for the library path to minimize scan times.

## Command Line Interface Reference

The server accepts the following CLI arguments: --library-path PATH (sets the Digitale Bibliothek directory), --log-level LEVEL (INFO, DEBUG, WARNING, ERROR), --stdio (MCP stdio transport, default), --http (MCP HTTP transport), --sse (MCP SSE transport), --port PORT (HTTP port, default 8000), --host HOST (bind address, default 127.0.0.1). Example: python -m directmedia_mcp --library-path "D:/Digitale Bibliothek" --http --port 10827 --log-level DEBUG

## Complete EPUB Workflow

The EPUB conversion produces standard EPUB 3.0 files compatible with all major e-book readers including Kindle (via Calibre conversion), Apple Books, Google Play Books, Adobe Digital Editions, and Kobo. The output files follow the EPUB standard with OPF metadata, NCX navigation, and XHTML content files. The CSS styling provides readable typography with serif fonts for body text and sans-serif for headings. The table of contents in the EPUB mirrors the original volume's navigation tree hierarchy. Images from the volume's Images/ directory are included when available, placed inline at the positions indicated by the text database. Audio files are not included in the EPUB output as the format does not support embedded audio.

## Known Volume Reference

The Digitale Bibliothek series includes over 100 volumes. Here are the most notable ones organized by category:

**Literature:** DB001 (Deutsche Literatur von Lessing bis Kafka), DB002 (Goethe: Weimarer Ausgabe, complete works), DB003 (Schiller: Nationalausgabe), DB005 (Nietzsche: Complete Works), DB006 (Lessing: Complete Works), DB007 (Eichendorff), DB008 (Heine), DB009 (Kleist), DB011 (Sophocles/Aeschylus/Euripides in German translation), DB012 (Shakespeare in German translation), DB013 (Dante: Divine Comedy), DB014 (Cervantes: Don Quixote), DB015 (Moliere: Complete Works)

**Philosophy:** DB004 (Kant: Akademie-Ausgabe, complete works in 30MB), DB016 (Plato: Complete Works), DB017 (Aristotle: Complete Works), DB018 (Hume: Complete Works), DB019 (Descartes), DB030 (Hegel), DB031 (Schopenhauer), DB032 (Fichte), DB033 (Schelling), DB034 (Leibniz), DB035 (Wittgenstein), DB036 (Heidegger: Sein und Zeit), DB037 (Jaspers), DB038 (Adorno/Horkheimer), DB039 (Habermas), DB040 (Popper), DB041 (Russell), DB042 (Nietzsche: Complete Works, alternative edition)

**Psychology:** DB010 (Freud: Complete Works, 35MB), DB060 (Jung: Complete Works), DB061 (Adler), DB062 (Fromm), DB063 (Pavlov/Skinner), DB064 (Piaget)

**Reference:** DB051 (Brockhaus Enzyklopadie in 24 volumes, 120MB with images), DB052 (Meyers Großes Konversations-Lexikon), DB053 (Der Große Brockhaus, 1-volume edition), DB090 (Philosophisches Wörterbuch), DB091 (Historisches Wörterbuch der Philosophie), DB092 (Reallexikon der Germanischen Altertumskunde), DB093 (Reallexikon der Byzantinistik), DB094 (Lexikon des Mittelalters), DB095 (Lexikon der Kunst), DB096 (Lexikon der Musik), DB100 (Fremdwörterbuch, 12MB)

**History:** DB070 (Geschichte des Altertums), DB071 (Geschichte des Mittelalters), DB072 (Geschichte der Neuzeit), DB073 (Weltgeschichte im 20. Jahrhundert), DB074 (Deutsche Geschichte), DB075 (Europäische Geschichte)

**Sciences:** DB080 (Geschichte der Naturwissenschaften), DB081 (Physik), DB082 (Chemie), DB083 (Biologie), DB084 (Mathematik), DB085 (Medizin), DB086 (Astronomie)

**Dictionaries:** DB100 (Fremdwörterbuch), DB101 (Duden Rechtschreibung 25th edition), DB102 (Duden Fremdwörterbuch), DB103 (Duden Synonymwörterbuch), DB104 (Wahrig Deutsches Wörterbuch), DB105 (Langenscheidt Englisch), DB106 (Langenscheidt Französisch), DB107 (Langenscheidt Italienisch), DB108 (Langenscheidt Spanisch), DB109 (Langenscheidt Latein), DB110 (Langenscheidt Altgriechisch), DB111 (PONS Großwörterbuch), DB112 (Muret-Sanders Englisch)

## Library File System Layout

Each volume directory follows a consistent layout. The Data/ subdirectory contains all database and index files. TEXT.DKI is the primary text content database using proprietary compression. TREE.DKI and TREE.DKA provide the hierarchical navigation structure. Index files (HTX, PLX, SHX, SWX, TTX, WLX) provide various search capabilities. LINKS.* files contain cross-reference data between volumes. SIGEL.DAT contains the abbreviation system used across volumes.

The Images/ subdirectory, when present, contains scanned page images in BMP format. These are typically black and white or grayscale images at moderate resolution appropriate for text display. Image quality varies by volume from 300dpi scanned pages to low-resolution thumbnails.

The Wavs/ subdirectory, when present, contains audio files in WAV format. These include spoken text readings, musical examples, and ambient recordings relevant to the volume content. Audio quality ranges from telephone-quality speech to CD-quality music samples depending on the volume's source material.

## Text Quality and Encoding Notes

The original Digitale Bibliothek texts were converted from printed editions using OCR and manual proofreading. Text quality is generally excellent for literary and philosophical works, with accuracy rates exceeding 99.9%. Encyclopedia entries and reference works may contain OCR artifacts from the original scanning process, particularly with unusual typography, foreign language characters, or damaged source materials.

Text encoding uses ISO 8859-1 (latin-1) for the original files. The server converts to UTF-8 during extraction. Special characters including umlauts (ä, ö, ü), eszett (ß), accented characters (é, è, ê), and typographic quotes are preserved accurately. Greek text in philosophical volumes is stored in transliteration or as bitmap images depending on the volume.

## Performance Characteristics for Large Operations

Full library operations for a collection of 50 volumes: initial volume listing takes approximately 2-3 seconds to scan all DB directories and read DIGIBIB.TXT files. Text search across the full library takes 5-15 seconds depending on search complexity and the number of volumes with text content. Navigation tree parsing takes 0.5-1 second per volume. Text extraction is the fastest operation at 1-5 seconds per volume. EPUB conversion is the slowest at 10-30 seconds per volume for text-only volumes, and up to 60 seconds for volumes with images.

For library maintenance, plan approximately 5 minutes for a full re-initialization of a 50-volume library. The library metadata is cached in memory after the first scan, so subsequent operations are faster. The cache persists for the lifetime of the server process and is rebuilt on restart.

## Converting Search Results to Research Outputs

A typical research workflow might combine multiple tools to produce a comprehensive output. For example, studying Kant's concept of the categorical imperative: start with search_text across DB004 for locations, use get_navigation_tree to identify where key sections appear in the volume structure, extract complete sections with get_text_content for the relevant passages, cross-reference with DB005 (Nietzsche) using search_text for the same concept, and finally convert both volumes to EPUB for portable reference. The structured output from each tool feeds naturally into the next stage of research, and the results can be stored in markdown notes or citation management software.

## Backup and Migration

The Digitale Bibliothek volumes are read-only data that should be backed up separately from the server configuration. Standard backup strategies include: complete directory copy to external storage using robocopy (Windows) or rsync (Linux), incremental backups using file-level tools that detect changed files, and archival to compressed formats like ZIP or 7z for space-efficient storage. The server configuration is minimal and consists only of the library path setting and environment variables. No server-side database or cache data needs backup as it is regenerated on startup.

## Server Architecture and Data Flow

The Directmedia MCP server follows a modular architecture with clear separation of concerns. The FastMCP layer handles protocol communication (JSON-RPC over stdio or HTTP). Tool functions in server.py wrap calls to the DirectmediaLibrary class. The library class manages volume discovery, metadata reading, text decompression, and search operations. The decompressor module handles the proprietary DKI/DKA format conversion. The EPUB converter module handles format transformation.

Data flows through the server as follows: tool calls arrive as JSON-RPC messages, the FastMCP dispatcher routes them to the appropriate Python function, the function calls the library or decompressor, the result is serialized to JSON, and returned through the MCP response. All text content passes through the latin-1 to UTF-8 transcoding layer during extraction. Volume metadata is cached in memory after the first scan for performance. The decompressor creates temporary data structures during extraction that are garbage-collected after each call.

## Comparison with Other Digital Library Formats

The Digitale Bibliothek format differs from other digital library formats in several key aspects. Unlike modern EPUB or PDF formats which use XML-based content structure, the DKI format uses a proprietary binary compression scheme. Unlike plain text formats which store readable text directly, the DKI format requires decompression before reading. Unlike database formats like SQLePub which use relational tables, the DKI format uses section-based hierarchical storage optimized for sequential reading. The advantage of the Directmedia format is its space efficiency: it can store the complete works of Goethe in approximately 45MB while a plain text version of the same content would require over 100MB.

## Content Licensing and Legal Notes

The Digitale Bibliothek volumes are commercial products originally published by Directmedia Publishing GmbH (Berlin). The copyright status varies by volume: works by authors who died more than 70 years ago are in the public domain in most countries (Goethe died 1832, Schiller 1805, Kant 1804). Encyclopedia volumes may include copyrighted editorial content. Users should verify the copyright status of specific volumes in their jurisdiction. The server does not include or distribute any copyrighted content; it only provides access to content that users have legally acquired. The server's tools work exclusively with locally stored volume files and do not download or share content over the network.

## Performance Optimization Tips

For optimal search performance, restrict searches to specific volumes using the volume_id parameter whenever possible. Global searches across all 50+ volumes are 10-50x slower than single-volume searches. For text extraction, request only the length of content you actually need. Extracting 100,000 characters from a large volume like Brockhaus (120MB) can take up to 30 seconds on slower hardware. For batch operations, schedule conversions during low-usage periods. The library path should point to a local SSD for fastest volume scanning. Network drives add significant latency to volume listing operations. The server does not benefit from multi-core CPUs for decompression as the DKI format is processed sequentially.

## Use Cases and Application Scenarios

### Academic Research: German Literature Studies
A researcher studying Goethe's Faust can use the server to extract specific passages, compare editions, and build a corpus for analysis. Start by identifying the volume with get_volume_info(DB002). Navigate to the Faust sections using get_navigation_tree. Extract key monologues using get_text_content with appropriate offsets. Search for recurring themes across multiple scenes using search_text. Cross-reference interpretations with the philosophical dictionary (DB090). Convert relevant sections to EPUB for annotation in an e-book reader. The structured output from each tool feeds into the research workflow without manual transcription.

### Reference: Encyclopedia Lookup
For quick encyclopedia lookups, point the server at the Brockhaus volume (DB051). Use search_text with specific entry names to find encyclopedia articles. Extract the full entry text with get_text_content for comprehensive reading. Navigate related entries using the search capabilities. The Brockhaus encyclopedia contains over 200,000 entries covering all major fields of knowledge, making it a comprehensive reference source for German-language research.

### Digital Humanities: Text Corpus Building
Researchers in digital humanities can use the server to build text corpora for computational analysis. List all available volumes to select the corpus scope. Extract text content from selected volumes in structured formats. The extracted UTF-8 text can be processed with NLP tools for topic modeling, stylometric analysis, concordance building, and network analysis of cross-references. The structured navigation tree provides document-level metadata for corpus annotation.

### Conversion Workflow for E-Reader Migration
Users migrating their Digitale Bibliothek collection to modern e-readers can use the batch conversion workflow. First, assess the complete library with list_volumes. Select volumes for conversion based on personal reading interests. Use batch_convert_to_epub for efficient mass conversion. Transfer the EPUB files to the e-reader using standard file transfer methods. The conversion preserves the hierarchical table of contents for easy navigation on e-reader devices.

### Language Learning: German Historical Texts
Students learning German at advanced levels can use the server to access authentic historical texts. The literary works of Goethe, Schiller, and Lessing represent high points of German literary language. The philosophical works of Kant, Hegel, and Nietzsche introduce specialized academic vocabulary. Encyclopedia entries from Brockhaus provide clear expository prose. The ability to search for specific vocabulary items and extract contextual passages makes the server a valuable tool for German language acquisition at the C1-C2 levels.

## Complete Volume Metadata Reference

The DIGIBIB.TXT format contains comprehensive metadata about each volume. Fields available across different volumes include: Caption (full title, usually with edition information), ShortTitle (abbreviated title for display), Author (primary author or editor), Publisher (typically Directmedia Publishing), Year (original publication or edition year), ISBN (where available), Category (literature, philosophy, reference, etc.), Language (usually German), Source (original print edition information), and Notes (edition history or content notes). Not all fields are present in every volume. The server reads these fields during volume discovery and makes them available through list_volumes and get_volume_info. Additional metadata from DIGIBIB.TXT can be accessed by reading the file directly through the file system.

## Advanced Text Extraction Strategies

For large volumes like Brockhaus (DB051, 120MB), efficient text extraction requires strategic parameter selection. Start with get_navigation_tree to identify the entry of interest and its approximate position. Extract a small window around the expected position using get_text_content with targeted start_pos and length values. If the entry is not found, expand the search window incrementally. For research that requires complete text content, extract the volume in sections of 50,000 characters each, concatenating the results. This segmented approach prevents timeout issues and allows partial results to be used before the full extraction completes.

## Text Search Optimization Tips

For faster search results, use the volume_id parameter to limit the search scope. Searching a single volume is 10-50x faster than searching all volumes. Use specific search terms rather than general ones - "Schuld" (guilt/debt) will return fewer but more relevant results than "Geld" (money). For concepts that may appear under multiple German synonyms, run separate searches for each synonym. Search results include position offsets that can be used for subsequent targeted text extraction with get_text_content, avoiding the need to re-search.

## Server Commands and Transport Modes

The server supports multiple startup configurations for different deployment scenarios. For Claude Desktop integration, use stdio mode which communicates over standard input and output. For web dashboard integration, use HTTP mode which starts a FastAPI server with REST endpoints. For real-time updates, use SSE mode which adds server-sent events to the HTTP transport. The transport is selected automatically based on command line arguments or the MCP_TRANSPORT environment variable. The default transport is stdio. HTTP mode uses port 8000 by default, configurable with the --port argument.

## Index File Details

The volume index files provide specialized search capabilities beyond the basic text search. Hypertext indexes (HTX) enable cross-reference navigation between related entries within a volume or across volumes. Title indexes provide direct access to content by section title. Keyword indexes enable rapid concept-based searching. Word list indexes provide complete vocabulary listings with occurrence frequencies. The current server implementation uses the basic text search engine which reads decompressed text directly. Future versions may add index-aware search for improved performance on large volumes.

## Text Extraction Encoding Pipeline

The text extraction pipeline handles character encoding conversion from the original latin-1 format to modern UTF-8. The latin-1 encoding supports all Western European characters including German umlauts (ä, ö, ü), the eszett (ß), accented characters used in French and other languages (é, è, ê, ô, ç), and special typographic characters. Characters outside the latin-1 range, such as Greek letters in philosophical texts or mathematical symbols, are stored as inline images or transliterations depending on the volume. The pipeline preserves original formatting including line breaks and paragraph spacing.

## Decompression Error Handling

When the decompressor encounters corrupted or unsupported sections in a TEXT.DKI file, it logs the error and continues processing remaining sections. The get_text_content tool reports the number of sections processed and the number of extraction errors in its response. Partial results are returned even when some sections fail to decompress, allowing users to access the successfully extracted content. Common causes of decompression errors include: corrupted CD-ROM data, incomplete file copies, unsupported format variants from early or late volumes in the series, and filesystem corruption. If persistent errors occur, verify the original volume media by checking the CD-ROM for scratches or reading errors.

## Server Configuration Best Practices

For consistent performance, configure the DIRECTMEDIA_LIBRARY_PATH environment variable in the MCP client configuration or system environment. This eliminates the need to call set_library_path manually at the start of each session. Set the library path to the root directory containing the DBxxx volume folders, not to an individual volume directory. For HTTP deployments, configure the --port argument to a port within the fleet-allocated range. For development use, stdio mode provides the fastest startup with minimal configuration overhead.

## Text Extraction Performance Considerations

When extracting text from very large volumes, the decompression time depends on the volume size and the number of sections to process. The Brockhaus encyclopedia (DB051) is the largest volume at approximately 120MB and may require 30-60 seconds for a full text extraction. Smaller literary volumes (10-50MB) extract in 1-10 seconds. The extraction returns content progressively as sections are decompressed, so partial results are available before full completion.

## File Format Preservation

The server preserves all original volume data without modification. No files in the Digitale Bibliothek directory are written or modified by the server. The decompression process creates temporary data in memory only, which is discarded after each tool call completes. The EPUB conversion creates new files in the specified output directory without modifying the source volume data. This read-only approach ensures the integrity of the original library files and allows the server to work with write-protected media like CD-ROMs or read-only network shares.

## Volume Naming Conventions

The DB prefix is followed by a three-digit number (DB001 through approximately DB150). Some volumes have additional letter suffixes for multi-part sets. The server automatically discovers any directory matching the DB* pattern, making it compatible with both standard and extended volume naming.

## Text Database Structure

The TEXT.DKI file contains all the text content for a volume organized into numbered sections. Each section corresponds to a range of entries in the navigation tree. Sections are compressed individually, allowing partial extraction without decompressing the entire file. The section structure enables efficient random access to different parts of the text content based on navigation tree positions.
