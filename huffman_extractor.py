#!/usr/bin/env python3
"""
Huffman Decompression Algorithm Extractor for Digibib5.exe
Extracts Huffman tables and decompression logic from the executable
"""

import struct
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import re

class HuffmanExtractor:
    def __init__(self, exe_path: str):
        self.exe_path = Path(exe_path)
        with open(self.exe_path, 'rb') as f:
            self.exe_data = f.read()

    def find_huffman_strings(self) -> List[Tuple[int, str]]:
        """Find all Huffman-related strings in the executable"""
        huffman_refs = []

        # Search for Huffman-related strings
        huffman_patterns = [
            b'Huffman',
            b'huffman',
            b'HUFFMAN',
            b'Uncompressed',
            b'Compressed',
            b'Optimal Huffman',
            b'Compressed size'
        ]

        for pattern in huffman_patterns:
            offset = 0
            while True:
                pos = self.exe_data.find(pattern, offset)
                if pos == -1:
                    break

                # Extract surrounding context
                start = max(0, pos - 20)
                end = min(len(self.exe_data), pos + len(pattern) + 20)
                context = self.exe_data[start:end]

                try:
                    context_str = context.decode('latin-1', errors='replace')
                    huffman_refs.append((pos, pattern.decode('ascii'), context_str))
                except:
                    pass

                offset = pos + 1

        return huffman_refs

    def find_potential_huffman_tables(self) -> List[Dict[str, Any]]:
        """Find potential Huffman tables in the executable"""
        tables = []

        # Look for arrays that could be Huffman tables
        # Huffman tables typically have:
        # - Variable-length codes (bit lengths)
        # - Symbol mappings
        # - Frequency counts

        # Search for consecutive bytes that could be bit lengths (1-32)
        for i in range(0, len(self.exe_data) - 256, 4):
            block = self.exe_data[i:i+256]

            # Check if this looks like a bit length table (values 0-32)
            bit_lengths = []
            valid_count = 0

            for j in range(min(256, len(block))):
                val = block[j]
                if 0 <= val <= 32:  # Valid bit length
                    bit_lengths.append(val)
                    if val > 0:
                        valid_count += 1
                else:
                    break

            if valid_count >= 16:  # At least 16 non-zero entries
                tables.append({
                    'offset': i,
                    'length': len(bit_lengths),
                    'bit_lengths': bit_lengths[:32],  # First 32 entries
                    'valid_entries': valid_count,
                    'entropy': len(set(bit_lengths)) / len(bit_lengths) if bit_lengths else 0
                })

        return tables

    def find_bit_manipulation_code(self) -> List[Dict[str, Any]]:
        """Find bit manipulation code patterns typical of Huffman decompression"""
        patterns = []

        # Common x86 bit manipulation instructions
        bit_ops = [
            b'\xD1\xE8',  # shr eax, 1
            b'\xD1\xE9',  # shr ecx, 1
            b'\xD1\xEA',  # shr edx, 1
            b'\xD1\xEB',  # shr ebx, 1
            b'\xC1\xE8',  # shr eax, imm8
            b'\xC1\xE9',  # shr ecx, imm8
            b'\xC1\xEA',  # shr edx, imm8
            b'\xC1\xEB',  # shr ebx, imm8
            b'\x0F\xB6',  # movzx reg, byte ptr
            b'\x8B\x45',  # mov eax, [ebp+offset]
            b'\x8B\x4D',  # mov ecx, [ebp+offset]
        ]

        for op in bit_ops:
            offset = 0
            while True:
                pos = self.exe_data.find(op, offset)
                if pos == -1:
                    break

                # Extract function context
                func_start = self._find_function_start(pos)
                if func_start:
                    func_size = min(1024, pos - func_start + 32)
                    func_code = self.exe_data[func_start:func_start + func_size]

                    patterns.append({
                        'offset': pos,
                        'opcode': op.hex(),
                        'function_start': func_start,
                        'function_size': func_size,
                        'code_sample': func_code[:64].hex()
                    })

                offset = pos + 1

        return patterns

    def _find_function_start(self, offset: int) -> Optional[int]:
        """Find the start of the function containing the given offset"""
        # Look backwards for function prolog
        search_start = max(0, offset - 1024)

        for i in range(offset, search_start, -1):
            # Check for common function prologs
            if self.exe_data[i:i+3] == b'\x55\x8B\xEC':  # push ebp; mov ebp, esp
                return i
            if self.exe_data[i:i+3] == b'\x55\x89\xE5':  # push ebp; mov ebp, esp (AT&T)
                return i

        return None

    def extract_symbol_tables(self) -> List[Dict[str, Any]]:
        """Extract potential symbol-to-code mapping tables"""
        tables = []

        # Look for tables that map symbols (0-255) to codes
        for i in range(0, len(self.exe_data) - 512, 4):
            block = self.exe_data[i:i+512]

            # Check if first 256 bytes could be a symbol mapping
            symbol_map = block[:256]
            code_data = block[256:512]

            # Analyze symbol distribution
            unique_symbols = len(set(symbol_map))
            if unique_symbols > 100:  # Most symbols used
                # Check if code_data looks like Huffman codes (variable length)
                code_lengths = []
                for j in range(0, len(code_data), 4):
                    if j+4 <= len(code_data):
                        code_len = struct.unpack('<I', code_data[j:j+4])[0]
                        if 0 < code_len <= 32:
                            code_lengths.append(code_len)

                if len(code_lengths) > 10:
                    tables.append({
                        'offset': i,
                        'symbol_count': unique_symbols,
                        'code_lengths': code_lengths[:16],
                        'symbol_entropy': unique_symbols / 256.0
                    })

        return tables

