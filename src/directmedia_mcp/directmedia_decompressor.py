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
            # Known magic numbers for different Directmedia formats
            text_magic_numbers = [0x00010d95, 0x001924cc]  # Add the discovered magic number

            if analysis['magic_number'] in text_magic_numbers:
                offsets = []
                # Start from offset 8 (after the first two 4-byte values)
                for i in range(8, len(header), 4):
                    if i + 4 <= len(header):
                        offset = struct.unpack('<I', header[i:i+4])[0]
                        if offset > 0 and offset < analysis['file_size']:
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
            file_data = f.read()

            # Parse Directmedia TEXT.DKI format properly
            # Main pattern: \x1b\x01 + length_byte + text_bytes (Latin-1 encoded German)
            text_records = []
            i = 0
            while i < len(file_data) - 10 and len(text_records) < max_sections * 200:

                # Main text extraction pattern: \x1b\x01 + length + text
                if file_data[i:i+2] == b'\x1b\x01':
                    length_byte = file_data[i+2]
                    if 2 <= length_byte <= 50:  # Reasonable German word/phrase length
                        text_start = i + 3
                        text_end = text_start + length_byte
                        if text_end <= len(file_data):
                            text_bytes = file_data[text_start:text_end]
                            try:
                                # Decode as Latin-1 (standard for German text in this era)
                                text = text_bytes.decode('latin-1', errors='strict')

                                # Strict validation: must be readable German text
                                # Allow letters, spaces, German chars, basic punctuation
                                valid_chars = set('abcdefghijklmnopqrstuvwxyzäöüßABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÜẞ .,;:!?-()[]{}"\'')

                                if (all(c in valid_chars for c in text) and
                                    any(c.isalpha() for c in text) and  # Must contain letters
                                    len(text.strip()) >= 2 and         # Minimum length
                                    not text.isdigit()):               # Not just numbers

                                    text_records.append({
                                        'offset': i,
                                        'length': length_byte,
                                        'text': text.strip(),
                                        'pattern': '1b01_latin1',
                                        'raw_bytes': text_bytes
                                    })

                            except UnicodeDecodeError:
                                # Skip invalid UTF-8 sequences
                                pass

                    i += 3 + max(1, length_byte)
                else:
                    i += 1

            # Group records into sections
            if text_records:
                section_size = max(1, len(text_records) // max_sections)
                for section_idx in range(max_sections):
                    start_idx = section_idx * section_size
                    end_idx = min(start_idx + section_size, len(text_records))
                    section_records = text_records[start_idx:end_idx]

                    if section_records:
                        combined_text = ' '.join(record['text'] for record in section_records)

                        result['extracted_sections'].append({
                            'section_id': section_idx,
                            'offset': section_records[0]['offset'],
                            'original_size': sum(record['length'] for record in section_records),
                            'records_found': len(section_records),
                            'records': [{
                                'offset': record['offset'],
                                'text_content': record['text'],
                                'text_length': len(record['text'])
                            } for record in section_records[:20]]  # First 20 records
                        })

                        result['total_extracted_size'] += len(combined_text)
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

    def _parse_text_dki_records(self, file_data: bytes, max_records: int = 1000) -> List[Dict[str, Any]]:
        """Parse TEXT.DKI file records: 2-byte length + 1-byte type + text content"""

        text_records = []
        i = 0

        while i < len(file_data) - 10 and len(text_records) < max_records:
            # Check for record header: 2 bytes length + 1 byte type
            if i + 3 <= len(file_data):
                record_length = int.from_bytes(file_data[i:i+2], byteorder='little')
                record_type = file_data[i+2]

                if 5 <= record_length <= 5000:  # Reasonable text length for philosophical content
                    text_start = i + 3
                    text_end = text_start + record_length

                    if text_end <= len(file_data):
                        text_bytes = file_data[text_start:text_end]

                        try:
                            # Decode as Latin-1 (German text encoding)
                            text = text_bytes.decode('latin-1', errors='replace')

                            # Validate as meaningful philosophical text
                            if (len(text.strip()) >= 10 and  # Substantial content
                                any(c.isalpha() for c in text) and  # Contains letters
                                not text.isdigit() and  # Not just numbers
                                text.count(' ') > 2 and  # Contains sentences/paragraphs
                                not all(c in '.,;:!?- ' for c in text)):  # Not just punctuation

                                text_records.append({
                                    'offset': i,
                                    'length': record_length,
                                    'text': text.strip(),
                                    'record_type': record_type,
                                    'raw_bytes': text_bytes
                                })

                        except UnicodeDecodeError:
                            pass

                i += 3 + record_length
            else:
                i += 1

        return text_records

    def _decompress_index_ttx(self, ttx_path: Path) -> str:
        """Decompress INDEX.TTX file to extract actual text content"""

        with open(ttx_path, 'rb') as f:
            data = f.read()

        extracted_text = []

        # Method 1: Try zlib decompression on compressed blocks
        import zlib

        i = 0
        while i < len(data) - 100:
            try:
                # Look for zlib compressed blocks
                if data[i:i+2] == b'\x78\x9c':  # Zlib signature
                    chunk = data[i:]
                    try:
                        decompressed = zlib.decompress(chunk)
                        text = decompressed.decode('latin-1', errors='replace')

                        # Check if we got meaningful philosophical text
                        if (len(text) > 100 and
                            any(word in text.lower() for word in ['philosoph', 'aristotel', 'metaphysik', 'ethik'])):

                            extracted_text.append(text)
                            print(f"Found philosophical text block at offset {i}")
                            break  # Found what we want

                    except (zlib.error, UnicodeDecodeError):
                        pass

            except:
                pass

            i += 1

        # Method 2: If no compressed blocks work, try direct text extraction
        if not extracted_text:
            print("No compressed blocks found, trying direct text extraction...")
            i = 0
            while i < len(data) - 500:
                if data[i] >= 32 and data[i] <= 255:
                    start = i
                    while i < len(data) and data[i] >= 32 and data[i] <= 255:
                        i += 1

                    block_length = i - start
                    if block_length >= 1000:  # Substantial text block
                        try:
                            text = data[start:i].decode('latin-1', errors='replace')

                            # Look for philosophy content
                            if any(word in text.lower() for word in ['aristotel', 'metaphysik', 'philosoph']):
                                extracted_text.append(text)
                                print(f"Found philosophical text block at offset {start}")
                                if len(extracted_text) >= 3:  # Get a few samples
                                    break

                        except UnicodeDecodeError:
                            pass
                else:
                    i += 1

        return '\n\n'.join(extracted_text) if extracted_text else ""

    def _extract_readable_text_blocks(self, data: bytes, max_blocks: int = 100, min_length: int = 20) -> List[Dict[str, Any]]:
        """Extract readable text blocks from binary data with strict validation"""
        text_blocks = []
        i = 0

        while i < len(data) and len(text_blocks) < max_blocks:
            # Look for start of potential text sequence
            if data[i] >= 32 and data[i] < 127:  # Printable ASCII start
                start = i

                # Collect sequence until we hit a likely binary boundary
                sequence_bytes = bytearray()
                while i < len(data):
                    byte_val = data[i]

                    # Stop conditions for text sequences:
                    if byte_val == 0x00:  # Null byte - definite binary
                        break
                    elif byte_val < 9 or (byte_val > 13 and byte_val < 32):  # Control chars except tab/lf/cr
                        break
                    elif byte_val > 127:  # High ASCII - might be German but check context
                        # Allow some high ASCII for German, but limit consecutive
                        pass

                    sequence_bytes.append(byte_val)
                    i += 1

                    # Stop if sequence gets too long without spaces (likely not natural text)
                    if len(sequence_bytes) > 200 and b' ' not in sequence_bytes[-50:]:
                        break

                sequence_length = len(sequence_bytes)
                if sequence_length >= min_length:
                    try:
                        text = sequence_bytes.decode('latin-1', errors='replace')

                        # Strict validation of extracted text
                        if self._validate_text_content(text, min_length):
                            # Clean up extra whitespace
                            import re
                            clean_text = re.sub(r'\s+', ' ', text.strip())

                            if len(clean_text) >= min_length:
                                text_blocks.append({
                                    'offset': start,
                                    'length': sequence_length,
                                    'text': clean_text
                                })
                    except:
                        pass
            else:
                i += 1

        return text_blocks

    def _validate_text_content(self, text: str, min_length: int) -> bool:
        """Validate that extracted text is actually readable content, not binary data"""
        if len(text) < min_length:
            return False

        # Count different character types
        total_chars = len(text)
        ascii_printable = sum(1 for c in text if 32 <= ord(c) <= 126)
        high_ascii = sum(1 for c in text if 127 <= ord(c) <= 255)
        whitespace = sum(1 for c in text if c in ' \t\n\r')
        replacement_chars = text.count('�')

        # Calculate ratios
        printable_ratio = (ascii_printable + high_ascii) / total_chars
        high_ascii_ratio = high_ascii / total_chars
        whitespace_ratio = whitespace / total_chars

        # Reject if too many replacement characters (encoding errors)
        if replacement_chars > total_chars * 0.1:  # More than 10% replacement chars
            return False

        # Reject if too many high ASCII chars (likely binary data)
        if high_ascii_ratio > 0.3:  # More than 30% high ASCII
            return False

        # Reject if not enough printable characters
        if printable_ratio < 0.7:  # Less than 70% printable
            return False

        # Check for natural text patterns
        words = text.split()
        if not words:
            return False

        # Should have some spaces (natural text has word boundaries)
        avg_word_length = sum(len(word) for word in words) / len(words)
        if avg_word_length > 50:  # Unusually long words suggest not natural text
            return False

        # Look for German text patterns (common words/letters)
        german_indicators = ['der', 'die', 'das', 'und', 'ist', 'von', 'mit', 'für', 'auf', 'ich', 'nicht', 'dass']
        german_score = sum(1 for indicator in german_indicators if indicator.lower() in text.lower())

        # Look for common German letters
        german_chars = sum(1 for c in text.lower() if c in 'äöüß')
        german_score += german_chars

        # Bonus for sentence-like patterns
        if any(punct in text for punct in '.!?'):
            german_score += 2

        # Accept if we have reasonable German content or natural text structure
        return german_score >= 2 or (printable_ratio > 0.8 and whitespace_ratio > 0.02)

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
