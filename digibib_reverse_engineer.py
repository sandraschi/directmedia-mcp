#!/usr/bin/env python3
"""
Directmedia Digibib5.exe Reverse Engineering Script
Analyzes the Digibib5.exe executable to extract decompression algorithms
"""

import struct
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import re

class DigibibReverseEngineer:
    def __init__(self, exe_path: str):
        self.exe_path = Path(exe_path)
        if not self.exe_path.exists():
            raise FileNotFoundError(f"Executable not found: {exe_path}")

        with open(self.exe_path, 'rb') as f:
            self.exe_data = f.read()

        self.exe_size = len(self.exe_data)
        print(f"Loaded executable: {self.exe_path} ({self.exe_size:,} bytes)")

    def find_strings(self, min_length: int = 4, encoding: str = 'latin-1') -> List[Tuple[int, str]]:
        """Extract strings from executable using null termination"""
        strings = []
        current_string = bytearray()
        start_offset = 0

        for i, byte in enumerate(self.exe_data):
            if byte == 0:  # Null terminator
                if len(current_string) >= min_length:
                    try:
                        string = current_string.decode(encoding, errors='ignore')
                        if string.strip():
                            strings.append((start_offset, string))
                    except UnicodeDecodeError:
                        pass
                current_string = bytearray()
                start_offset = i + 1
            else:
                if not current_string:  # Start of new string
                    start_offset = i
                current_string.append(byte)

        return strings

    def find_directmedia_patterns(self) -> Dict[str, List[Tuple[int, str]]]:
        """Find Directmedia-specific patterns and strings"""
        all_strings = self.find_strings()

        patterns = {
            'file_extensions': [],
            'compression_refs': [],
            'algorithm_refs': [],
            'directmedia_refs': []
        }

        # File extensions
        extensions = ['.DKI', '.DKA', '.HTX', '.TTX', '.PLX', '.WLX']
        for offset, string in all_strings:
            for ext in extensions:
                if ext in string.upper():
                    patterns['file_extensions'].append((offset, string))

        # Compression/decompression terms
        compress_terms = ['compress', 'decompress', 'unpack', 'pack', 'deflate', 'inflate',
                         'huffman', 'lz', 'zlib', 'gzip', 'bz2', 'algorithm', 'codec']
        for offset, string in all_strings:
            for term in compress_terms:
                if term.lower() in string.lower():
                    patterns['compression_refs'].append((offset, string))

        # Algorithm references
        algo_terms = ['table', 'tree', 'index', 'lookup', 'dictionary', 'key', 'value',
                     'bit', 'byte', 'shift', 'mask', 'xor', 'and', 'or']
        for offset, string in all_strings:
            for term in algo_terms:
                if term.lower() in string.lower():
                    patterns['algorithm_refs'].append((offset, string))

        # Directmedia specific
        directmedia_terms = ['directmedia', 'bibliothek', 'digitale', 'digibib', 'text.dki',
                           'index.', 'tree.dki', 'data\\']
        for offset, string in all_strings:
            for term in directmedia_terms:
                if term.lower() in string.lower():
                    patterns['directmedia_refs'].append((offset, string))

        return patterns

    def analyze_pe_structure(self) -> Dict[str, Any]:
        """Basic PE file structure analysis"""
        analysis = {}

        # DOS header
        if self.exe_data[:2] == b'MZ':
            dos_header = struct.unpack('<H', self.exe_data[0x3C:0x3E])[0]
            analysis['dos_header_offset'] = dos_header

            # PE signature
            pe_offset = dos_header
            if self.exe_data[pe_offset:pe_offset+4] == b'PE\x00\x00':
                analysis['pe_signature'] = True

                # COFF header
                coff_header = struct.unpack('<HHIIIHH', self.exe_data[pe_offset+4:pe_offset+24])
                analysis['machine_type'] = coff_header[0]
                analysis['number_of_sections'] = coff_header[1]
                analysis['timestamp'] = coff_header[2]

                # Optional header
                optional_header_offset = pe_offset + 24
                optional_magic = struct.unpack('<H', self.exe_data[optional_header_offset:optional_header_offset+2])[0]
                analysis['optional_magic'] = optional_magic

                if optional_magic == 0x10B:  # PE32
                    analysis['architecture'] = 'x86'
                    entry_point = struct.unpack('<I', self.exe_data[optional_header_offset+16:optional_header_offset+20])[0]
                    analysis['entry_point'] = entry_point
                elif optional_magic == 0x20B:  # PE32+
                    analysis['architecture'] = 'x64'
                    entry_point = struct.unpack('<I', self.exe_data[optional_header_offset+16:optional_header_offset+20])[0]
                    analysis['entry_point'] = entry_point

        return analysis

    def find_function_patterns(self) -> List[Dict[str, Any]]:
        """Look for common function patterns that might be decompression routines"""
        functions = []

        # Look for function prologs (common in x86)
        prologs = [
            b'\x55\x89\xE5',  # push ebp; mov ebp, esp
            b'\x55\x8B\xEC',  # push ebp; mov ebp, esp
            b'\x53\x56\x57',  # push ebx; push esi; push edi
        ]

        for prolog in prologs:
            offset = 0
            while True:
                pos = self.exe_data.find(prolog, offset)
                if pos == -1:
                    break

                # Check if this looks like a function start
                if pos > 0x1000:  # Skip early parts of file
                    functions.append({
                        'offset': pos,
                        'prolog': prolog.hex(),
                        'type': 'function_start'
                    })

                offset = pos + 1

        return functions

    def extract_embedded_data(self) -> Dict[str, Any]:
        """Look for embedded data tables or constants that might be Huffman tables"""
        data_analysis = {
            'large_arrays': [],
            'repeated_patterns': [],
            'huffman_like_tables': []
        }

        # Look for large contiguous data blocks
        i = 0
        while i < self.exe_size - 100:
            # Check for arrays of similar values (potential lookup tables)
            block_size = 0
            start_val = self.exe_data[i]

            while i + block_size < self.exe_size and block_size < 1000:
                if abs(self.exe_data[i + block_size] - start_val) <= 5:  # Similar values
                    block_size += 1
                else:
                    break

            if block_size >= 50:  # Large enough to be interesting
                data_analysis['large_arrays'].append({
                    'offset': i,
                    'size': block_size,
                    'avg_value': sum(self.exe_data[i:i+block_size]) / block_size
                })
                i += block_size
            else:
                i += 1

        # Look for Huffman-like tables (256 entries, 0-255 values)
        for i in range(0, self.exe_size - 256, 4):
            block = self.exe_data[i:i+256]
            if len(set(block)) > 200:  # Many different values, potential table
                data_analysis['huffman_like_tables'].append({
                    'offset': i,
                    'entropy': len(set(block)) / 256.0,
                    'min_val': min(block),
                    'max_val': max(block)
                })

        return data_analysis