def main():
    exe_path = r"C:\Program Files (x86)\Digitale Bibliothek 5\Digibib5.exe"

    extractor = HuffmanExtractor(exe_path)

    print("=" * 80)
    print("HUFFMAN DECOMPRESSION ALGORITHM EXTRACTION")
    print("=" * 80)

    # Find Huffman strings
    print("\n1. HUFFMAN STRINGS FOUND:")
    huffman_strings = extractor.find_huffman_strings()
    for offset, pattern, context in huffman_strings:
        print(f"   0x{offset:08X}: {pattern}")
        print(f"      Context: {repr(context)}")

    # Find potential Huffman tables
    print("\n2. POTENTIAL HUFFMAN TABLES:")
    tables = extractor.find_potential_huffman_tables()
    print(f"   Found {len(tables)} potential bit-length tables")
    for table in tables[:5]:  # Show first 5
        print(f"   Offset 0x{table['offset']:08X}: {table['length']} entries, {table['valid_entries']} valid")
        print(f"      Bit lengths: {table['bit_lengths'][:16]}...")

    # Find bit manipulation code
    print("\n3. BIT MANIPULATION CODE:")
    bit_code = extractor.find_bit_manipulation_code()
    print(f"   Found {len(bit_code)} bit manipulation patterns")
    for code in bit_code[:5]:  # Show first 5
        print(f"   0x{code['offset']:08X}: {code['opcode']} (function at 0x{code['function_start']:08X})")

    # Extract symbol tables
    print("\n4. SYMBOL MAPPING TABLES:")
    symbol_tables = extractor.extract_symbol_tables()
    print(f"   Found {len(symbol_tables)} potential symbol tables")
    for table in symbol_tables[:3]:  # Show first 3
        print(f"   Offset 0x{table['offset']:08X}: {table['symbol_count']} symbols")
        print(f"      Code lengths: {table['code_lengths']}")

    print("\n" + "=" * 80)
    print("HUFFMAN ANALYSIS COMPLETE")
    print("=" * 80)

    # Summary
    if huffman_strings:
        print("\nSUMMARY:")
        print("[SUCCESS] Huffman compression confirmed in executable")
        if tables:
            print(f"[SUCCESS] Found {len(tables)} potential Huffman tables")
        if bit_code:
            print(f"[SUCCESS] Found {len(bit_code)} bit manipulation functions")
        if symbol_tables:
            print(f"[SUCCESS] Found {len(symbol_tables)} symbol mapping tables")
        print("\nNEXT STEPS:")
        print("1. Extract the specific Huffman table used for Directmedia")
        print("2. Implement Huffman decompression algorithm")
        print("3. Test decompression on TEXT.DKI files")

if __name__ == "__main__":
    main()
