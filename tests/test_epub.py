#!/usr/bin/env python3
"""
Test the EPUB converter functionality
"""

import tempfile
import os
from src.directmedia_mcp.epub_converter import sanitize_filename, create_single_epub

def test_epub_converter():
    print("Testing EPUB Converter...")
    print("=" * 50)

    # Test filename sanitization
    test_name = 'Goethe: Faust - Erster Teil (mit Anmerkungen)'
    sanitized = sanitize_filename(test_name)
    print(f"[OK] Filename sanitization: '{test_name}' -> '{sanitized}'")

    # Test basic EPUB creation with mock data
    with tempfile.TemporaryDirectory() as temp_dir:
        test_data = {
            'title': 'Test Book - Faust',
            'author': 'Johann Wolfgang von Goethe',
            'content': '''Dies ist ein Testbuch mit deutschem Text.
Über allen Gipfeln ist Ruh, in allen Wipfeln spürest du kaum einen Hauch.
Die Vögelein schweigen im Walde. Warte nur, balde ruhest du auch.

Faust: Habe nun, ach! Philosophie,
Juristerei und Medizin,
Und leider auch Theologie
Durchaus studiert, mit heißem Bemühn.''',
            'volume_id': 'DB004',
            'volume_title': 'Goethe - Faust',
            'lang': 'de'
        }

        print(f"Creating EPUB for: {test_data['title']}")
        success = create_single_epub(test_data, temp_dir)

        if success:
            print("[OK] EPUB creation successful")

            # Check if file was created
            epub_files = [f for f in os.listdir(temp_dir) if f.endswith('.epub')]
            if epub_files:
                epub_path = os.path.join(temp_dir, epub_files[0])
                file_size = os.path.getsize(epub_path)
                print(f"[OK] EPUB file created: {epub_files[0]} ({file_size} bytes)")

                # Basic validation - check if it's a zip file (EPUB is ZIP-based)
                with open(epub_path, 'rb') as f:
                    header = f.read(4)
                    if header.startswith(b'PK'):  # ZIP file signature
                        print("[OK] Valid EPUB format (ZIP-based)")
                    else:
                        print("[ERROR] Invalid EPUB format")

            else:
                print("[ERROR] No EPUB file found")
        else:
            print("[ERROR] EPUB creation failed")

    print("\nEPUB Converter test completed!")

if __name__ == "__main__":
    test_epub_converter()
