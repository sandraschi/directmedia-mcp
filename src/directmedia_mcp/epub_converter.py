#!/usr/bin/env python3
"""
Directmedia EPUB Converter

Converts extracted Directmedia text content into proper EPUB format
for modern e-book readers and libraries.

Based on Gemini-generated code with enhancements for Directmedia integration.
"""

import os
import json
import zipfile
import re
from uuid import uuid4
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

# --- Constants & Templates ---

OPF_TEMPLATE = """<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>{title}</dc:title>
    <dc:creator>{author}</dc:creator>
    <dc:language>{lang}</dc:language>
    <dc:identifier id="uid">urn:uuid:{uuid}</dc:identifier>
    <meta property="dcterms:modified">{date}</meta>
    <dc:description>{description}</dc:description>
    <dc:publisher>Directmedia Publishing</dc:publisher>
    <dc:source>Directmedia Digitale Bibliothek</dc:source>
  </metadata>
  <manifest>
    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
    <item id="content" href="content.xhtml" media-type="application/xhtml+xml"/>
    <item id="css" href="style.css" media-type="text/css"/>
  </manifest>
  <spine>
    <itemref idref="content"/>
  </spine>
</package>"""

NAV_TEMPLATE = """<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head>
  <title>Navigation</title>
  <style>
    nav {{ font-family: serif; }}
    ol {{ list-style-type: none; }}
    a {{ text-decoration: none; color: #0066cc; }}
    a:hover {{ text-decoration: underline; }}
  </style>
</head>
<body>
  <nav epub:type="toc" id="toc">
    <h1>Table of Contents</h1>
    <ol>
      <li><a href="content.xhtml">{title}</a></li>
    </ol>
  </nav>
</body>
</html>"""

CONTENT_TEMPLATE = """<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
  <title>{title}</title>
  <link rel="stylesheet" type="text/css" href="style.css"/>
  <meta charset="utf-8"/>
</head>
<body>
  <div class="title-page">
    <h1 class="book-title">{title}</h1>
    <h2 class="book-author">{author}</h2>
    <p class="publisher-info">Directmedia Publishing • Digitale Bibliothek</p>
    <p class="volume-info">{volume_info}</p>
  </div>

  <div class="original-content">
    {body_html}
  </div>

  <div class="footer">
    <hr/>
    <p class="copyright">© Directmedia Publishing GmbH • Digitale Bibliothek</p>
    <p class="extraction-info">Extracted and converted to EPUB format</p>
  </div>
</body>
</html>"""

CSS_STYLES = """
/* EPUB Styles for Directmedia Content */

body {
    font-family: "Liberation Serif", "Times New Roman", serif;
    line-height: 1.4;
    margin: 5%;
    text-align: justify;
    font-size: 1em;
    color: #333;
}

.title-page {
    text-align: center;
    page-break-after: always;
    margin-bottom: 3em;
}

.book-title {
    font-size: 2em;
    font-weight: bold;
    margin-bottom: 0.5em;
    color: #000;
}

.book-author {
    font-size: 1.5em;
    font-style: italic;
    margin-bottom: 1em;
    color: #666;
}

.publisher-info {
    font-size: 0.9em;
    margin-bottom: 0.5em;
    color: #666;
}

.volume-info {
    font-size: 0.8em;
    color: #999;
}

/* Headings */
h1, h2, h3, h4, h5, h6 {
    color: #000;
    font-weight: bold;
    margin-top: 1.5em;
    margin-bottom: 0.5em;
    page-break-after: avoid;
}

h1 { font-size: 1.5em; }
h2 { font-size: 1.3em; }
h3 { font-size: 1.2em; }
h4 { font-size: 1.1em; }
h5, h6 { font-size: 1em; }

/* Paragraphs */
p {
    margin-bottom: 1em;
    text-indent: 1.5em;
    orphans: 2;
    widows: 2;
}

/* First paragraph after heading - no indent */
h1 + p, h2 + p, h3 + p, h4 + p, h5 + p, h6 + p {
    text-indent: 0;
}

/* Lists */
ul, ol {
    margin: 1em 0;
    padding-left: 2em;
}

li {
    margin-bottom: 0.5em;
}

/* Blockquotes */
blockquote {
    margin: 1em 2em;
    font-style: italic;
    color: #666;
    border-left: 4px solid #ccc;
    padding-left: 1em;
}

/* Tables */
table {
    border-collapse: collapse;
    margin: 1em auto;
    width: 90%;
}

th, td {
    border: 1px solid #ccc;
    padding: 0.5em;
    text-align: left;
}

th {
    background-color: #f5f5f5;
    font-weight: bold;
}

/* Code blocks */
pre, code {
    font-family: "Liberation Mono", "Courier New", monospace;
    background-color: #f8f8f8;
    padding: 0.2em 0.4em;
    border-radius: 3px;
}

pre {
    padding: 1em;
    overflow-x: auto;
    margin: 1em 0;
    white-space: pre-wrap;
}

/* Links */
a {
    color: #0066cc;
    text-decoration: underline;
}

/* Footer */
.footer {
    text-align: center;
    font-size: 0.8em;
    color: #999;
    margin-top: 3em;
    page-break-before: always;
}

.copyright {
    font-style: italic;
}

/* Page breaks */
.page-break {
    page-break-before: always;
}

/* German text improvements */
.german-quote {
    quotes: "\\201e" "\\201c" "\\201a" "\\2018";
}

/* Special Directmedia formatting */
.directmedia-note {
    background-color: #fff3cd;
    border: 1px solid #ffeaa7;
    padding: 1em;
    margin: 1em 0;
    border-radius: 5px;
    font-style: italic;
}

/* Preserve original formatting where possible */
.original-content {
    /* Styles for extracted Directmedia content */
}
"""


