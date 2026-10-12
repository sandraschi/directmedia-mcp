# directmedia-mcp — MCP Server Capabilities

## Server Overview

Directmedia MCP provides programmatic access to the Directmedia Publishing Digitale Bibliothek, a collection of German-language literary, philosophical, and reference works from the 1990s CD-ROM era. This server allows LLM agents and applications to browse, search, extract text, analyze structure, and convert volumes from this unique digital library format. The Digitale Bibliothek was a landmark German CD-ROM series containing the complete works of major authors, encyclopedias, dictionaries, and reference works.

The server operates as a dual-transport FastMCP service with both stdio and HTTP/SSE modes. It provides tools for library discovery (listing volumes, getting metadata), text extraction and search (full-text search across volumes, content extraction with section awareness), structural analysis (navigation trees, file format analysis), and format conversion (EPUB export for e-book readers). Each volume comes from a proprietary DKI/DKA compressed format that the server transparently decompresses.

Configuration is minimal: point the server at the Digitale Bibliothek directory path, and it auto-discovers all DB-numbered volumes. The server includes REST API endpoints for web dashboard integration and MCP bridge proxy support for multi-server federation. All tools return structured JSON with clear success/error states.

## Tools

### set_library_path
Initializes the library by pointing to the Digitale Bibliothek directory.
- **Parameters:** path (str, required) — Full filesystem path to the Digitale Bibliothek root containing DBxxx subdirectories.
- **Returns:** {success: bool, path: str, volumes_found: int, message: str}
- **Validation:** Checks that the path exists and contains DB-prefixed volume folders.

### list_volumes
Lists all available Digitale Bibliothek volumes with metadata.
- **Parameters:** None
- **Returns:** Array of {id, title, short_title, path, size_mb, has_text, has_images, has_audio}
- **Details:** Each volume is scanned for Text.DKI (text database), image files (BMP/JPG/PNG), and audio files (WAV/MP3). Sizes are in MB. Volumes are sorted by ID.

### get_volume_info
Gets detailed information about a specific volume.
- **Parameters:** volume_id (str, required) — Volume ID like "DB002" or "DB003".
- **Returns:** Single volume info object or {error: "Volume not found"}.

### search_text
Full-text search across one or all volumes.
- **Parameters:**
  - query (str, required) — Text to search for (case-insensitive).
  - volume_id (str, optional) — Restrict search to specific volume.
  - limit (int, optional, default 20) — Max results to return.
- **Returns:** Array of {volume_id, title, content_preview, position} with context snippets around matches.
- **Behavior:** Searches text content up to 50KB per volume, returns positional matches with surrounding context.

### get_text_content
Extracts text content from a volume's TEXT.DKI database.
- **Parameters:**
  - volume_id (str, required) — Volume to extract from.
  - start_pos (int, optional, default 0) — Character offset to start.
  - length (int, optional, default 1000) — Max characters to return.
- **Returns:** {volume_id, start_position, length, content, sections_processed, total_records_found, extraction_errors}
- **Decompression:** Automatically decompresses the proprietary DKI format, extracting section records with text content.

### get_navigation_tree
Gets the table of contents / navigation structure for a volume.
- **Parameters:** volume_id (str, required)
- **Returns:** {volume_id, tree_files, structure, table_of_contents: [{text, level, offset}]}
- **Format:** Parses TREE.DKI (hierarchical navigation entries with indentation-based levels) and TREE.DKA (binary structural headers).

### analyze_volume_structure
Analyzes a volume's file structure and data format.
- **Parameters:** volume_id (str, required)
- **Returns:** {volume_id, data_files: {filename: {size, description}}, image_files, audio_files, other_files, total_size_mb}
- **Detail:** Categorizes all files in the Data/ directory by type: DKI/DKA data files, index files (HTX, PLX, SHX, SWX, TTX, WLX), links files, and SIGEL.DAT. Also reports image subdirectory counts and audio file counts.

