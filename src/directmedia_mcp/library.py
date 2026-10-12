"""
Directmedia Library - Access to Directmedia Publishing Digitale Bibliothek
"""

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .dki_text import DkiFormatError, TextDki, find_text_dki
from .dki_tree import load_toc
from .logging_config import get_logger

logger = get_logger("directmedia_mcp.library")

_CAPTION_PREFIX = re.compile(r"^(DB\s+)?Digitale Bibliothek(\s+(Band|Sonderband|Spezial))?\s*\d*\s*:\s*", re.IGNORECASE)


def _fix_cyrillic(text: str) -> str:
    """DIGIBIB.TXT is read as Latin-1; Russian volumes (e.g. DB006) are really CP1251."""
    high = sum(1 for ch in text if "À" <= ch <= "ÿ")
    letters = sum(1 for ch in text if ch.isalpha())
    if letters and high / letters > 0.5:
        try:
            return text.encode("latin-1").decode("cp1251")
        except UnicodeError:
            return text
    return text


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
                        if line.startswith("Caption=") and title == f"Band {volume_id}":  # first section only
                            title = line.split("=", 1)[1].strip()
                        elif line.startswith("ShortTitle=") and short_title == volume_id:
                            short_title = line.split("=", 1)[1].strip()
            except Exception as e:
                logger.warning(f"Error reading DIGIBIB.TXT for {volume_id}: {e}")

        title = _fix_cyrillic(title)
        if short_title == volume_id:
            # Most later volumes have no ShortTitle: derive it from "Digitale Bibliothek Band 19: <title>".
            short_title = _CAPTION_PREFIX.sub("", title).strip() or volume_id

        # Calculate size and check for content types
        total_size = 0
        has_text = False
        has_images = False
        has_audio = False

        try:
            for root, _dirs, files in os.walk(volume_path):
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

    def _text_dki_path(self, volume_id: str) -> Path | None:
        return find_text_dki(self.library_path / volume_id)

    def _search_volume_text(self, volume_id: str, query: str, limit: int) -> list[SearchResult]:
        """Case-insensitive substring search over every decoded record of one volume.

        Linear scan (no use of the INDEX.* files yet): fine for one volume, slow across the
        largest ones (DB125 has 600k records).
        """
        path = self._text_dki_path(volume_id)
        if path is None or limit <= 0:
            return []
        results: list[SearchResult] = []
        needle = query.lower()
        with TextDki(path) as dki:
            for k in range(dki.count):
                try:
                    rec = dki.decode_record(k)
                except DkiFormatError as exc:
                    logger.warning("Skipping undecodable record %s/%d: %s", volume_id, k, exc)
                    continue
                hay = rec.text.lower()
                found = hay.find(needle)
                if found < 0:
                    continue
                start = max(0, found - 60)
                end = min(len(rec.text), found + len(query) + 60)
                preview = " ".join(rec.text[start:end].split())
                results.append(
                    SearchResult(
                        volume_id=volume_id,
                        title=rec.source or f"Record {k}",
                        content_preview=f"...{preview}...",
                        position=k,
                    )
                )
                if len(results) >= limit:
                    break
        return results

    def get_text_content(self, volume_id: str, start_pos: int = 0, length: int = 1000) -> dict[str, Any]:
        """Decode text starting at record (page) start_pos, up to length characters.

        Whole records are returned, so the first record is always included even if longer
        than length. Continue with start_pos=next_pos.
        """
        path = self._text_dki_path(volume_id)
        if path is None:
            return {"error": f"Volume {volume_id} not found or has no TEXT.DKI"}
        try:
            with TextDki(path) as dki:
                if not 0 <= start_pos < dki.count:
                    return {"error": f"start_pos {start_pos} out of range 0..{dki.count - 1} for {volume_id}"}
                parts: list[str] = []
                sources: list[str] = []
                pages: list[int] = []
                total = 0
                k = start_pos
                while k < dki.count and (not parts or total < length):
                    rec = dki.decode_record(k)
                    parts.append(rec.text)
                    total += len(rec.text) + 2
                    pages.extend(rec.pages)
                    if rec.source and rec.source not in sources:
                        sources.append(rec.source)
                    k += 1
                content = "\n\n".join(parts)
                return {
                    "volume_id": volume_id,
                    "start_position": start_pos,
                    "next_pos": k if k < dki.count else None,
                    "total_records": dki.count,
                    "records_returned": k - start_pos,
                    "length": len(content),
                    "content": content,
                    "sources": sources,
                    "print_pages": pages,
                    "format": f"{dki.family}v{dki.version}",
                }
        except (DkiFormatError, OSError) as e:
            logger.exception("Error reading text from %s", volume_id)
            return {"error": f"Failed to read text: {e!s}"}

    def get_full_text(self, volume_id: str) -> str:
        """Decode every record of a volume into one string (records separated by blank lines)."""
        path = self._text_dki_path(volume_id)
        if path is None:
            raise ValueError(f"Volume {volume_id} has no TEXT.DKI")
        parts = []
        with TextDki(path) as dki:
            for k in range(dki.count):
                try:
                    parts.append(dki.decode_record(k).text)
                except DkiFormatError as exc:
                    logger.warning("Skipping undecodable record %s/%d: %s", volume_id, k, exc)
        return "\n\n".join(parts)

    def get_navigation_tree(self, volume_id: str, parent: int | None = None) -> dict[str, Any]:
        """Table of contents: children of TOC entry `parent` (None = top level), each with its start record."""
        volume_dir = self.library_path / volume_id
        if not volume_dir.is_dir():
            return {"error": f"Volume {volume_id} not found"}
        entries = load_toc(volume_dir)
        if not entries:
            return {"error": f"Volume {volume_id} has no TREE.DKI"}
        if parent is not None and not 0 <= parent < len(entries):
            return {"error": f"TOC entry {parent} out of range 0..{len(entries) - 1}"}
        children = [e for e in entries if e.parent == parent]
        return {
            "volume_id": volume_id,
            "total_entries": len(entries),
            "has_record_map": entries[0].record is not None,
            "parent": parent,
            "entries": [
                {"index": e.index, "title": e.title, "record": e.record, "child_count": e.child_count} for e in children
            ],
        }

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
            "TEXT.DKI": "Haupttextdatenbank (tokenisierter Volltext, unkomprimiert)",
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
