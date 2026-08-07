#!/usr/bin/env python3
"""
Directmedia MCP Server - Access to Directmedia Publishing Digitale Bibliothek
"""

import json
import os
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastmcp import FastMCP
from fastmcp.server import create_proxy
from pydantic import BaseModel, Field

from .epub_converter import batch_convert_library, convert_volume_to_epub
from .library import DirectmediaLibrary
from .logging_config import get_logger

logger = get_logger("directmedia_mcp")

# Initialize MCP server
mcp = FastMCP(
    "DirectmediaMCP",
    instructions="Access Directmedia Publishing Digitale Bibliothek (1990s German literature collection)",
    version="0.1.0",
)

_bridge_proxies = []
bridge_urls = os.getenv("MCP_BRIDGE_URLS", "")
if bridge_urls:
    for url in bridge_urls.split(","):
        url = url.strip()
        if url:
            try:
                mcp.add_provider(create_proxy(url))
                _bridge_proxies.append(url)
            except Exception as exc:
                logger.debug("Skipping bridge URL %s: %s", url, exc)

# Global library instance
library: DirectmediaLibrary | None = None


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
    """Initialize or re-initialize the Directmedia library at the given path."""
    global library
    library = DirectmediaLibrary(library_path)
    return library


def serialize_tool_result(result: Any) -> Any:
    """Return plain JSON data from a FastMCP ToolResult for the HTTP bridge."""
    payload: Any = None
    structured = getattr(result, "structured_content", None)
    if structured is not None:
        payload = structured
    elif hasattr(result, "model_dump"):
        data = result.model_dump(by_alias=False)
        if data.get("structured_content") is not None:
            payload = data["structured_content"]
        else:
            for chunk in data.get("content") or []:
                if chunk.get("type") == "text" and chunk.get("text"):
                    try:
                        payload = json.loads(chunk["text"])
                    except json.JSONDecodeError:
                        payload = chunk["text"]
                    break
    if payload is None:
        return result
    # FastMCP wraps bare list tool returns as {"result": [...]}
    if isinstance(payload, dict) and set(payload.keys()) == {"result"}:
        return payload["result"]
    return payload


@mcp.tool()
async def list_volumes() -> list[dict[str, Any]]:
    """
    List all available Directmedia volumes/bände

    Returns a list of all volumes in the Digitale Bibliothek collection
    with metadata about each volume.
    """
    if library is None:
        return [{"error": "Library not initialized. Use set_library_path first."}]

    try:
        volumes = library.list_volumes()
        # Convert VolumeInfo objects to dictionaries
        result = []
        for vol in volumes:
            result.append(
                {
                    "id": vol.id,
                    "title": vol.title,
                    "short_title": vol.short_title,
                    "path": vol.path,
                    "size_mb": vol.size_mb,
                    "has_text": vol.has_text,
                    "has_images": vol.has_images,
                    "has_audio": vol.has_audio,
                }
            )
        return result
    except Exception as e:
        logger.error(f"Error listing volumes: {e}")
        return [{"error": f"Failed to list volumes: {e!s}"}]


@mcp.tool()
async def get_volume_info(volume_id: str) -> dict[str, Any]:
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
            # Convert VolumeInfo object to dictionary
            return {
                "id": volume.id,
                "title": volume.title,
                "short_title": volume.short_title,
                "path": volume.path,
                "size_mb": volume.size_mb,
                "has_text": volume.has_text,
                "has_images": volume.has_images,
                "has_audio": volume.has_audio,
            }
        else:
            return {"error": f"Volume {volume_id} not found"}
    except Exception as e:
        logger.error(f"Error getting volume info for {volume_id}: {e}")
        return {"error": f"Failed to get volume info: {e!s}"}


@mcp.tool()
async def search_text(query: str, volume_id: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
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
        # Convert SearchResult dataclasses to dictionaries
        from dataclasses import asdict

        return [asdict(result) for result in results]
    except Exception as e:
        logger.error(f"Error searching text '{query}': {e}")
        return [{"error": f"Failed to search: {e!s}"}]


@mcp.tool()
async def get_text_content(volume_id: str, start_pos: int = 0, length: int = 1000) -> dict[str, Any]:
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
            "content": content,
        }
    except Exception as e:
        logger.error(f"Error getting text content from {volume_id}: {e}")
        return {"error": f"Failed to get text content: {e!s}"}


@mcp.tool()
async def get_navigation_tree(volume_id: str) -> dict[str, Any]:
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
        return {"error": f"Failed to get navigation tree: {e!s}"}


@mcp.tool()
async def analyze_volume_structure(volume_id: str) -> dict[str, Any]:
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
        return {"error": f"Failed to analyze volume: {e!s}"}


@mcp.tool()
async def set_library_path(path: str) -> dict[str, Any]:
    """
    Set the path to the Digitale Bibliothek collection

    Args:
        path: Full path to the "Digitale Bibliothek" directory
    """
    try:
        if not os.path.exists(path):
            return {"error": f"Path does not exist: {path}"}

        # Check if it looks like a Directmedia library
        db_folders = [f for f in os.listdir(path) if f.startswith("DB") and os.path.isdir(os.path.join(path, f))]
        if not db_folders:
            return {"error": f"No Directmedia volumes (DBxxx folders) found in {path}"}

        global library
        library = initialize_library(path)

        return {
            "success": True,
            "path": path,
            "volumes_found": len(db_folders),
            "message": f"Library initialized with {len(db_folders)} volumes",
        }
    except Exception as e:
        logger.error(f"Error setting library path: {e}")
        return {"error": f"Failed to initialize library: {e!s}"}


