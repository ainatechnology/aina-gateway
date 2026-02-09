# Changelog

All notable changes to pixelmemory-gateway.

## [0.3.0] - 2026-02-07

### Added
- **IP Whitelist Middleware** — blocks all IPs except Anthropic (`160.79.104.0/21`), LAN, and loopback
- **Cloudflare Tunnel support** — public HTTPS access via Named Tunnel
- **LaunchAgent templates** — auto-start gateway and tunnel on macOS login
- `IP_WHITELIST_ENABLED` and `ALLOWED_IPS` configuration options
- `deploy/` directory with LaunchAgent plist templates

### Changed
- Renamed project from `aina-gateway` to `pixelmemory-gateway`
- Updated `pyproject.toml` with new name and version
- Expanded README for open source release (English)
- Updated `.env.example` with all configuration options

## [0.2.0] - 2026-02-06

### Added
- **Bearer Token Authentication** — `BearerTokenMiddleware` with `secrets.compare_digest` for timing-attack resistance
- `API_KEY` configuration via `.env`
- `transport_security=None` for LAN access from Claude Desktop

## [0.1.0] - 2026-02-06

### Added
- Initial release with 7 MCP tools (memory_search, memory_list, memory_add, bookmark_search, bookmark_list, bookmark_add, get_schema)
- FastMCP server with Streamable HTTP transport
- Pixeltable backend with `memory.memories` and `memory.bookmarks` tables
- Async-safe design using `asyncio.to_thread()` for blocking Pixeltable calls
- Integration tests
