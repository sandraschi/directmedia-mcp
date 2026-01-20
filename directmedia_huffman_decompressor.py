#!/usr/bin/env python3
"""
Directmedia Huffman Decompressor
Implements Huffman decompression for Directmedia TEXT.DKI files based on reverse engineering
"""

import struct
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, BinaryIO
from dataclasses import dataclass
import bitarray
from bitarray import bitarray

@dataclass
class HuffmanNode:
    symbol: Optional[int] = None
    left: Optional['HuffmanNode'] = None
    right: Optional['HuffmanNode'] = None

class DirectmediaHuffmanDecompressor:
    def __init__(self):
        self.huffman_tree: Optional[HuffmanNode] = None
        self.bit_lengths: List[int] = []

    def build_huffman_tree_from_lengths(self, bit_lengths: List[int]) -> HuffmanNode:
        """Build Huffman tree from bit length array (canonical Huffman coding)"""
        if not bit_lengths:
            raise ValueError("Empty bit lengths")

        # Find max bit length
        max_bits = max(bit_lengths) if bit_lengths else 0

        # Count symbols at each bit length
        length_count = [0] * (max_bits + 1)
        for length in bit_lengths:
            if length > 0:
                length_count[length] += 1

        # Build canonical codes
        code = 0
        next_code = [0] * (max_bits + 1)
        for bits in range(1, max_bits + 1):
            code = (code + length_count[bits - 1]) << 1
            next_code[bits] = code

        # Assign codes to symbols
        symbol_codes = {}
        for symbol, length in enumerate(bit_lengths):
            if length > 0:
                symbol_codes[symbol] = format(next_code[length], f'0{length}b')
                next_code[length] += 1

        # Build Huffman tree
        root = HuffmanNode()

        for symbol, code in symbol_codes.items():
            node = root
            for bit in code:
                if bit == '0':
                    if node.left is None:
                        node.left = HuffmanNode()
                    node = node.left
                else:
                    if node.right is None:
                        node.right = HuffmanNode()
                    node = node.right
            node.symbol = symbol

        return root

    def decompress_stream(self, compressed_data: bytes, expected_size: Optional[int] = None) -> bytes:
        """Decompress Huffman-compressed data"""
        if not self.huffman_tree:
            raise ValueError("Huffman tree not initialized")

        # Convert to bit stream
        bits = bitarray()
        bits.frombytes(compressed_data)

        output = bytearray()
        node = self.huffman_tree

        for bit in bits:
            if bit:  # 1 = right
                node = node.right
            else:   # 0 = left
                node = node.left

            if node is None:
                break  # End of stream or error

            if node.symbol is not None:
                output.append(node.symbol)
                node = self.huffman_tree  # Reset to root

                # Check if we've decompressed enough
                if expected_size and len(output) >= expected_size:
                    break

        return bytes(output)

    def analyze_directmedia_file(self, file_path: Path) -> Dict[str, Any]:
        """Analyze a Directmedia file to understand its structure"""
        with open(file_path, 'rb') as f:
            data = f.read()

        analysis = {
            'file_size': len(data),
            'header': data[:256].hex(),
            'first_1k': data[:1024].hex(),
            'magic_bytes': [],
            'potential_lengths': [],
            'text_blocks': []
        }

        # Look for magic bytes/patterns
        # Directmedia often uses specific patterns
        patterns = [
            b'\x1b\x01',  # Common pattern we saw
            b'DKI',      # File extension in header
            b'TEXT',     # TEXT marker
            b'DATA',     # DATA marker
        ]

        for pattern in patterns:
            offset = 0
            while True:
                pos = data.find(pattern, offset)
                if pos == -1:
                    break
                analysis['magic_bytes'].append((pos, pattern.hex()))
                offset = pos + 1

        # Look for length-prefixed blocks
        i = 0
        while i < min(len(data), 2048):
            # Try different length field sizes
            if i + 2 <= len(data):
                length = struct.unpack('<H', data[i:i+2])[0]
                if 1 <= length <= 1024:  # Reasonable text block size
                    if i + 2 + length <= len(data):
                        block = data[i+2:i+2+length]
                        try:
                            text = block.decode('latin-1', errors='ignore')
                            if any(c.isalpha() for c in text):  # Contains letters
                                analysis['potential_lengths'].append({
                                    'offset': i,
                                    'length': length,
                                    'text_sample': text[:50]
                                })
                        except:
                            pass
            i += 1

        # Look for readable text blocks
        text_blocks = []
        current_block = bytearray()

        for byte in data:
            if 32 <= byte <= 126 or byte in [10, 13]:  # Printable ASCII + CRLF
                current_block.append(byte)
            else:
                if len(current_block) >= 10:  # Minimum readable block
                    try:
                        text = current_block.decode('latin-1', errors='ignore')
                        if any(c.isalpha() for c in text):
                            text_blocks.append({
                                'offset': len(data) - len(current_block),
                                'length': len(current_block),
                                'text': text[:100]
                            })
                    except:
                        pass
                current_block = bytearray()

        analysis['text_blocks'] = text_blocks[:10]  # First 10 blocks

        return analysis

    def extract_text_from_dki(self, dki_path: Path) -> str:
        """Extract readable text from a TEXT.DKI file"""
        analysis = self.analyze_directmedia_file(dki_path)

        extracted_text = []

        # Method 1: Use potential length-prefixed blocks
        for block_info in analysis['potential_lengths'][:50]:  # First 50 blocks
            text = block_info['text_sample']
            if len(text.strip()) > 5:  # Reasonable text length
                extracted_text.append(text)

        # Method 2: Use readable text blocks
        for block_info in analysis['text_blocks']:
            text = block_info['text']
            if len(text.strip()) > 5:
                extracted_text.append(text)

        # Method 3: Look for \x1b\x01 pattern we saw earlier
        with open(dki_path, 'rb') as f:
            data = f.read()

        offset = 0
        while True:
            pos = data.find(b'\x1b\x01', offset)
            if pos == -1:
                break

            # Extract length (next byte after \x1b\x01)
            if pos + 2 < len(data):
                length = data[pos + 2]
                if pos + 3 + length <= len(data):
                    text_block = data[pos + 3:pos + 3 + length]
                    try:
                        text = text_block.decode('latin-1', errors='ignore')
                        if text.strip():
                            extracted_text.append(text)
                    except:
                        pass

            offset = pos + 1

        # Combine and clean up
        full_text = '\n'.join(extracted_text)

        # Basic cleanup
        full_text = full_text.replace('\r\n', '\n').replace('\r', '\n')
        # Remove excessive whitespace
        lines = [line.strip() for line in full_text.split('\n') if line.strip()]
        full_text = '\n'.join(lines)

        return full_text