@mcp.tool()
async def convert_volume_to_epub_file(volume_id: str, output_dir: str) -> dict[str, Any]:
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
        result = convert_volume_to_epub(str(library.library_path), volume_id, output_dir)

        if result.get("epub_files_created", 0) > 0:
            return {
                "success": True,
                "volume_id": volume_id,
                "epub_files_created": result["epub_files_created"],
                "output_dir": result["output_dir"],
                "message": f"Successfully converted volume {volume_id} to EPUB format",
            }
        else:
            return {
                "success": False,
                "volume_id": volume_id,
                "errors": result.get("errors", ["Unknown error"]),
                "message": f"Failed to convert volume {volume_id}",
            }

    except Exception as e:
        logger.error(f"Error converting volume {volume_id} to EPUB: {e}")
        return {"error": f"EPUB conversion failed: {e!s}"}


@mcp.tool()
async def batch_convert_to_epub(output_dir: str, volume_ids: list[str] | None = None) -> dict[str, Any]:
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
        result = batch_convert_library(str(library.library_path), output_dir, volume_ids)

        return {
            "success": True,
            "volumes_processed": result["total_volumes_processed"],
            "epub_files_created": result["epub_files_created"],
            "volumes_converted": result["volumes_converted"],
            "output_dir": result["output_dir"],
            "errors": result.get("errors", []),
            "message": f"Batch conversion complete: {result['epub_files_created']} EPUB files created",
        }

    except Exception as e:
        logger.error(f"Error in batch EPUB conversion: {e}")
        return {"error": f"Batch conversion failed: {e!s}"}


_mcp_http = mcp.http_app(path="/")
app = FastAPI(title="Directmedia MCP API", version="0.1.0", lifespan=_mcp_http.lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "healthy",
        "service": "directmedia-mcp",
        "library_initialized": library is not None,
    }


@app.get("/api/v1/status")
async def api_status() -> dict[str, Any]:
    volume_count = 0
    library_path: str | None = None
    if library is not None:
        library_path = str(library.library_path)
        try:
            volume_count = len(library.list_volumes())
        except Exception as exc:
            logger.warning("Could not count volumes: %s", exc)

    return {
        "status": "healthy",
        "service": "directmedia-mcp",
        "library_initialized": library is not None,
        "library_path": library_path,
        "volume_count": volume_count,
        "tools": [
            "set_library_path",
            "list_volumes",
            "get_volume_info",
            "search_text",
            "get_text_content",
            "get_navigation_tree",
            "analyze_volume_structure",
            "convert_volume_to_epub_file",
            "batch_convert_to_epub",
        ],
    }


class LibraryPathRequest(BaseModel):
    path: str = Field(description="Full path to the Digitale Bibliothek root directory")


@app.post("/api/v1/library/path")
async def api_set_library_path(body: LibraryPathRequest) -> dict[str, Any]:
    """Set and initialize the Digitale Bibliothek library path."""
    path = body.path.strip()
    if not path:
        raise HTTPException(status_code=400, detail="Library path is required")
    try:
        logger.info("Setting library path via REST: %s", path)
        result = await mcp.call_tool("set_library_path", {"path": path})
        payload = serialize_tool_result(result)
        if isinstance(payload, dict) and payload.get("error"):
            raise HTTPException(status_code=400, detail=str(payload["error"]))
        if not isinstance(payload, dict):
            raise HTTPException(status_code=500, detail="Unexpected tool response")
        return payload
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to set library path")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/v1/call")
async def api_call_tool(request: dict[str, Any]) -> Any:
    """Bridge for web_sota to invoke MCP tools over HTTP."""
    name = request.get("name")
    arguments = request.get("arguments") or {}
    if not name:
        raise HTTPException(status_code=400, detail="Tool name is required")
    try:
        logger.info("Web bridge calling tool %s", name)
        result = await mcp.call_tool(name, arguments)
        return serialize_tool_result(result)
    except Exception as exc:
        logger.exception("Tool call failed: %s", name)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.on_event("startup")
async def startup_init_library() -> None:
    """Optionally initialize library from DIRECTMEDIA_LIBRARY_PATH on boot."""
    env_path = os.getenv("DIRECTMEDIA_LIBRARY_PATH", "").strip()
    if not env_path:
        return
    try:
        result = await mcp.call_tool("set_library_path", {"path": env_path})
        payload = serialize_tool_result(result)
        if isinstance(payload, dict) and payload.get("success"):
            logger.info("Auto-initialized library from DIRECTMEDIA_LIBRARY_PATH: %s", env_path)
        elif isinstance(payload, dict) and payload.get("error"):
            logger.warning("DIRECTMEDIA_LIBRARY_PATH invalid: %s", payload["error"])
    except Exception as exc:
        logger.warning("Could not auto-initialize library: %s", exc)


app.mount("/mcp", _mcp_http)


def main():
    """Main entry point with unified transport handling (FastMCP 2.14.4+)."""
    import logging as log_module

    from .transport import create_argument_parser, run_server

    # Create parser with custom arguments
    parser = create_argument_parser(server_name="DirectmediaMCP")
    parser.add_argument("--library-path", help="Path to Digitale Bibliothek directory")
    parser.add_argument("--log-level", default="INFO", help="Logging level")

    args = parser.parse_args()

    # Set log level
    log_module.getLogger().setLevel(getattr(log_module, args.log_level.upper()))

    # Initialize library if path provided
    if args.library_path:
        global library
        library = initialize_library(args.library_path)
        logger.info(f"Initialized library with {len(library.list_volumes())} volumes")

    # Run with unified transport
    run_server(mcp, server_name="directmedia-mcp")


if __name__ == "__main__":
    main()
