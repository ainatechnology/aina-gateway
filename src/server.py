"""aina-gateway - MCP Gateway for PixelMemory.

Exposes local Pixeltable memory/bookmarks via MCP Streamable HTTP transport.
Designed for use with Claude.ai Remote MCP integration.

Phase 2a: Bearer Token Authentication via ASGI middleware.
Phase 2c: IP Whitelist for Cloudflare Tunnel security.
Phase 3:  Schema v2 - row_id + full CRUD (30 tools).
"""

import asyncio

import uvicorn
import pixeltable as pxt
from mcp.server.fastmcp import FastMCP

from src.auth import BearerTokenMiddleware, IPWhitelistMiddleware
from src.config import GATEWAY_HOST, GATEWAY_PORT, API_KEY, IP_WHITELIST_ENABLED
from src.tools import register_tools

# Initialize Pixeltable (uses default ~/.pixeltable/ datastore)
pxt.init()

# Create MCP server (bind to 0.0.0.0 is handled by uvicorn, not FastMCP)
mcp = FastMCP(
    "PixelMemory Gateway",
    json_response=True,
    host=GATEWAY_HOST,
    port=GATEWAY_PORT,
    # Disable DNS rebinding protection for LAN access
    transport_security=None,
)

# Register all tools
register_tools(mcp)


def create_app():
    """Create the Starlette ASGI app with security middleware.

    Middleware execution order (outermost first):
    1. IPWhitelistMiddleware - blocks unknown IPs
    2. BearerTokenMiddleware - validates API key (Anthropic IPs exempt)
    3. FastMCP app - handles MCP protocol

    Note: Starlette applies middleware in reverse add order,
    so we add Bearer first, then IP whitelist.
    """
    # Get the raw Starlette app from FastMCP
    app = mcp.streamable_http_app()

    # Inner layer: Bearer Token auth (applied second)
    app.add_middleware(BearerTokenMiddleware, api_key=API_KEY)

    # Outer layer: IP whitelist (applied first, before auth)
    app.add_middleware(IPWhitelistMiddleware, enabled=IP_WHITELIST_ENABLED)

    return app


def main():
    """Start the gateway server."""
    auth_status = "🔒 AUTH ENABLED (Bearer Token, Anthropic IPs exempt)" if API_KEY else "⚠️  AUTH DISABLED (no API_KEY set)"
    ip_status = "🛡️  IP WHITELIST ACTIVE" if IP_WHITELIST_ENABLED else "⚠️  IP WHITELIST DISABLED"

    print(f"🚀 PixelMemory Gateway v2 starting on http://{GATEWAY_HOST}:{GATEWAY_PORT}/mcp")
    print(f"   {auth_status}")
    print(f"   {ip_status}")
    print(f"   Tools: 30 (5×CRUD + vault_read/write/list + get_schema)")
    print(f"   Transport: Streamable HTTP")
    print()

    app = create_app()

    config = uvicorn.Config(
        app,
        host=GATEWAY_HOST,
        port=GATEWAY_PORT,
        log_level="info",
    )
    server = uvicorn.Server(config)

    asyncio.run(server.serve())


if __name__ == "__main__":
    main()