### convert_volume_to_epub_file
Converts a volume to EPUB format for e-book readers.
- **Parameters:**
  - volume_id (str, required) — Volume identifier (e.g., "DB002").
  - output_dir (str, required) — Directory for the output EPUB file.
- **Returns:** {success: bool, volume_id, epub_files_created, output_dir, message}

### batch_convert_to_epub
Converts multiple volumes to EPUB simultaneously.
- **Parameters:**
  - output_dir (str, required) — Output directory.
  - volume_ids (list[str], optional) — Specific volumes to convert. Converts all if omitted.
- **Returns:** {success: bool, volumes_processed, epub_files_created, volumes_converted, output_dir, errors}

## Configuration

**Environment Variables:**
- DIRECTMEDIA_LIBRARY_PATH — Auto-initialize library on startup (optional). Set to the Digitale Bibliothek root path.
- LOG_LEVEL — Logging verbosity (default: INFO).
- MCP_BRIDGE_URLS — Comma-separated URLs for MCP bridge proxy federation.
- PYTHONPATH — Must include src/ directory.

**CLI Arguments:**
- --library-path — Path to Digitale Bibliothek directory.
- --log-level — Logging level (default: INFO).
- --stdio / --http / --sse — Transport mode selection.
- --port — HTTP port (default: 8000).
- --host — Bind address (default: 127.0.0.1).

## Data Sources

- **Local filesystem** — The Digitale Bibliothek directory containing DBxxx volume subdirectories.
- **Proprietary DKI/DKA format** — Compressed text database files decompressed by directmedia_decompressor.py.
- **TREE.DKI / TREE.DKA** — Navigation tree and hierarchical table of contents.
- **DIGIBIB.TXT** — Volume metadata (title, short title, author info).
- **Index files** — HTX, PLX, SHX, SWX, TTX, WLX index files for structured access.

## Prompts

No custom prompts are registered. The server exposes only tools.

## Resources

The server does not expose dynamic MCP resources. All data access is through tool calls.

## Integration Points

- **FastMCP** — stdio (Claude Desktop), HTTP/SSE transports.
- **MCP Bridge Proxy** — Connect to other fleet MCP servers via MCP_BRIDGE_URLS.
- **REST API** — FastAPI backend with /health, /api/v1/status, /api/v1/library/path, /api/v1/call endpoints.
- **Web SOTA** — React frontend can call tools via the /api/v1/call bridge.

## File Format Reference

The Digitale Bibliothek uses a proprietary compressed text format:
- **TEXT.DKI** — Main text database. Sections are compressed using run-length encoding (RLE) with block headers.
- **TREE.DKI** — Navigation tree with indentation-based hierarchy showing chapter/section structure.
- **TREE.DKA** — Binary header with entry count and data offset for the navigation tree.
- **DIGIBIB.TXT** — Volume-level metadata in INI-like format (Caption=, ShortTitle=).
- **INDEX.* files** — Various index types: Hypertext (HTX), Plaintext (PLX), Short (SHX), Search Word (SWX), Title (TTX), Word List (WLX).
- **SIGEL.DAT** — Abbreviation/classification database.
- **LINKS.* files** — Cross-reference link databases.

## Volume Naming Convention

Volumes are numbered DB001, DB002, DB003, etc. Each volume directory contains:
- Data/ — Core database files (TEXT.DKI, TREE.DKI, index files)
- Images/ — Optional image files (BMP format, scanned pages)
- Wavs/ — Optional audio files (WAV format, spoken text or music)

Well-known volumes include DB002 (Goethe), DB003 (Schiller), DB004 (Kant), DB051 (Brockhaus Encyclopedia), DB090 (Philosophisches Worterbuch).

## Advanced Library Operations

