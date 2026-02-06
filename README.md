# aina-gateway

MCP Gateway für PixelMemory – macht lokale Pixeltable-Daten (Memories & Bookmarks) über das MCP Streamable HTTP Protokoll für Claude.ai zugänglich.

## Architektur

```
Claude.ai Web ──HTTPS/SSE──► Cloudflare Tunnel ──► aina-gateway (localhost:8008) ──► Pixeltable
```

## Setup

```bash
cd /Volumes/AINA/aina-gateway

# Virtual Environment
python3 -m venv .venv
source .venv/bin/activate

# Dependencies installieren
pip install -e ".[dev]"

# Konfiguration
cp .env.example .env
# .env nach Bedarf anpassen
```

## Starten

```bash
# Aus dem Projektverzeichnis
source .venv/bin/activate
python -m src.server

# Oder via Entry Point (nach pip install -e .)
aina-gateway
```

Server läuft auf `http://127.0.0.1:8008/mcp`

## Testen

```bash
# Health Check - MCP Endpoint erreichbar?
curl -s http://127.0.0.1:8008/mcp -X POST \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"test","version":"0.1"}}}'

# Tools auflisten
curl -s http://127.0.0.1:8008/mcp -X POST \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'
```

## Verfügbare Tools

| Tool | Beschreibung |
|------|-------------|
| `memory_search` | Memories durchsuchen (Substring-Match) |
| `memory_list` | Memories auflisten (mit Filtern) |
| `memory_add` | Neue Memory anlegen |
| `bookmark_search` | Bookmarks durchsuchen |
| `bookmark_list` | Bookmarks auflisten |
| `bookmark_add` | Neuen Bookmark anlegen |
| `get_schema` | Tabellenstruktur abfragen |

## Roadmap

- [x] Phase 1: Gateway lokal implementieren und testen
- [ ] Phase 2: API-Key Authentifizierung
- [ ] Phase 3: Cloudflare Tunnel einrichten
- [ ] Phase 4: In Claude.ai als Remote MCP konfigurieren
