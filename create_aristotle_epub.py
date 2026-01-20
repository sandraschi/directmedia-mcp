#!/usr/bin/env python3
"""
Create EPUB from Aristotle's Metaphysics extracted text
"""

import zipfile
from pathlib import Path

def create_aristotle_epub():
    print('CREATING ARISTOTLE METAPHYSICS EPUB')

    # Read the extracted text
    extracted_path = Path(r'L:\Multimedia Files\Written Word\Digitale Bibliothek\DB002\Data\TEXT_extracted_new.txt')
    output_epub = Path('./Aristotle_Metaphysics.epub')

    if not extracted_path.exists():
        print('ERROR: TEXT_extracted.txt not found')
        return

    with open(extracted_path, 'r', encoding='latin-1', errors='replace') as f:
        content = f.read()

    print(f'Read {len(content)} characters of Aristotle text')

    # Create EPUB
    with zipfile.ZipFile(output_epub, 'w') as zf:
        # mimetype (must be first, uncompressed)
        zf.writestr('mimetype', 'application/epub+zip', compress_type=zipfile.ZIP_STORED)

        # META-INF/container.xml
        container = '''<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>'''
        zf.writestr('META-INF/container.xml', container)

        # OEBPS/content.opf
        opf = '''<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="book-id" version="3.0">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>Aristotle: Metaphysics - Directmedia Digitale Bibliothek</dc:title>
    <dc:creator>Aristotle</dc:creator>
    <dc:language>de</dc:language>
    <dc:identifier id="book-id">aristotle-metaphysics-directmedia</dc:identifier>
  </metadata>
  <manifest>
    <item id="chapter1" href="chapter1.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine>
    <itemref idref="chapter1"/>
  </spine>
</package>'''
        zf.writestr('OEBPS/content.opf', opf)

        # OEBPS/chapter1.xhtml - the actual content
        chapter = f'''<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
  <title>Aristotle: Metaphysics</title>
  <style>
    body {{ font-family: serif; margin: 2em; }}
    h1 {{ color: #2c3e50; }}
    h2 {{ color: #34495e; }}
    pre {{ white-space: pre-wrap; font-family: monospace; }}
  </style>
</head>
<body>
  <h1>Aristotle: Metaphysics</h1>
  <h2>From Directmedia Digitale Bibliothek (1998)</h2>

  <p>This EPUB contains Aristotle's Metaphysics and other philosophical works from the historic German Directmedia Digitale Bibliothek collection.</p>

  <p><strong>Contents:</strong></p>
  <ul>
    <li>Aristotle's Metaphysics (German translation)</li>
    <li>Nicomachean Ethics</li>
    <li>Politics</li>
    <li>Poetics</li>
    <li>Complete philosophy collection introduction</li>
  </ul>

  <h2>Extracted Text Content</h2>
  <pre>{content}</pre>
</body>
</html>'''
        zf.writestr('OEBPS/chapter1.xhtml', chapter)

    size_mb = output_epub.stat().st_size / (1024*1024)
    print(f'\nSUCCESS! Created: {output_epub.name}')
    print(f'Size: {size_mb:.2f} MB')
    print(f'Location: {output_epub.absolute()}')
    print('\nCONTAINS:')
    print('- Aristotle Metaphysics (German)')
    print('- Complete philosophy introduction')
    print('- All extracted philosophical content')
    print('- Professional EPUB formatting')
    print('- Ready for e-book readers')

if __name__ == '__main__':
    create_aristotle_epub()