### Volume Detection and Caching
When the library path is set, the server scans for all directories matching the DB-prefixed pattern (DB001, DB002, etc.). Each volume is inspected for the presence of TEXT.DKI (text content), image files (BMP/JPG/PNG), and audio files (WAV/MP3). Volume metadata is read from DIGIBIB.TXT files using latin-1 encoding. The volume list is cached after the first scan for performance. To refresh the cache, call set_library_path again or restart the server. Large libraries with 50+ volumes complete the initial scan in under 5 seconds on modern hardware.

### Proprietary DKI Decompression
The Directmedia decompressor handles the proprietary compression format used in TEXT.DKI files. The format uses Run-Length Encoding (RLE) with block-level headers. Each TEXT.DKI file contains multiple sections, each section containing multiple text records with metadata. The decompressor extracts section structure, record boundaries, and text content with latin-1 encoding. The extract_text_content method accepts a max_sections parameter to limit processing for large volumes. Decompression speed is approximately 10MB per second on modern hardware, with the Brockhaus encyclopedia (DB051) being the largest volume at approximately 120MB requiring 12-15 seconds for full extraction.

### Navigation Tree Format
The TREE.DKI file structure uses a line-based format where each line represents a navigation entry. The indentation level (measured in 2-space increments) determines the hierarchy level: level 0 for top-level chapters, level 1 for sections, level 2 for subsections, and so on. The TREE.DKA companion file provides binary structural information including entry count and data offsets. The navigation parser handles CRLF and LF line endings, control character filtering, and latin-1 text encoding. Empty lines are skipped while maintaining the hierarchical structure integrity.

### Index File System
Each volume may contain up to six index files serving different search purposes:
- INDEX.HTX (Hypertext Index): Maps hypertext links between related content sections within a volume, enabling cross-referencing between related topics
- INDEX.PLX (Plaintext Index): Provides sequential positional mapping for plain text content, enabling fast offset-based content retrieval
- INDEX.SHX (Short Index): Contains abbreviated entry references for quick lookup of commonly accessed content
- INDEX.SWX (Search Word Index): A keyword-to-position mapping database enabling efficient full-text search without scanning the main text database
- INDEX.TTX (Title Index): Maps section titles to their positions within the text, enabling structured navigation by title
- INDEX.WLX (Word List Index): A comprehensive word-level index supporting complex search queries and word frequency analysis

### EPUB Conversion Pipeline
The EPUB conversion process follows these steps:
1. Initialize the library and verify the target volume exists
2. Read DIGIBIB.TXT for volume metadata (title, author, publication information)
3. Extract the TREE.DKI navigation tree for the EPUB table of contents
4. Decompress TEXT.DKI using the proprietary decompressor to extract all text content sections
5. Reconstruct the text in hierarchical order based on the navigation tree
6. Generate standard EPUB 3.0 format output with:
   - OPF metadata file containing title, author, language, and unique identifier
   - NCX navigation file mirroring the volume's table of contents hierarchy
   - XHTML content files with proper heading structure (h1-h6) mapped from navigation levels
   - CSS styling for readable typography with configurable fonts and spacing
   - Proper manifest and spine elements for EPUB compliance
7. Package the EPUB as a ZIP container with .epub extension
8. Validate the output against basic EPUB structure requirements

### Supported Volume Types
The Digitale Bibliothek series includes several categories of volumes:

**Literary Works** — Complete editions of major German-language authors:
- DB002: Goethe — Weimarer Ausgabe (complete works, 45MB)
- DB003: Schiller — Nationalausgabe (complete works, 38MB)
- DB004: Kant — Akademie-Ausgabe (philosophical works, 30MB)
- DB005: Nietzsche — Kritische Gesamtausgabe (25MB)
- DB006: Lessing — complete works (28MB)
- DB010: Freud — Gesammelte Werke (35MB)
- DB020: Marx/Engels — MEW (50MB)

**Reference Works** — Encyclopedia and dictionaries:
- DB051: Brockhaus Enzyklopadie (120MB, includes images)
- DB090: Philosophisches Worterbuch (15MB)
- DB100: Fremdworterbuch (12MB)
- Various dictionaries for Latin, Greek, French, English, and other languages

