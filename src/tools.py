"""PixelMemory tools - Memory and Bookmark operations via Pixeltable."""

import asyncio
import json
from datetime import datetime, timezone
from functools import partial
from typing import Optional

import pixeltable as pxt

from mcp.server.fastmcp import FastMCP


def _format_rows(result_set) -> list[dict]:
    """Convert Pixeltable ResultSet to list of dicts."""
    return [row for row in result_set]


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


async def _run_sync(func, *args, **kwargs):
    """Run a synchronous function in a thread to avoid blocking the event loop."""
    return await asyncio.to_thread(partial(func, *args, **kwargs))


# ── Synchronous Pixeltable operations ─────────────────────────

def _do_memory_search(query: str, limit: int) -> str:
    t = pxt.get_table("memory.memories")
    results = t.where(
        t.content.contains(query)
    ).order_by(t.created_at, asc=False).limit(limit).collect()
    return json.dumps(_format_rows(results), ensure_ascii=False, indent=2)


def _do_memory_list(limit: int, memory_type: Optional[str], project: Optional[str]) -> str:
    t = pxt.get_table("memory.memories")
    q = t
    if memory_type:
        q = q.where(t.memory_type == memory_type)
    results = q.order_by(t.created_at, asc=False).limit(limit).collect()
    rows = _format_rows(results)
    if project:
        rows = [r for r in rows if project in (r.get("projects") or [])]
    return json.dumps(rows, ensure_ascii=False, indent=2)


def _do_memory_add(content, memory_type, projects, tags, source) -> str:
    t = pxt.get_table("memory.memories")
    now = _now_iso()
    entry = {
        "content": content,
        "memory_type": memory_type,
        "projects": projects or [],
        "tags": tags or [],
        "source": source,
        "created_at": now,
        "updated_at": now,
    }
    t.insert([entry])
    return json.dumps({"status": "ok", "memory": entry}, ensure_ascii=False, indent=2)


def _do_bookmark_search(query: str, limit: int) -> str:
    t = pxt.get_table("memory.bookmarks")
    results = t.where(
        (t.title.contains(query))
        | (t.description.contains(query))
        | (t.url.contains(query))
    ).order_by(t.created_at, asc=False).limit(limit).collect()
    return json.dumps(_format_rows(results), ensure_ascii=False, indent=2)


def _do_bookmark_list(limit: int, bookmark_type: Optional[str]) -> str:
    t = pxt.get_table("memory.bookmarks")
    q = t
    if bookmark_type:
        q = q.where(t.bookmark_type == bookmark_type)
    results = q.order_by(t.created_at, asc=False).limit(limit).collect()
    return json.dumps(_format_rows(results), ensure_ascii=False, indent=2)


def _do_bookmark_add(url, title, description, bookmark_type, projects, tags, source, language) -> str:
    t = pxt.get_table("memory.bookmarks")
    now = _now_iso()
    entry = {
        "url": url,
        "title": title,
        "description": description,
        "bookmark_type": bookmark_type,
        "projects": projects or [],
        "tags": tags or [],
        "source": source,
        "language": language,
        "http_status": None,
        "last_checked": None,
        "created_at": now,
        "updated_at": now,
        "search_text": f"{title} {description} {url}",
    }
    t.insert([entry])
    return json.dumps({"status": "ok", "bookmark": entry}, ensure_ascii=False, indent=2)


def _do_get_schema(table_name: str) -> str:
    if table_name not in ("memory.memories", "memory.bookmarks"):
        return json.dumps({"error": f"Unknown table: {table_name}. Use 'memory.memories' or 'memory.bookmarks'."})
    t = pxt.get_table(table_name)
    schema = {}
    for col_name in t.columns():
        col_expr = getattr(t, col_name)
        schema[col_name] = str(col_expr.col_type)
    return json.dumps({"table": table_name, "columns": schema}, ensure_ascii=False, indent=2)


# ── Tool registration (async wrappers) ───────────────────────

def register_tools(mcp: FastMCP):
    """Register all PixelMemory tools on the MCP server."""

    @mcp.tool()
    async def memory_search(query: str, limit: int = 20) -> str:
        """Search memories by content (case-insensitive substring match).

        Args:
            query: Search text to find in memory content
            limit: Maximum number of results (default: 20)

        Returns:
            JSON array of matching memories with all fields.
        """
        return await _run_sync(_do_memory_search, query, limit)

    @mcp.tool()
    async def memory_list(
        limit: int = 20,
        memory_type: Optional[str] = None,
        project: Optional[str] = None,
    ) -> str:
        """List recent memories, optionally filtered by type or project.

        Args:
            limit: Maximum number of results (default: 20)
            memory_type: Filter by type (e.g. 'learning', 'status', 'decision', 'note')
            project: Filter by project name (e.g. 'aina-updater', 'cdp')

        Returns:
            JSON array of memories, newest first.
        """
        return await _run_sync(_do_memory_list, limit, memory_type, project)

    @mcp.tool()
    async def memory_add(
        content: str,
        memory_type: str = "note",
        projects: Optional[list[str]] = None,
        tags: Optional[list[str]] = None,
        source: str = "claude-web",
    ) -> str:
        """Add a new memory entry.

        Args:
            content: The memory content text
            memory_type: Type of memory - one of: 'learning', 'status', 'decision', 'note', 'preference'
            projects: List of related project names (e.g. ['aina-updater', 'cdp'])
            tags: List of tags for categorization
            source: Source identifier (default: 'claude-web')

        Returns:
            Confirmation with the stored memory.
        """
        return await _run_sync(_do_memory_add, content, memory_type, projects, tags, source)

    @mcp.tool()
    async def bookmark_search(query: str, limit: int = 20) -> str:
        """Search bookmarks by title, description or URL.

        Args:
            query: Search text to find in bookmark title, description, or URL
            limit: Maximum number of results (default: 20)

        Returns:
            JSON array of matching bookmarks.
        """
        return await _run_sync(_do_bookmark_search, query, limit)

    @mcp.tool()
    async def bookmark_list(
        limit: int = 20,
        bookmark_type: Optional[str] = None,
    ) -> str:
        """List recent bookmarks, optionally filtered by type.

        Args:
            limit: Maximum number of results (default: 20)
            bookmark_type: Filter by bookmark type

        Returns:
            JSON array of bookmarks, newest first.
        """
        return await _run_sync(_do_bookmark_list, limit, bookmark_type)

    @mcp.tool()
    async def bookmark_add(
        url: str,
        title: str,
        description: str = "",
        bookmark_type: str = "reference",
        projects: Optional[list[str]] = None,
        tags: Optional[list[str]] = None,
        source: str = "claude-web",
        language: str = "en",
    ) -> str:
        """Add a new bookmark entry.

        Args:
            url: The URL to bookmark
            title: Title/name of the bookmark
            description: Brief description of the content
            bookmark_type: Type (e.g. 'reference', 'tool', 'article', 'documentation')
            projects: List of related project names
            tags: List of tags for categorization
            source: Source identifier (default: 'claude-web')
            language: Content language code (default: 'en')

        Returns:
            Confirmation with the stored bookmark.
        """
        return await _run_sync(_do_bookmark_add, url, title, description, bookmark_type, projects, tags, source, language)

    @mcp.tool()
    async def get_schema(table_name: str = "memory.memories") -> str:
        """Get the schema of a PixelMemory table.

        Args:
            table_name: Table path (default: 'memory.memories'). Options: 'memory.memories', 'memory.bookmarks'

        Returns:
            JSON object with column names and types.
        """
        return await _run_sync(_do_get_schema, table_name)
