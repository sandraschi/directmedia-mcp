#!/usr/bin/env python3
"""
Test script for Directmedia MCP functionality
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from directmedia_mcp.library import DirectmediaLibrary


def test_basic_functionality():
    """Test basic library functionality"""

    library_path = r"L:\Multimedia Files\Written Word\Digitale Bibliothek"

    print("Testing Directmedia Library Access")
    print("=" * 40)

    try:
        # Initialize library
        lib = DirectmediaLibrary(library_path)
        print(f"[OK] Library initialized at: {library_path}")

        # List volumes
        volumes = lib.list_volumes()
        print(f"[OK] Found {len(volumes)} volumes")

        # Show first few volumes
        print("\nFirst 5 volumes:")
        for vol in volumes[:5]:
            print(f"  {vol.id}: {vol.title} ({vol.size_mb}MB)")

        # Test volume info
        if volumes:
            vol_info = lib.get_volume_info(volumes[0].id)
            print(f"\n[OK] Volume info for {volumes[0].id}:")
            print(f"  Title: {vol_info.title}")
            print(f"  Has text: {vol_info.has_text}")
            print(f"  Has images: {vol_info.has_images}")
            print(f"  Size: {vol_info.size_mb}MB")

        # Test text extraction
        if volumes and volumes[0].has_text:
            content = lib.get_text_content(volumes[0].id, 0, 500)
            if "content" in content:
                print(f"\n[OK] Text extraction from {volumes[0].id}:")
                print(f"  Length: {len(content['content'])} characters")
                # Safe preview that handles encoding issues
                try:
                    preview = content["content"][:100]
                    print(f"  Preview: {preview}...")
                except UnicodeEncodeError:
                    print("  Preview: [Text contains special characters]")
                except Exception as e:
                    print(f"  Preview error: {e}")

        # Test search
        if volumes:
            results = lib.search_text("philosoph", volumes[0].id, 3)
            print(f"\n[OK] Search results for 'philosoph' in {volumes[0].id}:")
            print(f"  Found {len(results)} matches")

        # Test structure analysis
        if volumes:
            analysis = lib.analyze_volume_structure(volumes[0].id)
            print(f"\n[OK] Structure analysis for {volumes[0].id}:")
            print(f"  Data files: {len(analysis.get('data_files', {}))}")
            print(f"  Total size: {analysis.get('total_size_mb', 0)}MB")

        print("\n[OK] All tests completed successfully!")

    except Exception as e:
        print(f"[ERROR] Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_basic_functionality()