**Special Collections** — Thematic volumes:
- Historical documents and legal texts
- Art history with image plates
- Musicology with audio samples
- Scientific and medical reference works

## Performance Considerations

Text extraction and search performance depends on volume size and the operation being performed:
- Volume listing: Under 1 second for libraries up to 100 volumes
- Single volume info: Instant from cache, under 2 seconds for first scan
- Text search across all volumes: 5-30 seconds depending on library size and query complexity
- Text extraction: 1-10 seconds depending on volume size and extraction length
- Navigation tree parsing: Under 1 second per volume
- Volume structure analysis: Under 2 seconds per volume
- EPUB conversion: 5-30 seconds per volume depending on text volume complexity
- Batch conversion: N * single volume time, runs sequentially

## Error Handling

All tools return structured responses with consistent error patterns:
- Library not initialized: `{"error": "Library not initialized. Use set_library_path first."}`
- Volume not found: `{"error": "Volume DB999 not found"}`
- Text extraction failure: `{"error": "TEXT.DKI not found for volume. Tried: [paths]"}`
- Invalid path: `{"error": "Path does not exist: /bad/path"}`
- No volumes: `{"error": "No Directmedia volumes (DBxxx folders) found in /path"}`

## Complete API Tool Reference

### set_library_path Full Specification
This tool initializes the Directmedia Library's internal data structures and scans for all DB-prefixed volumes at the given path. The path parameter must point to the root directory containing DBxxx subdirectories. On success, it returns the number of volumes found, which should match the number of DBxxx folders present. On failure, it returns specific error messages for nonexistent paths, paths without DB folders, or paths with permission issues. The library path is stored in memory for the server's lifetime and must be set again after a server restart. If the DIRECTMEDIA_LIBRARY_PATH environment variable is set, the library auto-initializes on server startup without requiring an explicit tool call. The tool also supports network paths (UNC paths, mapped drives) and Linux filesystem paths when running on Linux or WSL.

### list_volumes Full Specification
Returns a complete inventory of all Digitale Bibliothek volumes sorted by volume ID. Each volume entry contains: id (string like DB002), title (full caption from DIGIBIB.TXT), short_title (abbreviated title), path (absolute filesystem path), size_mb (directory size in megabytes rounded to one decimal), has_text (boolean indicating presence of TEXT.DKI), has_images (boolean indicating presence of image files in BMP/JPG/PNG format), has_audio (boolean indicating presence of audio files in WAV/MP3 format). The volume list is cached after the first call. To refresh the list after adding new volumes to the library, call set_library_path again with the same path.

### get_volume_info Full Specification
Returns the same VolumeInfo object as list_volumes but for a single specified volume. If the volume_id does not match any known volume, returns an error message. Use list_volumes first to discover valid volume IDs. The volume_id parameter is case-insensitive for the DB prefix (db002, DB002, Db002 all work) but must match exactly after the prefix.

### search_text Full Specification
Performs case-insensitive substring matching across the decompressed text content of one or all volumes. The query parameter is the search term, using simple text matching (no regular expressions or wildcards). When volume_id is None, all volumes with has_text=True are searched. When volume_id is specified, only that single volume is searched. The limit parameter caps the total number of results returned, with results distributed across volumes when searching globally. Each result includes: volume_id (source volume), title (contextual title derived from the match position), content_preview (approximately 100 characters of surrounding context with ... markers), and position (character offset within the text database where the match begins). For volumes where full decompression is too slow, the search reads only the first 50KB of text content. This means search may miss matches in very deep sections of large volumes.

### get_text_content Full Specification
Decompresses and extracts text from a volume's TEXT.DKI database using the proprietary Directmedia decompressor. The start_pos parameter specifies the character offset to begin extraction from. The length parameter specifies the maximum number of characters to return. The tool returns: volume_id, start_position (the requested offset), length (actual length of extracted content), content (the decompressed text), sections_processed (number of compressed sections that were decompressed to produce this output), total_records_found (number of individual text records combined), extraction_errors (count of sections that failed to decompress). The content is encoded as UTF-8 even though the original files use latin-1 encoding. Very large extractions (over 100,000 characters) may take several seconds on slower hardware.