def sanitize_filename(name: str) -> str:
    """
    Prevents filesystem errors by removing illegal characters.
    Essential for processing thousands of legacy titles.
    """
    if not name:
        return "Unknown"

    # Remove characters that are unsafe for filenames
    s = re.sub(r'[\\/*?:"<>|]', "", name)
    # Replace problematic characters with safe alternatives
    s = re.sub(r'[^\w\s\-\.]', "_", s)
    # Truncate to avoid filesystem limits
    s = s.strip()[:100]
    # Ensure it's not empty
    if not s:
        s = "Unknown"
    return s


def sanitize_html_content(text: str) -> str:
    """
    Clean and prepare extracted Directmedia text for HTML inclusion.
    """
    if not text:
        return "<p>No content extracted.</p>"

    # Basic HTML escaping for safety
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")

    # Convert line breaks to paragraphs (basic)
    paragraphs = text.split('\n\n')
    html_paragraphs = []

    for para in paragraphs:
        para = para.strip()
        if para:
            # Simple paragraph detection
            if len(para) > 50:  # Likely a content paragraph
                html_paragraphs.append(f"<p>{para}</p>")
            else:  # Likely a heading or short text
                html_paragraphs.append(f"<p><strong>{para}</strong></p>")

    return "\n".join(html_paragraphs) if html_paragraphs else "<p>Content could not be formatted.</p>"


def create_single_epub(book_data: Dict[str, Any], output_dir: Union[str, Path]) -> bool:
    """
    Generates a single EPUB artifact from Directmedia extracted content.
    """
    title = book_data.get('title', 'Unknown Title')
    author = book_data.get('author', 'Unknown Author')
    body_text = book_data.get('content', '')
    volume_id = book_data.get('volume_id', 'Unknown Volume')
    volume_title = book_data.get('volume_title', '')
    lang = book_data.get('lang', 'de')

    # Prepare content
    body_html = sanitize_html_content(body_text)

    # Create description
    description = f"Extracted from Directmedia Digitale Bibliothek - {volume_title}"

    # Generate filename
    safe_title = sanitize_filename(title)
    safe_author = sanitize_filename(author)
    filename = f"{safe_author} - {safe_title}.epub"
    filepath = Path(output_dir) / filename

    # Ensure output directory exists
    filepath.parent.mkdir(parents=True, exist_ok=True)

    # Metadata
    book_uuid = str(uuid4())
    current_date = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    # Volume info for display
    volume_info = f"Volume: {volume_id}"
    if volume_title:
        volume_info += f" - {volume_title}"

    try:
        with zipfile.ZipFile(filepath, 'w', zipfile.ZIP_DEFLATED) as zf:
            # 1. Mimetype (Stored, not deflated - critical for validity)
            zf.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)

            # 2. Container
            zf.writestr("META-INF/container.xml",
                        """<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>""")

            # 3. Content files
            zf.writestr("OEBPS/style.css", CSS_STYLES)
            zf.writestr("OEBPS/nav.xhtml", NAV_TEMPLATE.format(title=title))

            # Inject Content
            zf.writestr("OEBPS/content.xhtml", CONTENT_TEMPLATE.format(
                title=title,
                author=author,
                volume_info=volume_info,
                body_html=body_html
            ))

            # Package Definition
            zf.writestr("OEBPS/content.opf", OPF_TEMPLATE.format(
                title=title,
                author=author,
                lang=lang,
                uuid=book_uuid,
                date=current_date,
                description=description
            ))

        print(f"[OK] Created EPUB: {filename}")
        return True

    except Exception as e:
        print(f"[ERROR] Error creating {filename}: {e}")
        return False


