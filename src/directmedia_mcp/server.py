#!/usr/bin/env python3
"""
Directmedia MCP Server - Access to Directmedia Publishing Digitale Bibliothek
"""

import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List

from fastmcp import FastMCP
from pydantic import BaseModel, Field

from .library import DirectmediaLibrary
from .epub_converter import convert_volume_to_epub, batch_convert_library
from .logging_config import get_logger

logger = get_logger("directmedia_mcp")

# Initialize MCP server
mcp = FastMCP(
    "DirectmediaMCP",
    description="Access Directmedia Publishing Digitale Bibliothek (1990s German literature collection)",
    version="0.1.0"
)

# Global library instance
library: Optional[DirectmediaLibrary] = None


class VolumeInfo(BaseModel):
    """Information about a library volume"""
    id: str = Field(description="Volume ID (e.g., 'DB002')")
    title: str = Field(description="Full volume title")
    short_title: str = Field(description="Short title")
    path: str = Field(description="Filesystem path")
    size_mb: float = Field(description="Size in MB")
    has_text: bool = Field(description="Has text database")
    has_images: bool = Field(description="Has images")
    has_audio: bool = Field(description="Has audio files")


class SearchResult(BaseModel):
    """Search result"""
    volume_id: str = Field(description="Volume containing the result")
    title: str = Field(description="Entry title")
    content_preview: str = Field(description="Content preview")
    position: int = Field(description="Position in text")


def initialize_library(library_path: str) -> DirectmediaLibrary:
    """Initialize the Directmedia library"""
    global library
    if library is None:
        library = DirectmediaLibrary(library_path)
    return library


@mcp.tool()
async def list_volumes() -> List[Dict[str, Any]]:
    """
    List all available Directmedia volumes/bände

    Returns a list of all volumes in the Digitale Bibliothek collection
    with metadata about each volume.
    """
    if library is None:
        return [{"error": "Library not initialized. Use set_library_path first."}]

    try:
        volumes = library.list_volumes()
        return [vol.model_dump() for vol in volumes]
    except Exception as e:
        logger.error(f"Error listing volumes: {e}")
        return [{"error": f"Failed to list volumes: {str(e)}"}]