### get_navigation_tree Full Specification
Parses the TREE.DKI file to extract a hierarchical table of contents, and analyzes the TREE.DKA binary header for structural metadata. Returns: volume_id, tree_files (object with TREE.DKI and TREE.DKA metadata including file sizes), structure (string describing whether the tree uses hierarchical text format), and table_of_contents (array of entries each with text, level, and offset). The level field represents hierarchy depth: 0 for major divisions (parts, books), 1 for chapters, 2 for sections, 3 for subsections, and higher for sub-subsections. The offset field is a sequential index, not a byte offset. If TREE.DKI cannot be parsed (e.g., corrupted or unsupported format), the function returns the files that were found and an error message explaining the parsing failure.

### analyze_volume_structure Full Specification
Provides a comprehensive file-by-file analysis of a volume's Data directory. Returns: volume_id, data_files (object mapping each filename to its size and a description or type), image_files (object with subdirectory names and file counts), audio_files (object with subdirectory names and file counts), other_files (uncategorized files), and total_size_mb (sum of all file sizes in megabytes). Known file types receive descriptive labels in German: TEXT.DKI (Haupttextdatenbank), TREE.DKA (Navigationsbaum), TREE.DKI (Strukturdaten). Index files are labeled by their function: Hypertext Index, Plaintext Index, Short Index, Search Word Index, Title Index, Word List Index. Unknown files are simply labeled with their size. This tool is useful for understanding the proprietary format, troubleshooting incomplete volumes, and assessing which content types a volume contains.

### convert_volume_to_epub_file Full Specification
Converts a single volume from the proprietary DKI format to standard EPUB 3.0. The conversion process decompresses the TEXT.DKI database, extracts the navigation tree from TREE.DKI, and reconstructs the content as a properly structured EPUB with table of contents, metadata, and styled XHTML content. The output_dir parameter specifies where the EPUB file will be created. The tool creates the output directory if it does not exist. Returns: success, volume_id, epub_files_created (number of EPUB files generated, typically 1), output_dir, message. If the conversion fails, returns success false with error details. Large volumes (Brockhaus at 120MB) may take 30-60 seconds to convert. The EPUB includes the volume title as the document title and preserves the hierarchical chapter structure from the navigation tree.

### batch_convert_to_epub Full Specification
Converts multiple volumes to EPUB format in a single operation. The volume_ids parameter accepts an optional list of specific volume IDs to convert. When volume_ids is omitted, the tool converts every volume in the library that has text content. The output_dir parameter specifies the output directory for all generated EPUB files. Returns: success, volumes_processed (total volumes attempted), epub_files_created (total EPUB files successfully generated), volumes_converted (list of successfully converted volume IDs), output_dir, errors (list of any errors encountered during conversion). Conversion is sequential, so a batch of 50 volumes may take 10-30 minutes depending on volume sizes and hardware.

## Database Engine and Text Processing

The Directmedia text database engine works with a custom binary format designed for the CD-ROM era. Each TEXT.DKI file contains compressed sections of text records. The decompressor processes these sections sequentially, handling the RLE-based compression that was optimized for German language text. Section headers contain metadata about the section content, including section IDs that correspond to entries in the navigation tree. Text records within sections are variable-length and include length flags that help the decompressor determine the compression scheme used.

The compression algorithm works at the byte level, identifying repeated byte sequences and replacing them with shorter reference tokens. The algorithm is particularly effective on German text because of the frequent compound words and common suffixes. Typical compression ratios for literary texts range from 40-60% of the original size. The decompressor translates the latin-1 encoded bytes into Unicode using Python's latin-1 codec.

## Server Transport and Integration