def main():
    decompressor = DirectmediaHuffmanDecompressor()

    # Test with Aristotle volume
    library_path = Path(r"L:\Multimedia Files\Written Word\Digitale Bibliothek")
    volume_path = library_path / "DB002" / "Data" / "TEXT.DKI"

    if volume_path.exists():
        print(f"Analyzing {volume_path}")
        analysis = decompressor.analyze_directmedia_file(volume_path)

        print(f"File size: {analysis['file_size']:,} bytes")
        print(f"Magic bytes found: {len(analysis['magic_bytes'])}")
        for offset, pattern in analysis['magic_bytes'][:5]:
            print(f"  0x{offset:08X}: {pattern}")

        print(f"Potential text blocks: {len(analysis['potential_lengths'])}")
        for i, block in enumerate(analysis['potential_lengths'][:3]):
            # Handle encoding issues
            sample = block['text_sample'][:40]
            safe_sample = sample.encode('cp1252', errors='replace').decode('cp1252', errors='replace')
            print(f"  Block {i+1}: {safe_sample}...")

        print(f"Readable text blocks: {len(analysis['text_blocks'])}")
        for i, block in enumerate(analysis['text_blocks'][:3]):
            sample = block['text'][:40]
            safe_sample = sample.encode('cp1252', errors='replace').decode('cp1252', errors='replace')
            print(f"  Text {i+1}: {safe_sample}...")

        # Extract text
        print("\nExtracting text...")
        extracted_text = decompressor.extract_text_from_dki(volume_path)

        print(f"Extracted {len(extracted_text):,} characters")
        print("\nFirst 1000 characters:")
        safe_text = extracted_text[:1000].encode('cp1252', errors='replace').decode('cp1252', errors='replace')
        print(safe_text)
        print("\n" + "="*50)

        # Look for Aristotle/Aristoteles
        aristotle_lines = [line for line in extracted_text.split('\n')
                          if 'aristotel' in line.lower() or 'metaphys' in line.lower()]

        if aristotle_lines:
            print("Found Aristotle references:")
            for line in aristotle_lines[:10]:
                print(f"  {line}")
        else:
            print("No Aristotle references found in extracted text")

        # Save extracted text
        output_path = library_path / "DB002" / "Data" / "TEXT_extracted_new.txt"
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(extracted_text)

        print(f"\nSaved extracted text to: {output_path}")

    else:
        print(f"File not found: {volume_path}")

if __name__ == "__main__":
    main()