@mcp.tool()
async def get_volume_info(volume_id: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific volume

    Args:
        volume_id: Volume ID (e.g., 'DB002', 'DB003')
    """
    if library is None:
        return {"error": "Library not initialized. Use set_library_path first."}

    try:
        volume = library.get_volume_info(volume_id)
        if volume:
            return volume.model_dump()
        else:
            return {"error": f"Volume {volume_id} not found"}
    except Exception as e:
        logger.error(f"Error getting volume info for {volume_id}: {e}")
        return {"error": f"Failed to get volume info: {str(e)}"}


@mcp.tool()
async def search_text(query: str, volume_id: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
    """
    Search for text across volumes

    Args:
        query: Search query (supports basic text matching)
        volume_id: Optional volume ID to search in (searches all if None)
        limit: Maximum number of results to return
    """
    if library is None:
        return [{"error": "Library not initialized. Use set_library_path first."}]

    try:
        results = library.search_text(query, volume_id, limit)
        return [result.model_dump() for result in results]
    except Exception as e:
        logger.error(f"Error searching text '{query}': {e}")
        return [{"error": f"Failed to search: {str(e)}"}]


@mcp.tool()
async def get_text_content(volume_id: str, start_pos: int = 0, length: int = 1000) -> Dict[str, Any]:
    """
    Extract text content from a volume

    Args:
        volume_id: Volume ID to extract from
        start_pos: Starting position in the text database
        length: Number of characters to extract
    """
    if library is None:
        return {"error": "Library not initialized. Use set_library_path first."}

    try:
        content = library.get_text_content(volume_id, start_pos, length)
        return {
            "volume_id": volume_id,
            "start_position": start_pos,
            "length": length,
            "content": content
        }
    except Exception as e:
        logger.error(f"Error getting text content from {volume_id}: {e}")
        return {"error": f"Failed to get text content: {str(e)}"}


@mcp.tool()
async def get_navigation_tree(volume_id: str) -> Dict[str, Any]:
    """
    Get the navigation tree/structure for a volume

    Args:
        volume_id: Volume ID to get navigation for
    """
    if library is None:
        return {"error": "Library not initialized. Use set_library_path first."}

    try:
        tree = library.get_navigation_tree(volume_id)
        return tree
    except Exception as e:
        logger.error(f"Error getting navigation tree for {volume_id}: {e}")
        return {"error": f"Failed to get navigation tree: {str(e)}"}


@mcp.tool()
async def analyze_volume_structure(volume_id: str) -> Dict[str, Any]:
    """
    Analyze the file structure and format of a volume

    Args:
        volume_id: Volume ID to analyze
    """
    if library is None:
        return {"error": "Library not initialized. Use set_library_path first."}

    try:
        analysis = library.analyze_volume_structure(volume_id)
        return analysis
    except Exception as e:
        logger.error(f"Error analyzing volume {volume_id}: {e}")
        return {"error": f"Failed to analyze volume: {str(e)}"}


@mcp.tool()
async def set_library_path(path: str) -> Dict[str, Any]:
    """
    Set the path to the Digitale Bibliothek collection

    Args:
        path: Full path to the "Digitale Bibliothek" directory
    """
    try:
        if not os.path.exists(path):
            return {"error": f"Path does not exist: {path}"}

        # Check if it looks like a Directmedia library
        db_folders = [f for f in os.listdir(path) if f.startswith('DB') and os.path.isdir(os.path.join(path, f))]
        if not db_folders:
            return {"error": f"No Directmedia volumes (DBxxx folders) found in {path}"}

        global library
        library = initialize_library(path)

        return {
            "success": True,
            "path": path,
            "volumes_found": len(db_folders),
            "message": f"Library initialized with {len(db_folders)} volumes"
        }
    except Exception as e:
        logger.error(f"Error setting library path: {e}")
        return {"error": f"Failed to initialize library: {str(e)}"}


@mcp.tool()
async def convert_volume_to_epub_file(volume_id: str, output_dir: str) -> Dict[str, Any]:
    """
    Convert a Directmedia volume to EPUB format for e-book readers

    Args:
        volume_id: Volume identifier (e.g., 'DB002')
        output_dir: Directory where EPUB file will be created

    Returns:
        Conversion results with file path and status
    """
    try:
        if not library:
            return {"error": "Library not initialized. Use set_library_path first."}

        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)

        # Convert volume to EPUB
        result = convert_volume_to_epub(library.base_path, volume_id, output_dir)

        if result.get("epub_files_created", 0) > 0:
            return {
                "success": True,
                "volume_id": volume_id,
                "epub_files_created": result["epub_files_created"],
                "output_dir": result["output_dir"],
                "message": f"Successfully converted volume {volume_id} to EPUB format"
            }
        else:
            return {
                "success": False,
                "volume_id": volume_id,
                "errors": result.get("errors", ["Unknown error"]),
                "message": f"Failed to convert volume {volume_id}"
            }

    except Exception as e:
        logger.error(f"Error converting volume {volume_id} to EPUB: {e}")
        return {"error": f"EPUB conversion failed: {str(e)}"}


@mcp.tool()
async def batch_convert_to_epub(output_dir: str, volume_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Convert multiple Directmedia volumes to EPUB format

    Args:
        output_dir: Directory where EPUB files will be created
        volume_ids: Optional list of specific volume IDs to convert (converts all if None)

    Returns:
        Batch conversion results
    """
    try:
        if not library:
            return {"error": "Library not initialized. Use set_library_path first."}

        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)

        # Perform batch conversion
        result = batch_convert_library(library.base_path, output_dir, volume_ids)

        return {
            "success": True,
            "volumes_processed": result["total_volumes_processed"],
            "epub_files_created": result["epub_files_created"],
            "volumes_converted": result["volumes_converted"],
            "output_dir": result["output_dir"],
            "errors": result.get("errors", []),
            "message": f"Batch conversion complete: {result['epub_files_created']} EPUB files created"
        }

    except Exception as e:
        logger.error(f"Error in batch EPUB conversion: {e}")
        return {"error": f"Batch conversion failed: {str(e)}"}


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Directmedia MCP Server")
    parser.add_argument("--library-path", help="Path to Digitale Bibliothek directory")
    parser.add_argument("--log-level", default="INFO", help="Logging level")

    args = parser.parse_args()

    # Set log level
    import logging
    logging.getLogger().setLevel(getattr(logging, args.log_level.upper()))

    # Initialize library if path provided
    if args.library_path:
        global library
        library = initialize_library(args.library_path)
        logger.info(f"Initialized library with {len(library.list_volumes())} volumes")

    # Run MCP server
    mcp.run()


if __name__ == "__main__":
    main()