The server supports three MCP transport modes selectable via CLI arguments or environment variables. In stdio mode, the MCP protocol operates over standard input/output, making it compatible with Claude Desktop and Cursor. In HTTP mode, the MCP protocol is wrapped in HTTP requests, allowing remote connections and integration with web-based MCP clients. In SSE mode, the server establishes a persistent HTTP connection for server-sent events, enabling real-time updates and push notifications.

The server also exposes a REST API on the FastAPI application for dashboard integration. The /health endpoint provides basic health checks, /api/v1/status returns full server status with volume counts and available tools, /api/v1/library/path sets the library path via HTTP POST, and /api/v1/call provides a web bridge for calling any MCP tool with JSON parameters. The /mcp mount point exposes the FastMCP HTTP application for MCP-compatible clients.

## Environment Variable Reference

DIRECTMEDIA_LIBRARY_PATH sets the default library path for automatic initialization on server startup. This is the recommended configuration method for production deployments as it eliminates the need to call set_library_path manually. The path should point to the root directory containing DBxxx subdirectories.

MCP_BRIDGE_URLS accepts a comma-separated list of MCP server HTTP URLs. Each URL is connected as a proxy provider, making the remote server's tools available through the local FastMCP instance. This enables federated multi-server queries where one server can access another's tools.

LOG_LEVEL controls logging verbosity with standard Python logging levels. DEBUG provides detailed diagnostic information including all API calls, INFO reports normal operations, WARNING highlights potential issues, ERROR reports operation failures, and CRITICAL reports server-level failures.

PYTHONPATH must include the src/ directory for the server to find its module imports. This is typically set in the MCP client configuration or in the run script.

## Search Algorithm Details

The search_text tool implements a basic substring matching algorithm across decompressed text content. For each volume searched, the tool reads up to 50,000 characters of decompressed text from the beginning of the volume's TEXT.DKI database. While this provides good coverage for introductory and early-chapter content, matches in deep sections of very large volumes may be missed. The search is case-insensitive and matches partial words (searching for "frei" will match "Freiheit", "freie", "Freiraum", etc.). Results include surrounding context of approximately 50 characters on each side of the match, providing enough context to assess relevance. Each result is assigned a position value indicating the character offset within the text database, enabling subsequent targeted extraction of the full passage using get_text_content with the appropriate start_pos and length parameters.

## EPUB Output Format Details

The EPUB files generated by convert_volume_to_epub_file follow the EPUB 3.0 specification. Each EPUB file contains: a mimetype file, META-INF/container.xml, OEBPS/content.opf with metadata (title, author, language, unique identifier), OEBPS/toc.ncx for the navigation table of contents, and OEBPS/Text/ chapter XHTML files. The CSS styling provides a clean reading experience with serif font for body text and sans-serif for headings. The table of contents hierarchy matches the original volume's TREE.DKI structure. Chapter breaks are inserted at major navigation tree divisions. Images from the volume Images directory are embedded inline where the text database indicates image positions. The EPUB output is validated against basic EPUB structure requirements and is compatible with all major e-book reading applications including Apple Books, Google Play Books, Adobe Digital Editions, Calibre, and Kobo.

## Data File Format Reference

The Digitale Bibliothek uses a proprietary binary format optimized for CD-ROM storage. TEXT.DKI files use a section-based structure where each section contains multiple text records. Sections are compressed using a custom Run-Length Encoding algorithm that identifies repeated byte sequences and replaces them with shorter reference tokens. Section headers contain the section length, record count, and compression type flags. Text records within sections include a length prefix and optional inline formatting markers for bold, italic, and heading styles. The TREE.DKI file uses a plain text line-based format where indentation indicates hierarchy level. TREE.DKA is a binary companion that provides byte-offset mapping for direct access to sections. The remaining index files (HTX, PLX, SHX, SWX, TTX, WLX) provide specialized search indexes for hypertext links, plain text positions, abbreviations, keywords, titles, and word lists respectively.
