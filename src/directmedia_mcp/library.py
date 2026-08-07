"""
Directmedia Library - Access to Directmedia Publishing Digitale Bibliothek
"""

import os
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .directmedia_decompressor import DirectmediaDecompressor
from .logging_config import get_logger

logger = get_logger("directmedia_mcp.library")


@dataclass
class VolumeInfo:
    """Information about a library volume"""

    id: str
    title: str
    short_title: str
    path: str
    size_mb: float
    has_text: bool
    has_images: bool
    has_audio: bool


@dataclass
class SearchResult:
    """Search result"""

    volume_id: str
    title: str
    content_preview: str
    position: int


class DirectmediaLibrary:
    """Access to Directmedia Publishing Digitale Bibliothek"""

    def __init__(self, library_path: str):
        self.library_path = Path(library_path)
        if not self.library_path.exists():
            raise ValueError(f"Library path does not exist: {library_path}")

        self._volumes_cache: list[VolumeInfo] | None = None
        logger.info(f"Initialized Directmedia library at {library_path}")

    def list_volumes(self) -> list[VolumeInfo]:
        """List all available volumes"""
        if self._volumes_cache is not None:
            return self._volumes_cache

        volumes = []
        for item in self.library_path.iterdir():
            if item.is_dir() and item.name.startswith("DB"):
                try:
                    volume_info = self._get_volume_info(item.name)
                    if volume_info:
                        volumes.append(volume_info)
                except Exception as e:
                    logger.warning(f"Error reading volume {item.name}: {e}")

        # Sort by volume number
        volumes.sort(key=lambda v: v.id)
        self._volumes_cache = volumes
        return volumes

    def _get_volume_info(self, volume_id: str) -> VolumeInfo | None:
        """Get information about a specific volume"""

        volume_path = self.library_path / volume_id
        if not volume_path.exists():
            return None

        # Read DIGIBIB.TXT for metadata
        digibib_path = volume_path / "Data" / "DIGIBIB.TXT"
        title = f"Band {volume_id}"
        short_title = volume_id

        if digibib_path.exists():
            try:
                with open(digibib_path, encoding="latin-1") as f:
                    content = f.read()
                    for line in content.split("\n"):
                        if line.startswith("Caption="):
                            title = line.split("=", 1)[1].strip()
                        elif line.startswith("ShortTitle="):
                            short_title = line.split("=", 1)[1].strip()
            except Exception as e:
                logger.warning(f"Error reading DIGIBIB.TXT for {volume_id}: {e}")

        # Calculate size and check for content types
        total_size = 0
        has_text = False
        has_images = False
        has_audio = False

        try:
            for root, dirs, files in os.walk(volume_path):
                for file in files:
                    filepath = Path(root) / file
                    stat_info = filepath.stat()
                    total_size += stat_info.st_size

                    if file.upper() == "TEXT.DKI":
                        has_text = True
                    elif file.lower().endswith((".bmp", ".jpg", ".jpeg", ".png")):
                        has_images = True
                    elif file.lower().endswith((".wav", ".mp3")):
                        has_audio = True
        except Exception as e:
            logger.warning(f"Error calculating size for {volume_id}: {e}")

        return VolumeInfo(
            id=volume_id,
            title=title,
            short_title=short_title,
            path=str(volume_path),
            size_mb=round(total_size / 1024 / 1024, 1),
            has_text=has_text,
            has_images=has_images,
            has_audio=has_audio,
        )

    def get_volume_info(self, volume_id: str) -> VolumeInfo | None:
        """Get detailed information about a volume"""
        volumes = self.list_volumes()
        for volume in volumes:
            if volume.id == volume_id:
                return volume
        return None

    def search_text(self, query: str, volume_id: str | None = None, limit: int = 20) -> list[SearchResult]:
        """Search for text in volumes"""
        results = []

        volumes_to_search = []
        if volume_id:
            volume = self.get_volume_info(volume_id)
            if volume:
                volumes_to_search = [volume]
        else:
            volumes_to_search = self.list_volumes()

        for volume in volumes_to_search:
            if volume.has_text:
                try:
                    volume_results = self._search_volume_text(volume.id, query, limit // len(volumes_to_search) + 1)
                    results.extend(volume_results)
                except Exception as e:
                    logger.warning(f"Error searching volume {volume.id}: {e}")

        # Sort by relevance and limit results
        results.sort(key=lambda r: r.position)
        return results[:limit]

    def _search_volume_text(self, volume_id: str, query: str, limit: int) -> list[SearchResult]:
        """Search text in a specific volume"""
        # For now, implement basic text extraction and search
        # This is a simplified implementation - real implementation would use INDEX files

        results = []
        text_content = self.get_text_content(volume_id, 0, 50000)  # First 50KB

        if "content" in text_content:
            content = text_content["content"].lower()
            query_lower = query.lower()

            pos = 0
            while pos < len(content) and len(results) < limit:
                found_pos = content.find(query_lower, pos)
                if found_pos == -1:
                    break

                # Extract preview around the match
                start = max(0, found_pos - 50)
                end = min(len(content), found_pos + len(query) + 50)
                preview = content[start:end]

                results.append(
                    SearchResult(
                        volume_id=volume_id,
                        title=f"Match in {volume_id}",
                        content_preview="..." + preview + "...",
                        position=found_pos,
                    )
                )

                pos = found_pos + 1

        return results

    def get_text_content(self, volume_id: str, start_pos: int = 0, length: int = 1000) -> dict[str, Any]:
        """Extract text content from a volume"""

        volume = self.get_volume_info(volume_id)
        if not volume or not volume.has_text:
            return {"error": f"Volume {volume_id} not found or has no text"}

        # Try different possible paths for TEXT.DKI
        possible_paths = [
            self.library_path / volume_id / "Data" / "TEXT.DKI",
            self.library_path / volume_id / "DATA" / "TEXT.DKI",
            self.library_path / volume_id / "Text.dki",
            self.library_path / volume_id / "TEXT.DKI",
        ]

        text_dki_path = None
        for path in possible_paths:
            if path.exists():
                text_dki_path = path
                break

        if text_dki_path is None:
            return {"error": f"TEXT.DKI not found for volume {volume_id}. Tried: {[str(p) for p in possible_paths]}"}

        try:
            # Use the proper decompressor to extract text content
            decompressor = DirectmediaDecompressor()
            result = decompressor.extract_text_content(text_dki_path, max_sections=10)

            # Combine all extracted text from sections
            all_text_parts = []
            total_records = 0

            for section in result["extracted_sections"]:
                if "records" in section:
                    for record in section["records"]:
                        if record.get("text_content"):
                            all_text_parts.append(record["text_content"])
                            total_records += 1

            # Combine all text
            full_text = "\n\n".join(all_text_parts)

            # Apply start_pos and length limits if specified
            if start_pos > 0:
                full_text = full_text[start_pos:]
            if len(full_text) > length:
                full_text = full_text[:length]

            return {
                "volume_id": volume_id,
                "start_position": start_pos,
                "length": len(full_text.encode("utf-8")),
                "content": full_text,
                "sections_processed": len(result["extracted_sections"]),
                "total_records_found": total_records,
                "extraction_errors": len(result.get("errors", [])),
            }

        except Exception as e:
            logger.error(f"Error reading text from {volume_id}: {e}")
            return {"error": f"Failed to read text: {e!s}"}

    def get_navigation_tree(self, volume_id: str) -> dict[str, Any]:
        """Get navigation tree (table of contents) for a volume"""

        volume = self.get_volume_info(volume_id)
        if not volume:
            return {"error": f"Volume {volume_id} not found"}

        tree_dki_path = self.library_path / volume_id / "Data" / "TREE.DKI"

        tree_info = {"volume_id": volume_id, "tree_files": {}, "structure": "unknown", "table_of_contents": []}

        # Parse TREE.DKI for table of contents
        if tree_dki_path.exists():
            try:
                toc_entries = self._parse_tree_dki(tree_dki_path)
                tree_info["structure"] = "hierarchical_text"
                tree_info["table_of_contents"] = toc_entries
                tree_info["tree_files"]["TREE.DKI"] = {
                    "size": tree_dki_path.stat().st_size,
                    "entries": len(toc_entries),
                }
            except Exception as e:
                logger.warning(f"Error parsing TREE.DKI: {e}")
                tree_info["error"] = str(e)

        # Analyze TREE.DKA (structural information)
        tree_dka_path = self.library_path / volume_id / "Data" / "TREE.DKA"
        if tree_dka_path.exists():
            try:
                with open(tree_dka_path, "rb") as f:
                    header = f.read(64)
                    if len(header) >= 8:
                        num_entries = struct.unpack("<I", header[:4])[0]
                        data_offset = struct.unpack("<I", header[4:8])[0]
                        tree_info["tree_files"]["TREE.DKA"] = {
                            "size": tree_dka_path.stat().st_size,
                            "num_entries": num_entries,
                            "data_offset": data_offset,
                        }
            except Exception as e:
                logger.warning(f"Error analyzing TREE.DKA: {e}")

        return tree_info

    def _parse_tree_dki(self, tree_dki_path: Path) -> list[dict[str, Any]]:
        """Parse TREE.DKI file to extract hierarchical table of contents"""

        with open(tree_dki_path, "rb") as f:
            data = f.read()

        toc_entries = []
        current_line = []
        i = 0

        while i < len(data):
            if data[i] == 0x0D and i + 1 < len(data) and data[i + 1] == 0x0A:  # CRLF
                # End of line
                if current_line:
                    line_bytes = bytes(current_line)
                    try:
                        line_text = line_bytes.decode("latin-1", errors="replace").rstrip()
                        if line_text.strip():  # Skip empty lines
                            # Calculate indentation level (number of leading spaces)
                            indent_level = len(line_text) - len(line_text.lstrip(" "))
                            clean_text = line_text.strip()

                            toc_entries.append(
                                {
                                    "text": clean_text,
                                    "level": indent_level // 2,  # Each level uses 2 spaces
                                    "offset": len(toc_entries),  # Sequential index
                                }
                            )
                    except UnicodeDecodeError:
                        pass
                    current_line = []
                i += 2
            elif data[i] >= 32 and data[i] <= 255:  # Printable character
                current_line.append(data[i])
                i += 1
            else:
                # Skip control characters
                i += 1

        return toc_entries

    def analyze_volume_structure(self, volume_id: str) -> dict[str, Any]:
        """Analyze the file structure of a volume"""

        volume_path = self.library_path / volume_id
        if not volume_path.exists():
            return {"error": f"Volume {volume_id} not found"}

        analysis = {
            "volume_id": volume_id,
            "data_files": {},
            "image_files": {},
            "audio_files": {},
            "other_files": {},
            "total_size_mb": 0,
        }

        data_path = volume_path / "Data"
        if data_path.exists():
            for file_path in data_path.iterdir():
                if file_path.is_file():
                    stat_info = file_path.stat()
                    size = stat_info.st_size
                    analysis["total_size_mb"] += size / 1024 / 1024

                    ext = file_path.suffix.upper()
                    filename = file_path.name.upper()

                    if ext in [".DKI", ".DKA"]:
                        analysis["data_files"][file_path.name] = {
                            "size": size,
                            "description": self._get_file_description(file_path.name),
                        }
                    elif ext in [".HTX", ".PLX", ".SHX", ".SWX", ".TTX", ".WLX"]:
                        index_type = self._get_index_type(file_path.name)
                        analysis["data_files"][file_path.name] = {
                            "size": size,
                            "type": "index",
                            "index_type": index_type,
                        }
                    elif filename.startswith("LINKS."):
                        analysis["data_files"][file_path.name] = {"size": size, "type": "links"}
                    elif filename == "SIGEL.DAT":
                        analysis["data_files"][file_path.name] = {
                            "size": size,
                            "type": "sigel",
                            "description": "Abkürzungsverzeichnis",
                        }
                    else:
                        analysis["data_files"][file_path.name] = {"size": size}

        # Check for images and audio in subdirectories
        for subdir in ["IMAGES", "Images", "images", "WAVS", "Wavs"]:
            sub_path = volume_path / subdir
            if sub_path.exists():
                file_count = len(list(sub_path.glob("*")))
                if subdir.upper() in ["IMAGES", "IMAGES"]:
                    analysis["image_files"][subdir] = file_count
                elif subdir.upper() in ["WAVS", "WAVS"]:
                    analysis["audio_files"][subdir] = file_count

        analysis["total_size_mb"] = round(analysis["total_size_mb"], 1)
        return analysis

    def _get_file_description(self, filename: str) -> str:
        """Get description for known file types"""
        descriptions = {
            "TEXT.DKI": "Haupttextdatenbank (komprimierter Volltext)",
            "TREE.DKA": "Navigationsbaum (Inhaltsverzeichnis)",
            "TREE.DKI": "Navigationsbaum (Strukturdaten)",
        }
        return descriptions.get(filename, "Unbekannt")

    def _get_index_type(self, filename: str) -> str:
        """Get index type description"""
        index_types = {
            "INDEX.HTX": "Hypertext Index",
            "INDEX.PLX": "Plaintext Index",
            "INDEX.SHX": "Short Index",
            "INDEX.SWX": "Search Word Index",
            "INDEX.TTX": "Title Index",
            "INDEX.WLX": "Word List Index",
        }
        return index_types.get(filename, "Unbekannt")
