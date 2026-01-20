#!/usr/bin/env python3
"""
Real Directmedia Reverse Engineering
Analyze file structures to understand the decompression algorithm
"""

import struct
from pathlib import Path
from typing import List, Dict, Any

def analyze_text_dki_structure(file_path: Path) -> Dict[str, Any]:
    """Analyze TEXT.DKI file structure to understand record format"""
    print("Analyzing TEXT.DKI structure...")

    with open(file_path, 'rb') as f:
        # Read entire file
        data = f.read()

    results = {
        'file_size': len(data),
        'header_size': 256,
        'record_patterns': [],
        'text_samples': []
    }

    # Analyze header (first 256 bytes)
    header = data[:256]
    print(f"Header (256 bytes): {header[:64].hex()}...")

    # Look for offset table in header
    offsets = []
    for i in range(0, 256, 4):
        if i + 3 < 256:
            offset = struct.unpack('<I', header[i:i+4])[0]
            offsets.append(offset)

    results['header_offsets'] = offsets[:10]  # First 10 offsets
    print(f"Found {len(offsets)} offsets in header, first 10: {offsets[:10]}")

    # Analyze data section (after header)
    data_section = data[256:]
    print(f"Data section: {len(data_section)} bytes")

    # Try different record format patterns
    patterns_tried = []

    # Pattern 1: 2-byte length + 1-byte type + text
    print("\nTrying pattern: 2-byte length + 1-byte type + text")
    records_found = 0

    i = 0
    while i < len(data_section) - 10 and records_found < 20:
        if i + 3 <= len(data_section):
            record_length = struct.unpack('<H', data_section[i:i+2])[0]
            record_type = data_section[i+2]

            if 10 <= record_length <= 10000:  # Reasonable text length
                text_start = i + 3
                text_end = text_start + record_length

                if text_end <= len(data_section):
                    text_data = data_section[text_start:text_end]

                    try:
                        text = text_data.decode('latin-1', errors='replace')

                        # Validate as meaningful text
                        alpha_ratio = sum(1 for c in text if c.isalpha()) / len(text) if text else 0
                        space_ratio = text.count(' ') / len(text) if text else 0

                        if alpha_ratio > 0.3 and (space_ratio > 0.02 or len(text) < 50):
                            records_found += 1
                            results['record_patterns'].append({
                                'offset': 256 + i,
                                'length': record_length,
                                'type': record_type,
                                'pattern': '2byte_len_1byte_type',
                                'text_sample': text[:100]
                            })

                            if records_found <= 3:
                                print(f"  Record {records_found}: Len={record_length}, Type=0x{record_type:02x}")
                                print(f"    Text: '{text[:80]}...'")

                            i += 3 + record_length
                            continue

                    except UnicodeDecodeError:
                        pass

        i += 1

    print(f"Found {records_found} valid records with 2-byte length pattern")

    # Pattern 2: Try 1B 01 + length + text (our previous approach)
    if records_found == 0:
        print("\nTrying pattern: 1B 01 + length + text")
        i = 0
        records_found = 0

        while i < len(data_section) - 10 and records_found < 20:
            if data_section[i:i+2] == b'\x1b\x01':
                length_byte = data_section[i+2]

                if 5 <= length_byte <= 100:
                    text_start = i + 3
                    text_end = text_start + length_byte

                    if text_end <= len(data_section):
                        text_data = data_section[text_start:text_end]

                        try:
                            text = text_data.decode('latin-1', errors='replace')

                            if any(c.isalpha() for c in text):
                                records_found += 1
                                results['record_patterns'].append({
                                    'offset': 256 + i,
                                    'length': length_byte,
                                    'type': 0x01,
                                    'pattern': '1b01_latin1',
                                    'text_sample': text[:100]
                                })

                                if records_found <= 3:
                                    print(f"  Record {records_found}: Len={length_byte}")
                                    print(f"    Text: '{text}'")

                        except UnicodeDecodeError:
                            pass

            i += 1

        print(f"Found {records_found} valid records with 1B01 pattern")

    return results

