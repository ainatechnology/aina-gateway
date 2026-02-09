# pixelmemory-gateway

**Give Claude a persistent, local-first memory — across conversations, projects, and devices.**

An MCP server that connects Claude.ai and Claude Desktop to a local [Pixeltable](https://github.com/pixeltable/pixeltable) database via [Streamable HTTP](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports#streamable-http). Store memories and bookmarks on your own machine. No cloud. No vendor lock-in. Full control.

```
Claude.ai ──HTTPS──► Cloudflare Tunnel ──► pixelmemory-gateway ──► Pixeltable (local)
Claude Desktop VM ──────── LAN ──────────► pixelmemory-gateway ──► Pixeltable (local)
```

## The Problem

Claude doesn't remember you. Every conversation starts from zero. Anthropic's built-in memory is limited to the current project and updates sporadically. If you work across multiple projects or switch between Claude.ai and Claude Desktop, context is lost.

## The Solution

pixelmemory-gateway runs a local MCP server that gives Claude read/write access to a Pixeltable database on your machine. Memories persist across conversations, projects, and clients — because they live on *your* hardware.

### Key Features

- **7 MCP tools** — search, list, and add memories and bookmarks, plus schema introspection
- **Local-first** — all data stays on your machine (Pixeltable + PostgreSQL)
- **Dual access** — Claude.ai via Cloudflare Tunnel, Claude Desktop via LAN
- **Security stack** — IP whitelist (Anthropic IPs only) + Bearer token auth
- **Auto-start** — macOS LaunchAgent with crash recovery
- **Async-safe** — synchronous Pixeltable calls offloaded to threads

---

## Quick Start

### Prerequisites

- Python 3.13 (not 3.14 — see [known issues](#known-issues))
- [Pixeltable](https://github.com/pixeltable/pixeltable) installed and initialized
- A Pixeltable database with `memory.memories` and `memory.bookmarks` tables

### Installation

```bash
git clone https://github.com/AINA-Technology/pixelmemory-gateway.git
cd pixelmemory-gateway

python3.13 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

cp .env.example .env
# Edit .env to your needs
```

### Start the Server

```bash
python -m src.server
```

The gateway starts on `http://0.0.0.0:8008/mcp`.

### Verify

```bash
curl -s http://127.0.0.1:8008/mcp -X POST \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"test","version":"0.1"}}}'
```

---

## Configuration

All settings via `.env`:

```bash
# Server
GATEWAY_HOST=0.0.0.0
GATEWAY_PORT=8008

# Authentication (empty = authless mode)
API_KEY=

# IP Whitelist (blocks all IPs except Anthropic + LAN)
IP_WHITELIST_ENABLED=true

# Additional allowed IPs (comma-separated CIDRs)
# ALLOWED_IPS=203.0.113.0/24,198.51.100.42
```

---

## Architecture

### Security Stack

Requests pass through two middleware layers before reaching the MCP server:

```
Request → IPWhitelistMiddleware → BearerTokenMiddleware → FastMCP
```

| Access Path | Authentication | Protection |
|---|---|---|
| **Claude.ai** via Cloudflare Tunnel | Authless | IP whitelist (Anthropic IPs only) |
| **Claude Desktop** via LAN | Bearer Token | API key + private network |
| **localhost** | Authless or Bearer | Loopback interface |

### IP Whitelist

The gateway only accepts requests from:

- **Anthropic**: `160.79.104.0/21` + legacy IPs
- **Private networks**: `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`
- **Loopback**: `127.0.0.0/8`, `::1/128`
- **Custom**: via `ALLOWED_IPS` in `.env`

When behind a Cloudflare Tunnel, the middleware reads `CF-Connecting-IP` to get the real client IP.

### Why Not Cloudflare WAF?

Cloudflare's Web Application Firewall with custom IP rules requires a paid plan. Application-level filtering gives us the same result at zero cost.

---

## MCP Tools

| Tool | Description | Key Parameters |
|---|---|---|
| `memory_search` | Search memories by content substring | `query`, `limit` |
| `memory_list` | List recent memories | `limit`, `memory_type`, `project` |
| `memory_add` | Store a new memory | `content`, `memory_type`, `projects`, `tags` |
| `bookmark_search` | Search bookmarks by title/URL/description | `query`, `limit` |
| `bookmark_list` | List recent bookmarks | `limit`, `bookmark_type` |
| `bookmark_add` | Store a new bookmark | `url`, `title`, `description`, `tags` |
| `get_schema` | Inspect table structure | `table_name` |

---

## Connecting Claude.ai (via Cloudflare Tunnel)

### 1. Install cloudflared

```bash
brew install cloudflared
cloudflared tunnel login
```

### 2. Create a Named Tunnel

```bash
cloudflared tunnel create pixelmemory
cloudflared tunnel route dns pixelmemory mcp.yourdomain.com
```

### 3. Configure the Tunnel

Create `~/.cloudflared/config.yml`:

```yaml
tunnel: <your-tunnel-id>
credentials-file: /Users/<you>/.cloudflared/<your-tunnel-id>.json

ingress:
  - hostname: mcp.yourdomain.com
    service: http://localhost:8008
  - service: http_status:404
```

### 4. Start the Tunnel

```bash
cloudflared tunnel run pixelmemory
```

### 5. Add to Claude.ai

Go to Claude.ai → Settings → Connectors → "Add MCP Server":
- **URL**: `https://mcp.yourdomain.com/mcp`
- **Authentication**: None

The IP whitelist ensures only Anthropic's servers can reach your gateway.

---

## Connecting Claude Desktop (via LAN)

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "pixelmemory": {
      "command": "npx",
      "args": [
        "mcp-remote",
        "http://<gateway-ip>:8008/mcp",
        "--header",
        "Authorization: Bearer <your-api-key>"
      ]
    }
  }
}
```

---

## Auto-Start (macOS)

Create `~/Library/LaunchAgents/org.pixelmemory.gateway.plist` to start the gateway at login with automatic crash recovery. See [the docs](docs/) for the full LaunchAgent configuration.

```bash
launchctl load ~/Library/LaunchAgents/org.pixelmemory.gateway.plist
```

---

## Pixeltable Schema

The gateway expects two tables in the `memory` directory:

### `memory.memories`

| Column | Type | Description |
|---|---|---|
| `content` | String | The memory content |
| `memory_type` | String | Category (e.g., `fact`, `decision`, `status`) |
| `projects` | JSON | Associated projects |
| `tags` | JSON | Tags for organization |
| `source` | String | Origin of the memory |
| `created_at` | String | ISO timestamp |
| `updated_at` | String | ISO timestamp |

### `memory.bookmarks`

| Column | Type | Description |
|---|---|---|
| `url` | String | Bookmark URL |
| `title` | String | Page title |
| `description` | String | Description |
| `bookmark_type` | String | Category |
| `projects` | JSON | Associated projects |
| `tags` | JSON | Tags |
| `source` | String | Origin |
| `language` | String | Content language |
| `created_at` | String | ISO timestamp |
| `updated_at` | String | ISO timestamp |

---

## Technical Design Decisions

### Why Pixeltable?

Pixeltable provides a local PostgreSQL-backed database with built-in embedding support (via `sentence-transformers`). This means semantic search comes for free — no external vector database needed.

### Why `asyncio.to_thread()`?

FastMCP runs in an async event loop. Pixeltable operations are synchronous and blocking. Every tool call is offloaded to a thread to keep the event loop responsive:

```python
@mcp.tool()
async def memory_search(query: str, limit: int = 10) -> str:
    return await asyncio.to_thread(_do_memory_search, query, limit)
```

### Why Not OAuth?

Claude.ai Custom Connectors support either OAuth or authless — no simple Bearer token. Since implementing a full OAuth flow adds significant complexity for a single-user gateway, we chose authless mode protected by IP filtering instead.

---

## Known Issues

- **Python 3.14**: The `anyio` library (MCP SDK dependency) has a bug causing `TypeError: cannot create weak reference to 'NoneType' object`. Use Python 3.13.
- **Port conflicts**: After an unclean shutdown, the port may remain occupied. Fix with `kill -9 $(lsof -ti:8008)`.

---

## Project Structure

```
pixelmemory-gateway/
├── src/
│   ├── __init__.py      # Package marker
│   ├── auth.py          # IPWhitelistMiddleware + BearerTokenMiddleware
│   ├── config.py        # Configuration from .env
│   ├── server.py        # FastMCP server setup + startup
│   └── tools.py         # All 7 MCP tool implementations
├── tests/
│   └── test_gateway.py  # Integration tests
├── .env.example         # Configuration template
├── pyproject.toml       # Dependencies + metadata
├── LICENSE
└── README.md
```

---

## Dependencies

```
mcp >= 1.8.0              # MCP Python SDK (FastMCP + Streamable HTTP)
pixeltable >= 0.2.0       # Database backend
uvicorn >= 0.30.0         # ASGI server
python-dotenv >= 1.0.0    # .env configuration
sentence-transformers     # For Pixeltable embedding index
```

---

## License

MIT License — see [LICENSE](LICENSE).

---

## About

Built by [AINA Technology GmbH](https://aina-mcp.org) — an AI consultancy focused on local-first, privacy-respecting AI solutions.

*"The best AI memory is the one you own."*
