#!/usr/bin/env python3
"""
Export Deutsche Literatur volumes to EPUB format
"""

import time
import os
from pathlib import Path

def export_deutsche_literatur():
    """Export the Deutsche Literatur volumes to EPUB"""

    # Output directory for EPUB files
    output_dir = Path("D:/Dev/repos/deutsche_literatur_epub")
    output_dir.mkdir(exist_ok=True)

    print("Starting Deutsche Literatur EPUB export...")
    print(f"Output directory: {output_dir}")

    # Deutsche Literatur volumes identified from directory listing
    deutsche_literatur_volumes = [
        "DB088",  # Deutsche Literatur im Mittelalter
        "DB125",  # Deutsche Literatur von Luther bis Tucholsky
    ]

    print(f"Found {len(deutsche_literatur_volumes)} Deutsche Literatur volumes:")
    for vol in deutsche_literatur_volumes:
        print(f"  - {vol}")

    # Since the MCP server is running, we would normally use MCP client calls
    # But for this demo, let's simulate the process by calling the direct functions

    try:
        from directmedia_mcp.library import DirectmediaLibrary
        from directmedia_mcp.epub_converter import batch_convert_library

        # Initialize library
        library_path = r"C:\Users\sandr\OneDrive\Written Word\Digitale Bibliothek"
        print(f"Initializing library from: {library_path}")

        library = DirectmediaLibrary(library_path)

        # List volumes to verify
        volumes = library.list_volumes()
        print(f"Library contains {len(volumes)} volumes")

        # Filter for Deutsche Literatur volumes
        target_volumes = [v for v in volumes if v.id in deutsche_literatur_volumes]
        print(f"Found {len(target_volumes)} target volumes for conversion")

        for vol in target_volumes:
            print(f"  - {vol.id}: {vol.title} ({vol.size_mb:.1f} MB)")

        # Perform batch conversion
        print("\nStarting EPUB conversion...")
        result = batch_convert_library(library_path, str(output_dir), deutsche_literatur_volumes)

        print("\nConversion Results:")
        print(f"  - Total volumes processed: {result['total_volumes_processed']}")
        print(f"  - EPUB files created: {result['epub_files_created']}")
        print(f"  - Volumes converted: {len(result['volumes_converted'])}")
        print(f"  - Output directory: {result['output_dir']}")

        if result['volumes_converted']:
            print("\nConverted volumes:")
            for vol_id in result['volumes_converted']:
                print(f"  - {vol_id}")

        if result.get('errors'):
            print("\nErrors encountered:")
            for error in result['errors']:
                print(f"  - {error}")

        # List the created EPUB files
        epub_files = list(output_dir.glob("*.epub"))
        if epub_files:
            print(f"\nCreated {len(epub_files)} EPUB files:")
            for epub in sorted(epub_files):
                size_mb = epub.stat().st_size / (1024*1024)
                print(f"  - {epub.name} ({size_mb:.2f} MB)")

        print("\nEPUB export completed successfully!")
        print(f"You can now open the EPUB files in any e-book reader (Calibre, Apple Books, etc.)")

    except Exception as e:
        print(f"Error during EPUB export: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    export_deutsche_literatur()
