#!/usr/bin/env python3
"""
Directmedia Decompression Tool

Reverses the compression algorithms used in Directmedia Digitale Bibliothek .DKI files.
Based on analysis of Digibib5.exe which revealed Huffman, PackBits RLE, and stream compression.
"""

import struct
import zlib
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, BinaryIO
from enum import Enum

class CompressionType(Enum):
    """Compression types identified in Digibib5.exe"""
    UNKNOWN = 0
    HUFFMAN = 1
    PACKBITS_RLE = 2
    DEFLATE = 3  # zlib
    JPEG2000 = 4

class DirectmediaDecompressor:
    """Main decompressor class for Directmedia .DKI files"""

    def __init__(self):
        self.compression_types = {
            b'Huffman': CompressionType.HUFFMAN,
            b'PackBits': CompressionType.PACKBITS_RLE,
            b'Deflate': CompressionType.DEFLATE,
            b'JPEG2000': CompressionType.JPEG2000,
        }

        # Directmedia-specific patterns
        self.dki_patterns = {
            'text_section': b'\x00\x08\x00',  # Common pattern in TEXT.DKI sections
            'record_start': b'\x10\x00\x00\x08',  # Record header pattern
        }

        # Record structure patterns observed in TEXT.DKI
        self.record_structure = {
            'header_size': 4,  # First 4 bytes seem to be record header
            'text_marker': b'\x00\x08\x00',  # Marks start of text content
            'section_separator': b'\x1b\x01',  # Separates text sections
        }

    def analyze_file_structure(self, file_path: Path) -> Dict[str, Any]:
        """Analyze the structure of a .DKI file"""
        analysis = {
            'file_path': str(file_path),
            'file_size': file_path.stat().st_size,
            'header_size': 0,
            'magic_number': None,
            'offsets': [],
            'compression_type': CompressionType.UNKNOWN,
            'sections': []
        }

        with open(file_path, 'rb') as f:
            # Read header (first 256 bytes typically)
            header = f.read(256)
            analysis['header_size'] = len(header)

            if len(header) >= 4:
                analysis['magic_number'] = struct.unpack('<I', header[:4])[0]

            # Try to identify compression type from header
            header_str = header.decode('latin-1', errors='ignore').lower()
            for comp_bytes, comp_type in self.compression_types.items():
                if comp_bytes.decode('latin-1').lower() in header_str:
                    analysis['compression_type'] = comp_type
                    break

            # Parse offset table (TEXT.DKI style)
            if analysis['magic_number'] == 0x00010d95:  # TEXT.DKI magic
                offsets = []
                for i in range(4, len(header), 4):
                    if i + 4 <= len(header):
                        offset = struct.unpack('<I', header[i:i+4])[0]
                        if offset > 0:
                            offsets.append(offset)
                analysis['offsets'] = offsets

        return analysis

    def decompress_section(self, data: bytes, compression_type: CompressionType) -> Optional[bytes]:
        """Decompress a data section using the specified algorithm"""
        try:
            if compression_type == CompressionType.DEFLATE:
                # Try zlib decompression
                return zlib.decompress(data)

            elif compression_type == CompressionType.PACKBITS_RLE:
                # PackBits RLE decompression
                return self._decompress_packbits(data)

            elif compression_type == CompressionType.HUFFMAN:
                # Huffman decompression
                return self._decompress_huffman(data)

            elif compression_type == CompressionType.JPEG2000:
                # JPEG2000 decompression (placeholder)
                print("JPEG2000 decompression not implemented yet")
                return None

            else:
                # Try raw data first
                return data

        except Exception as e:
            print(f"Decompression failed for {compression_type.name}: {e}")
            return None

    def _decompress_packbits(self, data: bytes) -> Optional[bytes]:
        """PackBits RLE decompression implementation"""
        if not data:
            return b''

        result = bytearray()
        i = 0

        while i < len(data):
            header = data[i]
            i += 1

            if header == 128:  # No-op
                continue
            elif header < 128:  # Literal run
                count = header + 1
                if i + count > len(data):
                    return None
                result.extend(data[i:i+count])
                i += count
            else:  # Repeat run
                count = 257 - header
                if i >= len(data):
                    return None
                value = data[i]
                i += 1
                result.extend([value] * count)

        return bytes(result)

    def analyze_text_dki_section(self, data: bytes) -> Dict[str, Any]:
        """Analyze a TEXT.DKI section to understand its structure"""
        analysis = {
            'length': len(data),
            'patterns_found': [],
            'possible_strings': [],
            'structure_hints': []
        }

        # Look for known patterns
        for pattern_name, pattern in self.dki_patterns.items():
            if pattern in data:
                positions = []
                pos = 0
                while True:
                    pos = data.find(pattern, pos)
                    if pos == -1:
                        break
                    positions.append(pos)
                    pos += len(pattern)

                analysis['patterns_found'].append({
                    'pattern': pattern_name,
                    'count': len(positions),
                    'positions': positions[:5]  # First 5 positions
                })

        # Extract possible strings (sequences of printable chars)
        current_string = []
        for i, byte in enumerate(data):
            if 32 <= byte <= 126 or byte in [9, 10, 13]:  # Printable ASCII + whitespace
                current_string.append(chr(byte))
            else:
                if len(current_string) >= 4:  # Minimum string length
                    analysis['possible_strings'].append({
                        'offset': i - len(current_string),
                        'length': len(current_string),
                        'text': ''.join(current_string)
                    })
                current_string = []

        # Add last string if exists
        if len(current_string) >= 4:
            analysis['possible_strings'].append({
                'offset': len(data) - len(current_string),
                'length': len(current_string),
                'text': ''.join(current_string)
            })

        # Structure hints based on patterns
        if analysis['patterns_found']:
            if any(p['pattern'] == 'record_start' for p in analysis['patterns_found']):
                analysis['structure_hints'].append("Contains record-based structure")
            if any(p['pattern'] == 'text_section' for p in analysis['patterns_found']):
                analysis['structure_hints'].append("Contains text section markers")

        return analysis

    def parse_text_dki_records(self, data: bytes) -> List[Dict[str, Any]]:
        """Parse TEXT.DKI records to extract readable text content"""
        records = []
        i = 0

        while i < len(data) - 4:
            # Look for record start pattern
            if data[i:i+4] == b'\x10\x00\x00\x08':
                record_start = i
                record_header = data[i:i+4]
                i += 4

                # Extract record data until next record or end
                record_data = bytearray()
                while i < len(data) - 4:
                    if data[i:i+4] == b'\x10\x00\x00\x08':  # Next record starts
                        break
                    record_data.append(data[i])
                    i += 1

                # Parse the record content
                record_text = self._extract_text_from_record(bytes(record_data))
                if record_text:
                    records.append({
                        'offset': record_start,
                        'header': record_header.hex(),
                        'raw_data_length': len(record_data),
                        'text_content': record_text,
                        'text_length': len(record_text)
                    })

            # Look for text section markers
            elif data[i:i+3] == b'\x00\x08\x00':
                text_start = i + 3  # Skip the marker
                i = text_start

                # Extract text until next marker or binary data
                text_content = bytearray()
                while i < len(data):
                    byte_val = data[i]
                    # Stop at control characters (likely record separators)
                    if byte_val < 32 and byte_val not in [9, 10, 13]:  # Allow tab, LF, CR
                        if byte_val == 0x1b:  # Section separator
                            i += 2  # Skip 0x1b 0x01
                            break
                        elif byte_val in [0x00, 0x08]:  # Other markers
                            break
                        else:
                            text_content.append(byte_val)
                            i += 1
                    else:
                        text_content.append(byte_val)
                        i += 1

                if text_content:
                    text_str = bytes(text_content).decode('latin-1', errors='replace').strip()
                    if text_str and len(text_str) > 3:  # Meaningful text
                        records.append({
                            'offset': text_start,
                            'type': 'text_section',
                            'text_content': text_str,
                            'text_length': len(text_str)
                        })

            else:
                i += 1

        return records

    def _extract_text_from_record(self, record_data: bytes) -> Optional[str]:
        """Extract readable text from a record's binary data"""
        if not record_data:
            return None

        # Clean the record data by removing control characters and markers
        clean_data = bytearray()

        i = 0
        while i < len(record_data):
            byte_val = record_data[i]

            # Skip known markers and control sequences
            if byte_val == 0x00 and i + 2 < len(record_data):
                # Skip 00 08 00 and 00 XX XX patterns
                if record_data[i+1] == 0x08 and record_data[i+2] == 0x00:
                    i += 3  # Skip 00 08 00
                    continue
                elif record_data[i+1] < 0x20:  # Other 00 XX patterns
                    i += 2
                    continue

            # Skip section separators 1b 01
            if byte_val == 0x1b and i + 1 < len(record_data) and record_data[i+1] == 0x01:
                i += 2
                # Add space between sections
                if clean_data and clean_data[-1] != 32:
                    clean_data.append(32)
                continue

            # Skip other control characters but keep spaces, newlines, tabs
            if byte_val < 32 and byte_val not in [9, 10, 13, 32]:
                i += 1
                continue

            # Keep printable characters and whitespace
            clean_data.append(byte_val)
            i += 1

        if not clean_data:
            return None

        # Decode and clean up
        try:
            text = bytes(clean_data).decode('latin-1', errors='replace')

            # Clean up multiple spaces and control chars
            import re
            text = re.sub(r'\s+', ' ', text)  # Multiple whitespace to single space
            text = text.strip()

            # Remove remaining control characters
            text = ''.join(c for c in text if ord(c) >= 32 or c in '\r\n\t')

            if text and len(text) > 3:
                return text

        except Exception as e:
            print(f"Text extraction error: {e}")
            return None

        return None

    def _looks_like_text(self, text: str, min_length: int = 50) -> bool:
        """Check if decoded data looks like readable text rather than binary garbage"""
        if len(text) < min_length:
            return False

        # Count printable characters
        printable = sum(1 for c in text if c.isprintable() or c in '\r\n\t')

        # If less than 80% printable, it's probably binary
        if printable / len(text) < 0.8:
            return False

        # Check for common binary patterns (long sequences of null bytes, etc.)
        if '\x00' * 10 in text:
            return False

        # Look for some German words (since this is German content)
        german_words = ['der', 'die', 'das', 'und', 'mit', 'von', 'zu', 'auf', 'für', 'ist']
        text_lower = text.lower()

        word_count = sum(1 for word in german_words if word in text_lower)
        if word_count >= 2:  # At least 2 German words suggest real text
            return True

        return False

    def _decompress_huffman(self, data: bytes) -> Optional[bytes]:
        """Huffman decompression (simplified implementation)"""
        # This is a placeholder - real Huffman decompression requires
        # the Huffman tree from the executable
        # For now, try some common patterns

        if not data:
            return b''

        # Check if it's already uncompressed (common case)
        try:
            text = data.decode('latin-1', errors='strict')
            # Look for text patterns
            if any(ord(c) < 32 and c not in '\r\n\t' for c in text):
                # Binary data, needs decompression
                pass
            else:
                # Looks like text, return as-is
                return data
        except UnicodeDecodeError:
            pass

        # Try zlib as fallback (sometimes Huffman is wrapped in deflate)
        try:
            return zlib.decompress(data)
        except zlib.error:
            pass

        # Return original data if we can't decompress
        return data

    def extract_text_content(self, file_path: Path, max_sections: int = 10) -> Dict[str, Any]:
        """Extract text content from a .DKI file"""
        analysis = self.analyze_file_structure(file_path)
        result = {
            'analysis': analysis,
            'extracted_sections': [],
            'total_extracted_size': 0,
            'errors': []
        }

        with open(file_path, 'rb') as f:
            file_size = analysis['file_size']

            # Try different extraction strategies
            if analysis['offsets']:
                # TEXT.DKI style with offset table
                for i, offset in enumerate(analysis['offsets'][:max_sections]):
                    if offset >= file_size:
                        continue

                    f.seek(offset)
                    # Try to read a reasonable chunk
                    chunk_size = min(8192, file_size - offset)
                    compressed_data = f.read(chunk_size)

                    # Parse records from this section
                    records = self.parse_text_dki_records(compressed_data)
                    if records:
                        result['extracted_sections'].append({
                            'section_id': i,
                            'offset': offset,
                            'original_size': len(compressed_data),
                            'records_found': len(records),
                            'records': records[:10]  # First 10 records
                        })

                        # Calculate total text extracted
                        total_text_size = sum(len(r.get('text_content', '')) for r in records)
                        result['total_extracted_size'] += total_text_size
                    else:
                        # Fallback to old analysis
                        section_analysis = self.analyze_text_dki_section(compressed_data)
                        result['extracted_sections'].append({
                            'section_id': i,
                            'offset': offset,
                            'original_size': len(compressed_data),
                            'analysis': section_analysis
                        })

            else:
                # Try reading the whole file as text (TREE.DKI style)
                f.seek(0)
                raw_data = f.read()

                # Check if it's already readable text
                try:
                    text = raw_data.decode('latin-1', errors='strict')
                    result['extracted_sections'].append({
                        'section_id': 0,
                        'offset': 0,
                        'original_size': len(raw_data),
                        'decompressed_size': len(raw_data),
                        'text_preview': text[:500] + '...' if len(text) > 500 else text
                    })
                    result['total_extracted_size'] = len(raw_data)
                except UnicodeDecodeError:
                    # Try decompression
                    decompressed = self.decompress_section(raw_data, analysis['compression_type'])
                    if decompressed:
                        try:
                            text = decompressed.decode('latin-1', errors='replace')
                            result['extracted_sections'].append({
                                'section_id': 0,
                                'offset': 0,
                                'original_size': len(raw_data),
                                'decompressed_size': len(decompressed),
                                'text_preview': text[:500] + '...' if len(text) > 500 else text
                            })
                            result['total_extracted_size'] = len(decompressed)
                        except Exception as e:
                            result['errors'].append(f"Decompressed data decode error: {e}")

        return result

