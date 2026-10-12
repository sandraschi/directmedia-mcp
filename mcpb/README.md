# directmedia-mcp (MCPB Bundle)

MCP server for accessing Directmedia Publishing Digitale Bibliothek - AWAITING REVERSE ENGINEERING

## Usage

Add to \claude_desktop_config.json\:
\\\json
{
  "mcpServers": {
    "directmedia-mcp": {
      "command": "uv",
      "args": ["run", "--directory", "\D:\Dev\repos", "python", "-m", "directmedia_mcp"],
      "env": { "PYTHONPATH": "\D:\Dev\repos/src" }
    }
  }
}
\\\

## Tools

- **list_volumes**: list_volumes

## Requirements

- Python 3.12+
- uv