def convert_volume_to_epub(library_path: Union[str, Path],
                          volume_id: str,
                          output_dir: Union[str, Path]) -> Dict[str, Any]:
    """
    Convert an entire Directmedia volume to EPUB format.

    This function integrates with the DirectmediaLibrary to extract content
    and convert it to EPUB format.
    """
    from .library import DirectmediaLibrary

    results = {
        "volume_id": volume_id,
        "epub_files_created": 0,
        "errors": [],
        "output_dir": str(Path(output_dir))
    }

    try:
        # Initialize library
        lib = DirectmediaLibrary(str(library_path))

        # Get volume info
        volume_info = lib.get_volume_info(volume_id)
        if not volume_info:
            results["errors"].append(f"Volume {volume_id} not found")
            return results

        print(f"Converting volume: {volume_info.title}")

        # For now, create a single EPUB with all text content
        # Future enhancement: split into chapters/books based on structure
        try:
            # Extract all available text content
            text_content = lib.get_text_content(volume_id, length=50000)  # First 50KB

            if text_content and 'content' in text_content:
                book_data = {
                    'title': volume_info.title,
                    'author': 'Various Authors',  # Could be enhanced to extract from content
                    'content': text_content['content'],
                    'volume_id': volume_id,
                    'volume_title': volume_info.title,
                    'lang': 'de'  # German content
                }

                if create_single_epub(book_data, output_dir):
                    results["epub_files_created"] = 1
                    print(f"✓ Successfully converted volume {volume_id} to EPUB")
                else:
                    results["errors"].append(f"Failed to create EPUB for volume {volume_id}")
            else:
                results["errors"].append(f"No text content found for volume {volume_id}")

        except Exception as e:
            results["errors"].append(f"Error processing volume {volume_id}: {str(e)}")

    except Exception as e:
        results["errors"].append(f"Error initializing library: {str(e)}")

    return results


def batch_convert_library(library_path: Union[str, Path],
                         output_dir: Union[str, Path],
                         volume_filter: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Convert multiple Directmedia volumes to EPUB format.
    """
    from .library import DirectmediaLibrary

    results = {
        "total_volumes_processed": 0,
        "epub_files_created": 0,
        "errors": [],
        "volumes_converted": [],
        "output_dir": str(Path(output_dir))
    }

    try:
        lib = DirectmediaLibrary(str(library_path))
        volumes = lib.list_volumes()

        volumes_to_process = volumes
        if volume_filter:
            volumes_to_process = [v for v in volumes if v.id in volume_filter]

        print(f"Converting {len(volumes_to_process)} volumes to EPUB...")

        for volume in volumes_to_process:
            print(f"Processing volume: {volume.id} - {volume.title}")

            volume_result = convert_volume_to_epub(library_path, volume.id, output_dir)

            results["total_volumes_processed"] += 1
            results["epub_files_created"] += volume_result.get("epub_files_created", 0)

            if volume_result.get("epub_files_created", 0) > 0:
                results["volumes_converted"].append(volume.id)

            if volume_result.get("errors"):
                results["errors"].extend(volume_result["errors"])

    except Exception as e:
        results["errors"].append(f"Batch conversion failed: {str(e)}")

    print("\nBatch conversion complete:")
    print(f"  Volumes processed: {results['total_volumes_processed']}")
    print(f"  EPUB files created: {results['epub_files_created']}")
    print(f"  Output directory: {results['output_dir']}")
    if results["errors"]:
        print(f"  Errors encountered: {len(results['errors'])}")

    return results


# --- Command Line Interface ---

if __name__ == "__main__":
    # Example usage
    import argparse

    parser = argparse.ArgumentParser(description="Convert Directmedia volumes to EPUB format")
    parser.add_argument("library_path", help="Path to Directmedia library")
    parser.add_argument("volume_id", help="Volume ID to convert")
    parser.add_argument("output_dir", help="Output directory for EPUB files")

    args = parser.parse_args()

    result = convert_volume_to_epub(args.library_path, args.volume_id, args.output_dir)

    if result["epub_files_created"] > 0:
        print("Conversion successful!")
    else:
        print("Conversion failed. Errors:")
        for error in result["errors"]:
            print(f"  - {error}")