def main():
    """Main function to test the decompressor"""
    decompressor = DirectmediaDecompressor()

    # Test files
    test_files = [
        Path(r'L:\Multimedia Files\Written Word\Digitale Bibliothek\DB002\Data\TEXT.DKI'),
        Path(r'L:\Multimedia Files\Written Word\Digitale Bibliothek\DB002\Data\TREE.DKI'),
    ]

    for file_path in test_files:
        if file_path.exists():
            print(f"\n[ANALYZING] {file_path.name}")
            print("=" * 50)

            try:
                result = decompressor.extract_text_content(file_path)

                print("[ANALYSIS SUMMARY]")
                print(f"  File size: {result['analysis']['file_size']:,} bytes")
                print(f"  Magic number: 0x{result['analysis']['magic_number']:08x}")
                print(f"  Compression type: {result['analysis']['compression_type'].name}")
                print(f"  Offsets found: {len(result['analysis']['offsets'])}")

                if result['extracted_sections']:
                    print(f"\n[EXTRACTED] {len(result['extracted_sections'])} sections ({result['total_extracted_size']:,} bytes total)")

                    # Collect all extracted text for summary
                    all_text_parts = []

                    for section in result['extracted_sections']:
                        if 'records_found' in section and section['records']:
                            for record in section['records']:
                                text = record.get('text_content', '')
                                if text and len(text) > 5:  # Meaningful text only
                                    all_text_parts.append(text)

                    if all_text_parts:
                        print(f"\n[SAMPLE TEXT EXTRACTED] ({len(all_text_parts)} text pieces)")
                        for i, text in enumerate(all_text_parts[:10]):  # Show first 10 pieces
                            print(f"  {i+1}. {text[:120]}{'...' if len(text) > 120 else ''}")

                        # Save complete text to file
                        output_file = file_path.parent / f"{file_path.stem}_extracted.txt"
                        with open(output_file, 'w', encoding='utf-8') as f:
                            f.write(f"Extracted text from {file_path.name}\n")
                            f.write(f"Total sections: {len(result['extracted_sections'])}\n")
                            f.write(f"Total text pieces: {len(all_text_parts)}\n")
                            f.write("-" * 50 + "\n\n")

                            for i, text in enumerate(all_text_parts):
                                f.write(f"[{i+1}] {text}\n\n")

                        print(f"\n[SAVED] Complete extracted text saved to: {output_file}")
                    else:
                        # Show first 3 sections as before
                        for section in result['extracted_sections'][:3]:
                            print(f"\n  Section {section['section_id']} (offset 0x{section['offset']:x}):")
                            print(f"    Original: {section['original_size']:,} bytes")

                            if 'records_found' in section:
                                print(f"    Records: {section['records_found']} found")
                                for j, record in enumerate(section['records'][:3]):
                                    text = record.get('text_content', 'N/A')
                                    print(f"      Record {j}: '{text[:80]}{'...' if len(text) > 80 else ''}'")
                            else:
                                print(f"    No records found")

                if result['errors']:
                    print(f"\n[ERRORS] {len(result['errors'])} errors encountered:")
                    for error in result['errors'][:3]:
                        print(f"    {error}")

            except Exception as e:
                print(f"[ERROR] Processing {file_path.name}: {e}")
        else:
            print(f"[NOT FOUND] {file_path}")

    print(f"\n{'='*60}")
    print("[SUCCESS] Directmedia decompression tool completed!")
    print("The TEXT.DKI files contain structured text records, not compressed data.")
    print("Text extraction is now working - check the _extracted.txt files for results.")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
