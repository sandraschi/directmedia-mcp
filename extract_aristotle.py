#!/usr/bin/env python3
"""
Extract Aristotle's Metaphysics from Directmedia DB002
Real reverse engineering implementation
"""

import zlib
from pathlib import Path

def extract_aristotle_from_index_ttx():
    """Extract Aristotle text from INDEX.TTX using zlib decompression"""

    ttx_path = Path(r"L:\Multimedia Files\Written Word\Digitale Bibliothek\DB002\Data\INDEX.TTX")

    if not ttx_path.exists():
        print("INDEX.TTX not found")
        return ""

    print("Extracting Aristotle's Metaphysics from INDEX.TTX...")
    print("=" * 55)

    with open(ttx_path, 'rb') as f:
        data = f.read()

    print(f"INDEX.TTX file size: {len(data):,} bytes")

    # Try to find and decompress zlib compressed blocks
    extracted_texts = []

    # Look for zlib signatures and try decompression
    i = 0
    while i < len(data) - 100:
        if data[i:i+2] == b'\x78\x9c':  # Zlib signature
            print(f"Found zlib block at offset {i}")

            try:
                # Try to decompress from this point
                compressed_data = data[i:]
                decompressed = zlib.decompress(compressed_data)
                text = decompressed.decode('latin-1', errors='replace')

                # Check if this contains philosophical content
                if len(text) > 500:  # Substantial text
                    print(f"Decompressed {len(text)} characters")

                    # Look for Aristotle-specific content
                    aristotle_sections = []
                    lines = text.split('\n')

                    for line in lines:
                        line = line.strip()
                        if len(line) > 20 and any(keyword in line.lower() for keyword in
                                                  ['aristoteles', 'aristotle', 'metaphysik', 'metaphysics',
                                                   'philosophie', 'philosophy', 'ethik', 'ethics']):
                            aristotle_sections.append(line)

                    if aristotle_sections:
                        print(f"Found {len(aristotle_sections)} Aristotle-related sections!")
                        extracted_texts.append(text)
                        break  # Found what we want

            except (zlib.error, UnicodeDecodeError) as e:
                print(f"Decompression failed: {e}")

        i += 1

    # If no compressed blocks found, try direct text extraction
    if not extracted_texts:
        print("No compressed blocks worked, trying direct text extraction...")

        i = 0
        while i < len(data) - 1000:
            if data[i] >= 32 and data[i] <= 255:
                start = i
                while i < len(data) and data[i] >= 32 and data[i] <= 255:
                    i += 1

                block_length = i - start
                if block_length >= 2000:  # Very substantial block
                    try:
                        text = data[start:i].decode('latin-1', errors='replace')

                        # Check for philosophy content
                        if any(keyword in text.lower() for keyword in
                              ['aristoteles', 'metaphysik', 'philosophie']):
                            print(f"Found direct text block at {start} ({len(text)} chars)")
                            extracted_texts.append(text)
                            break

                    except UnicodeDecodeError:
                        pass
            else:
                i += 1

    if extracted_texts:
        full_text = '\n\n'.join(extracted_texts)

        # Save to file
        output_file = Path('./aristotle_metaphysics_extracted.txt')
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(full_text)

        print(f"\nSUCCESS! Extracted {len(full_text)} characters")
        print(f"Saved to: {output_file.absolute()}")

        # Show sample
        print("\nSAMPLE EXTRACTED TEXT:")
        print("-" * 30)
        lines = full_text.split('\n')[:10]  # First 10 lines
        for line in lines:
            if line.strip():
                print(line.strip())
                if len([l for l in lines[:lines.index(line)+1] if l.strip()]) >= 5:
                    break

        return full_text
    else:
        print("No Aristotle text found in INDEX.TTX")
        return ""

if __name__ == '__main__':
    extract_aristotle_from_index_ttx()




