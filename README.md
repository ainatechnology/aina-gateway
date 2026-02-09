# pixelmemory-gateway

**Give Claude a persistent, local-first memory — across conversations, projects, and devices.**

An MCP server that connects Claude.ai and Claude Desktop to a local [Pixeltable](https://github.com/pixeltable/pixeltable) database via [Streamable HTTP](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports#streamable-http). Store memories, bookmarks, chat references, project metadata, and document indices on your own machine. No cloud. No vendor lock-in. Full control.

```
Claude.ai ──HTTPS──► Cloudflare Tunnel ──► pixelmemory-gateway ──► Pixeltable (local)
Claude Desktop VM ──────── LAN ──────────► pixelmemory-gateway ──► Pixeltable (local)
```

## The Problem

Claude doesn't remember you. Every conversation starts from zero. Anthropic's built-in memory is limited to the current project and updates sporadically. If you work across multiple projects or switch between Claude.ai and Claude Desktop, context is lost.

## The Solution

pixelmemory-gateway runs a local MCP server that gives Claude read/write access to a Pixeltable database on your machine. Memories persist across conversations, projects, and clients — because they live on *your* hardware.

### Key Features

- **30 MCP tools** — full CRUD (search, list, add, update, delete) across 5 tables, plus vault access and schema introspection
- **5 knowledge tables** — memories, bookmarks, chats, projects, documents
- **Row-level operations** — every record has a unique `row_id` for precise update and delete
- **Local-first** — all data stays on your machine (Pixeltable + PostgreSQL)
- **Dual access** — Claude.ai via Cloudflare Tunnel, Claude Desktop via LAN
- **Security stack** — IP whitelist (Anthropic IPs only) + Bearer token auth (with smart exemptions)
- **Auto-start** — macOS LaunchAgent with crash recovery
- **Async-safe** — synchronous Pixeltable calls offloaded to threads

---

## Quick Start

### Prerequisites

- Python 3.13 (not 3.14 — see [known issues](#known-issues))
- [Pixeltable](https://github.com/pixeltable/pixeltable) installed and initialized
- A domain name you control (required for Cloudflare Tunnel → Claude.ai access)

### Installation

```bash
git clone https://github.com/ainatechnology/aina-gateway.git
cd aina-gateway

python3.13 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

cp .env.example .env
# Edit .env to your needs
```

### Create the Database Schema

```bash
python scripts/setup_schema.py
```

This creates all 5 tables with the correct schema including `row_id`.

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
# Anthropic IPs and localhost are always exempt from Bearer auth
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

| Access Path | Bearer Token | IP Whitelist | Notes |
|---|---|---|---|
| **Claude.ai** via Cloudflare Tunnel | Exempt | Anthropic IPs only | Authless by design |
| **Claude Desktop** via LAN | Required | Private networks | API key protects LAN access |
| **localhost** | Exempt | Loopback | Trusted by default |

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

### Memory (knowledge, decisions, learnings)

| Tool | Description | Key Parameters |
|---|---|---|
| `memory_search` | Search by content substring | `query`, `limit` |
| `memory_list` | List recent memories | `limit`, `memory_type`, `project` |
| `memory_add` | Store a new memory | `content`, `memory_type`, `projects`, `tags` |
| `memory_update` | Update by row_id | `row_id`, `content`, `memory_type`, `projects`, `tags` |
| `memory_delete` | Delete by row_id | `row_id` |

### Bookmarks (external URLs and references)

| Tool | Description | Key Parameters |
|---|---|---|
| `bookmark_search` | Search by title/URL/description | `query`, `limit` |
| `bookmark_list` | List recent bookmarks | `limit`, `bookmark_type` |
| `bookmark_add` | Store a new bookmark | `url`, `title`, `description`, `tags` |
| `bookmark_update` | Update by row_id | `row_id`, `url`, `title`, `description` |
| `bookmark_delete` | Delete by row_id | `row_id` |

### Chats (Claude.ai conversation references)

| Tool | Description | Key Parameters |
|---|---|---|
| `chat_search` | Search by title/project/chat_id | `query`, `limit` |
| `chat_list` | List registered chats | `limit`, `project_slug`, `active` |
| `chat_add` | Register a chat | `chat_id`, `chat_title`, `project_slug` |
| `chat_update` | Update by row_id | `row_id`, `chat_title`, `active` |
| `chat_delete` | Delete by row_id | `row_id` |

### Projects (project registry)

| Tool | Description | Key Parameters |
|---|---|---|
| `project_search` | Search by name/slug/description | `query`, `limit` |
| `project_list` | List projects | `limit`, `status`, `category` |
| `project_add` | Register a project | `name`, `slug`, `status`, `technologies` |
| `project_update` | Update by row_id | `row_id`, `status`, `next_steps`, `notes` |
| `project_delete` | Delete by row_id | `row_id` |

### Documents (vault file & artifact index)

| Tool | Description | Key Parameters |
|---|---|---|
| `document_search` | Search by title/path/description | `query`, `limit` |
| `document_list` | List documents | `limit`, `doc_type`, `project` |
| `document_add` | Register a document | `path`, `title`, `doc_type`, `projects` |
| `document_update` | Update by row_id | `row_id`, `title`, `path`, `doc_type` |
| `document_delete` | Delete by row_id | `row_id` |

### Utility Tools

| Tool | Description | Key Parameters |
|---|---|---|
| `vault_read` | Read a file from the Obsidian Vault | `path` |
| `vault_write` | Write a file to the Vault | `path`, `content` |
| `vault_list` | List directory contents | `path` |
| `get_schema` | Inspect table structure | `table_name` |

---

## Connecting Claude.ai (via Cloudflare Tunnel)

Claude.ai's Remote MCP feature connects to your gateway over the internet. This requires a **domain name** you control, pointed through a Cloudflare Tunnel to your local machine. The IP whitelist ensures only Anthropic's servers can reach your gateway — no other traffic gets through.

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

Copy the LaunchAgent plist from `deploy/` to your LaunchAgents directory, edit the paths, and load it:

```bash
cp deploy/org.pixelmemory.gateway.plist ~/Library/LaunchAgents/
# Edit paths in the plist to match your installation
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/org.pixelmemory.gateway.plist
```

The gateway will start automatically at login and restart on crash.

To stop/restart:

```bash
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/org.pixelmemory.gateway.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/org.pixelmemory.gateway.plist
```

---

## Pixeltable Schema

The gateway manages 5 tables in the `memory` directory. All tables include a `row_id` (UUID4 hex, 16 chars) for unique identification, plus `created_at` and `updated_at` timestamps.

### `memory.memories`

| Column | Type | Description |
|---|---|---|
| `row_id` | String | Unique identifier (auto-generated) |
| `content` | String | The memory content |
| `memory_type` | String | Category: `learning`, `status`, `decision`, `note`, `preference`, `reference` |
| `projects` | JSON | Associated project slugs |
| `tags` | JSON | Tags for organization |
| `source` | String | Origin (chat UUID or `claude-web`) |
| `created_at` | String | ISO 8601 timestamp |
| `updated_at` | String | ISO 8601 timestamp |

### `memory.bookmarks`

| Column | Type | Description |
|---|---|---|
| `row_id` | String | Unique identifier |
| `url` | String | Bookmark URL |
| `title` | String | Page title |
| `description` | String | Description |
| `bookmark_type` | String | Category: `reference`, `tool`, `article`, `documentation` |
| `projects` | JSON | Associated projects |
| `tags` | JSON | Tags |
| `source` | String | Origin |
| `language` | String | Content language (`en`, `de`, ...) |
| `created_at` | String | ISO 8601 timestamp |
| `updated_at` | String | ISO 8601 timestamp |

### `memory.chats`

| Column | Type | Description |
|---|---|---|
| `row_id` | String | Unique identifier |
| `chat_id` | String | Claude.ai chat UUID |
| `chat_title` | String | Human-readable title |
| `project_slug` | String | Associated project |
| `active` | String | Status: `yes` or `no` |
| `source` | String | Origin |
| `created_at` | String | ISO 8601 timestamp |
| `updated_at` | String | ISO 8601 timestamp |

### `memory.projects`

| Column | Type | Description |
|---|---|---|
| `row_id` | String | Unique identifier |
| `name` | String | Project name |
| `slug` | String | URL-safe identifier |
| `description` | String | Brief description |
| `status` | String | `active`, `paused`, `completed` |
| `category` | String | Project category |
| `priority` | String | `low`, `normal`, `high`, `critical` |
| `paths` | JSON | File system paths |
| `technologies` | JSON | Tech stack |
| `tags` | JSON | Tags |
| `related_projects` | JSON | Related project slugs |
| `next_steps` | String | Planned next steps |
| `notes` | String | Additional notes |
| `claude_project_id` | String | Claude.ai project UUID |
| `created_at` | String | ISO 8601 timestamp |
| `updated_at` | String | ISO 8601 timestamp |

### `memory.documents`

| Column | Type | Description |
|---|---|---|
| `row_id` | String | Unique identifier |
| `path` | String | Vault path or external URL |
| `title` | String | Document title |
| `description` | String | Description |
| `doc_type` | String | `artifact`, `report`, `template`, `reference`, `external` |
| `projects` | JSON | Associated projects |
| `tags` | JSON | Tags |
| `source` | String | Origin |
| `created_at` | String | ISO 8601 timestamp |
| `updated_at` | String | ISO 8601 timestamp |

---

## Technical Design Decisions

### Why Pixeltable?

Pixeltable provides a local PostgreSQL-backed database with built-in embedding support (via `sentence-transformers`). This means semantic search comes for free — no external vector database needed.

### Why `asyncio.to_thread()`?

FastMCP runs in an async event loop. Pixeltable operations are synchronous and blocking. Every tool call is offloaded to a thread to keep the event loop responsive:

```python
@mcp.tool()
async def memory_search(query: str, limit: int = 20) -> str:
    return await asyncio.to_thread(_do_memory_search, query, limit)
```

### Why Not OAuth?

Claude.ai Custom Connectors support either OAuth or authless — no simple Bearer token. Since implementing a full OAuth flow adds significant complexity for a single-user gateway, we chose authless mode protected by IP filtering instead. Bearer token auth is reserved for LAN access (Claude Desktop), while Anthropic IPs are automatically exempt.

### Why `row_id` Instead of Natural Keys?

Some tables have natural candidates (`chat_id`, `slug`, `url`), others don't (`memories`). A consistent `row_id` across all tables provides a uniform API for update and delete operations without ambiguity.

---

## Migration from v1

If you have an existing installation without `row_id` columns:

```bash
python scripts/migrate_add_row_id.py
```

For `memory.memories` (which may have an embedding index with string length limits), use the dedicated fix script:

```bash
python scripts/fix_memories_migration.py
```

---

## Known Issues

- **Python 3.14**: The `anyio` library (MCP SDK dependency) has a bug causing `TypeError: cannot create weak reference to 'NoneType' object`. Use Python 3.13.
- **Port conflicts**: After an unclean shutdown, the port may remain occupied. Fix with `kill -9 $(lsof -ti:8008)`.
- **LaunchAgent commands**: On modern macOS, use `launchctl bootstrap/bootout` instead of the deprecated `load/unload`.

---

## Project Structure

```
aina-gateway/
├── src/
│   ├── __init__.py      # Package marker
│   ├── auth.py          # IPWhitelistMiddleware + BearerTokenMiddleware
│   ├── config.py        # Configuration from .env
│   ├── server.py        # FastMCP server setup + startup
│   └── tools.py         # All 30 MCP tool implementations
├── scripts/
│   ├── setup_schema.py          # Create tables for new installations
│   ├── migrate_add_row_id.py    # Add row_id to existing tables
│   └── fix_memories_migration.py # Fix memories table specifically
├── deploy/
│   ├── org.pixelmemory.gateway.plist  # macOS LaunchAgent template
│   └── org.pixelmemory.tunnel.plist   # Cloudflare Tunnel LaunchAgent
├── tests/
│   └── test_gateway.py  # Integration tests
├── .env.example         # Configuration template
├── .gitignore
├── pyproject.toml       # Dependencies + metadata
├── CHANGELOG.md
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