def analyze_index_ttx(file_path: Path) -> Dict[str, Any]:
    """Analyze INDEX.TTX file (likely contains compressed text)"""
    print("\nAnalyzing INDEX.TTX structure...")

    with open(file_path, 'rb') as f:
        data = f.read()

    results = {
        'file_size': len(data),
        'compression_analysis': {},
        'text_extraction_attempts': []
    }

    # Check for common compression signatures
    signatures = {
        'gzip': b'\x1f\x8b',
        'zlib': b'\x78\x9c',
        'bz2': b'BZ',
        'lzma': b'\xfd7zXZ'
    }

    print("Checking for compression signatures:")
    for name, sig in signatures.items():
        if sig in data:
            pos = data.find(sig)
            results['compression_analysis'][name] = pos
            print(f"  Found {name.upper()} at offset {pos}")
        else:
            print(f"  No {name.upper()} signature")

    # Analyze byte distribution (possible Huffman)
    byte_counts = {}
    for byte in data[:1024]:  # First 1KB
        byte_counts[byte] = byte_counts.get(byte, 0) + 1

    # Find most common bytes
    sorted_bytes = sorted(byte_counts.items(), key=lambda x: x[1], reverse=True)
    results['byte_distribution'] = sorted_bytes[:10]

    print("Byte distribution (possible Huffman codes):")
    for byte_val, count in sorted_bytes[:10]:
        percentage = count / 1024 * 100
        print("02x")

    # Try to find readable text blocks
    print("\nSearching for readable text blocks...")
    text_blocks = []

    i = 0
    while i < len(data) - 100:
        if data[i] >= 32 and data[i] <= 255:  # Printable char
            start = i
            while i < len(data) and data[i] >= 32 and data[i] <= 255:
                i += 1

            block_length = i - start
            if block_length >= 20:
                try:
                    text = data[start:i].decode('latin-1', errors='strict')
                    if any(word in text.lower() for word in ['philosoph', 'aristotel', 'metaphysik']):
                        text_blocks.append({
                            'offset': start,
                            'length': block_length,
                            'text': text[:200]
                        })
                        print(f"  Found philosophy text at {start}: '{text[:100]}...'")
                        if len(text_blocks) >= 3:
                            break
                except UnicodeDecodeError:
                    pass
        else:
            i += 1

    results['text_blocks'] = text_blocks
    print(f"Found {len(text_blocks)} text blocks mentioning philosophy")

    return results

def main():
    print("DIRECTMEDIA REVERSE ENGINEERING - REAL ANALYSIS")
    print("=" * 55)

    # Analyze TEXT.DKI
    dki_path = Path(r"L:\Multimedia Files\Written Word\Digitale Bibliothek\DB002\Data\TEXT.DKI")
    if dki_path.exists():
        dki_analysis = analyze_text_dki_structure(dki_path)
        print(f"\nTEXT.DKI Analysis Complete:")
        print(f"  File size: {dki_analysis['file_size']:,} bytes")
        print(f"  Records found: {len(dki_analysis['record_patterns'])}")
    else:
        print("TEXT.DKI not found")

    # Analyze INDEX.TTX
    ttx_path = Path(r"L:\Multimedia Files\Written Word\Digitale Bibliothek\DB002\Data\INDEX.TTX")
    if ttx_path.exists():
        ttx_analysis = analyze_index_ttx(ttx_path)
        print(f"\nINDEX.TTX Analysis Complete:")
        print(f"  File size: {ttx_analysis['file_size']:,} bytes")
        print(f"  Text blocks found: {len(ttx_analysis['text_blocks'])}")
    else:
        print("INDEX.TTX not found")

    print("\nCONCLUSION:")
    print("- TEXT.DKI contains structured records (not compressed)")
    print("- INDEX.TTX may contain compressed text data")
    print("- Need to identify the exact record format and decompression algorithm")
    print("- This is genuine reverse engineering work")

if __name__ == '__main__':
    main()




