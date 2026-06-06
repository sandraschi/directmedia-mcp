"""Run the Directmedia MCP FastAPI app (web UI + MCP over HTTP)."""

from __future__ import annotations

import os

import uvicorn


def main() -> None:
    host = os.getenv("MCP_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_PORT", "10827"))
    uvicorn.run("directmedia_mcp.server:app", host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