def main():
    exe_path = r"C:\Program Files (x86)\Digitale Bibliothek 5\Digibib5.exe"

    try:
        re = DigibibReverseEngineer(exe_path)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return

    print("=" * 80)
    print("DIGIBIB5.EXE REVERSE ENGINEERING ANALYSIS")
    print("=" * 80)

    # PE structure analysis
    print("\n1. PE FILE STRUCTURE:")
    pe_info = re.analyze_pe_structure()
    for key, value in pe_info.items():
        print(f"   {key}: {value}")

    # Directmedia patterns
    print("\n2. DIRECTMEDIA PATTERNS:")
    patterns = re.find_directmedia_patterns()

    for category, items in patterns.items():
        if items:
            print(f"\n   {category.upper()}:")
            for offset, string in items[:10]:  # Show first 10
                print(f"      0x{offset:08X}: {repr(string)}")

    # Function patterns
    print("\n3. FUNCTION PATTERNS:")
    functions = re.find_function_patterns()
    print(f"   Found {len(functions)} potential function starts")
    for func in functions[:5]:  # Show first 5
        print(f"   Offset 0x{func['offset']:08X}: {func['prolog']}")

    # Embedded data
    print("\n4. EMBEDDED DATA ANALYSIS:")
    data_info = re.extract_embedded_data()

    if data_info['large_arrays']:
        print(f"   Large data arrays: {len(data_info['large_arrays'])}")
        for arr in data_info['large_arrays'][:3]:
            print(f"     Offset 0x{arr['offset']:08X}: {arr['size']} bytes, avg={arr['avg_value']:.1f}")

    if data_info['huffman_like_tables']:
        print(f"   Potential Huffman tables: {len(data_info['huffman_like_tables'])}")
        for table in data_info['huffman_like_tables'][:3]:
            print(f"     Offset 0x{table['offset']:08X}: entropy={table['entropy']:.3f}")

    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    main()
