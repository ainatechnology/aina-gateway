"""aina-gateway - MCP Gateway for PixelMemory.

Exposes local Pixeltable memory/bookmarks via MCP Streamable HTTP transport.
Designed for use with Claude.ai Remote MCP integration.
"""

import pixeltable as pxt
from mcp.server.fastmcp import FastMCP

from src.config import GATEWAY_HOST, GATEWAY_PORT
from src.tools import register_tools

# Initialize Pixeltable (uses default ~/.pixeltable/ datastore)
pxt.init()

# Create MCP server
mcp = FastMCP(
    "PixelMemory Gateway",
    json_response=True,
    host=GATEWAY_HOST,
    port=GATEWAY_PORT,
)

# Register all tools
register_tools(mcp)


def main():
    """Start the gateway server."""
    print(f"🚀 PixelMemory Gateway starting on http://{GATEWAY_HOST}:{GATEWAY_PORT}/mcp")
    print(f"   Tools: memory_search, memory_list, memory_add, bookmark_search, bookmark_list, bookmark_add, get_schema")
    print(f"   Transport: Streamable HTTP")
    print()
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
