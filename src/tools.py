"""PixelMemory tools v2 - Full CRUD operations via Pixeltable.

Changes from v1:
- row_id (UUID4 hex[:16]) generated automatically on every insert
- update and delete tools for all 5 tables (identified by row_id)
- updated_at set automatically on update
- Total: 30 tools (25 CRUD + 3 Vault + 1 Schema + 1 get_schema)
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from functools import partial
from typing import Optional

import os
from pathlib import Path

import pixeltable as pxt

from mcp.server.fastmcp import FastMCP

# ── Vault configuration ──────────────────────────────────────
VAULT_ROOT = Path("/Users/jung/Documents/AINAVault")
PROJECTS_ROOT = Path("/Volumes/AINA")
ALLOWED_ROOTS = [VAULT_ROOT, PROJECTS_ROOT]


def _validate_vault_path(path: str) -> Path:
    """Ensure path is within allowed roots. Returns resolved Path."""
    p = Path(path).resolve()
    if not any(p == root or root in p.parents for root in ALLOWED_ROOTS):
        raise ValueError(f"Access denied: {path} is outside allowed directories.")
    return p


def _format_rows(result_set) -> list[dict]:
    """Convert Pixeltable ResultSet to list of dicts."""
    return [row for row in result_set]


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _new_row_id() -> str:
    """Generate a short UUID4 hex string for row identification."""
    return uuid.uuid4().hex[:16]


async def _run_sync(func, *args, **kwargs):
    """Run a synchronous function in a thread to avoid blocking the event loop."""
    return await asyncio.to_thread(partial(func, *args, **kwargs))


# ══════════════════════════════════════════════════════════════
# MEMORY operations
# ══════════════════════════════════════════════════════════════

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
    row_id = _new_row_id()
    entry = {
        "row_id": row_id,
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


def _do_memory_update(row_id: str, content: Optional[str], memory_type: Optional[str],
                       projects: Optional[list], tags: Optional[list]) -> str:
    t = pxt.get_table("memory.memories")
    # Verify row exists
    matches = t.where(t.row_id == row_id).collect()
    if len(matches) == 0:
        return json.dumps({"status": "error", "message": f"No memory found with row_id: {row_id}"})

    updates = {"updated_at": _now_iso()}
    if content is not None:
        updates["content"] = content
    if memory_type is not None:
        updates["memory_type"] = memory_type
    if projects is not None:
        updates["projects"] = projects
    if tags is not None:
        updates["tags"] = tags

    t.where(t.row_id == row_id).update(updates)
    # Fetch updated row
    updated = t.where(t.row_id == row_id).collect()
    return json.dumps({"status": "ok", "updated": _format_rows(updated)[0]}, ensure_ascii=False, indent=2)


def _do_memory_delete(row_id: str) -> str:
    t = pxt.get_table("memory.memories")
    matches = t.where(t.row_id == row_id).collect()
    if len(matches) == 0:
        return json.dumps({"status": "error", "message": f"No memory found with row_id: {row_id}"})

    deleted_content = matches[0].get("content", "")[:80]
    t.where(t.row_id == row_id).delete()
    return json.dumps({"status": "ok", "deleted_row_id": row_id, "content_preview": deleted_content})


# ══════════════════════════════════════════════════════════════
# BOOKMARK operations
# ══════════════════════════════════════════════════════════════

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
    row_id = _new_row_id()
    entry = {
        "row_id": row_id,
        "url": url,
        "title": title,
        "description": description,
        "bookmark_type": bookmark_type,
        "projects": projects or [],
        "tags": tags or [],
        "source": source,
        "language": language,
        "created_at": now,
        "updated_at": now,
    }
    t.insert([entry])
    return json.dumps({"status": "ok", "bookmark": entry}, ensure_ascii=False, indent=2)


def _do_bookmark_update(row_id: str, url: Optional[str], title: Optional[str],
                         description: Optional[str], bookmark_type: Optional[str],
                         projects: Optional[list], tags: Optional[list]) -> str:
    t = pxt.get_table("memory.bookmarks")
    matches = t.where(t.row_id == row_id).collect()
    if len(matches) == 0:
        return json.dumps({"status": "error", "message": f"No bookmark found with row_id: {row_id}"})

    updates = {"updated_at": _now_iso()}
    if url is not None:
        updates["url"] = url
    if title is not None:
        updates["title"] = title
    if description is not None:
        updates["description"] = description
    if bookmark_type is not None:
        updates["bookmark_type"] = bookmark_type
    if projects is not None:
        updates["projects"] = projects
    if tags is not None:
        updates["tags"] = tags

    t.where(t.row_id == row_id).update(updates)
    updated = t.where(t.row_id == row_id).collect()
    return json.dumps({"status": "ok", "updated": _format_rows(updated)[0]}, ensure_ascii=False, indent=2)


def _do_bookmark_delete(row_id: str) -> str:
    t = pxt.get_table("memory.bookmarks")
    matches = t.where(t.row_id == row_id).collect()
    if len(matches) == 0:
        return json.dumps({"status": "error", "message": f"No bookmark found with row_id: {row_id}"})

    deleted_title = matches[0].get("title", "")[:80]
    t.where(t.row_id == row_id).delete()
    return json.dumps({"status": "ok", "deleted_row_id": row_id, "title_preview": deleted_title})


# ══════════════════════════════════════════════════════════════
# CHAT operations
# ══════════════════════════════════════════════════════════════

def _do_chat_search(query: str, limit: int) -> str:
    t = pxt.get_table("memory.chats")
    results = t.where(
        (t.chat_title.contains(query))
        | (t.project_slug.contains(query))
        | (t.chat_id.contains(query))
    ).order_by(t.created_at, asc=False).limit(limit).collect()
    return json.dumps(_format_rows(results), ensure_ascii=False, indent=2)


def _do_chat_list(limit: int, project_slug: Optional[str], active: Optional[str]) -> str:
    t = pxt.get_table("memory.chats")
    q = t
    if project_slug:
        q = q.where(t.project_slug == project_slug)
    if active:
        q = q.where(t.active == active)
    results = q.order_by(t.created_at, asc=False).limit(limit).collect()
    return json.dumps(_format_rows(results), ensure_ascii=False, indent=2)


def _do_chat_add(chat_id, chat_title, project_slug, active, source) -> str:
    t = pxt.get_table("memory.chats")
    now = _now_iso()
    row_id = _new_row_id()
    entry = {
        "row_id": row_id,
        "chat_id": chat_id,
        "chat_title": chat_title,
        "project_slug": project_slug,
        "active": active,
        "source": source,
        "created_at": now,
        "updated_at": now,
    }
    t.insert([entry])
    return json.dumps({"status": "ok", "chat": entry}, ensure_ascii=False, indent=2)


def _do_chat_update(row_id: str, chat_title: Optional[str], project_slug: Optional[str],
                     active: Optional[str]) -> str:
    t = pxt.get_table("memory.chats")
    matches = t.where(t.row_id == row_id).collect()
    if len(matches) == 0:
        return json.dumps({"status": "error", "message": f"No chat found with row_id: {row_id}"})

    updates = {"updated_at": _now_iso()}
    if chat_title is not None:
        updates["chat_title"] = chat_title
    if project_slug is not None:
        updates["project_slug"] = project_slug
    if active is not None:
        updates["active"] = active

    t.where(t.row_id == row_id).update(updates)
    updated = t.where(t.row_id == row_id).collect()
    return json.dumps({"status": "ok", "updated": _format_rows(updated)[0]}, ensure_ascii=False, indent=2)


def _do_chat_delete(row_id: str) -> str:
    t = pxt.get_table("memory.chats")
    matches = t.where(t.row_id == row_id).collect()
    if len(matches) == 0:
        return json.dumps({"status": "error", "message": f"No chat found with row_id: {row_id}"})

    deleted_title = matches[0].get("chat_title", "")[:80]
    t.where(t.row_id == row_id).delete()
    return json.dumps({"status": "ok", "deleted_row_id": row_id, "title_preview": deleted_title})


# ══════════════════════════════════════════════════════════════
# PROJECT operations
# ══════════════════════════════════════════════════════════════

def _do_project_search(query: str, limit: int) -> str:
    t = pxt.get_table("memory.projects")
    results = t.where(
        (t.name.contains(query))
        | (t.slug.contains(query))
        | (t.description.contains(query))
    ).order_by(t.created_at, asc=False).limit(limit).collect()
    return json.dumps(_format_rows(results), ensure_ascii=False, indent=2)


def _do_project_list(limit: int, status: Optional[str], category: Optional[str]) -> str:
    t = pxt.get_table("memory.projects")
    q = t
    if status:
        q = q.where(t.status == status)
    if category:
        q = q.where(t.category == category)
    results = q.order_by(t.created_at, asc=False).limit(limit).collect()
    return json.dumps(_format_rows(results), ensure_ascii=False, indent=2)


def _do_project_add(
    name, slug, description, status, category, priority,
    paths, technologies, tags, related_projects,
    next_steps, notes, claude_project_id,
) -> str:
    t = pxt.get_table("memory.projects")
    now = _now_iso()
    row_id = _new_row_id()
    entry = {
        "row_id": row_id,
        "name": name,
        "slug": slug,
        "description": description or "",
        "status": status,
        "category": category or "",
        "priority": priority or "normal",
        "paths": paths or [],
        "technologies": technologies or [],
        "tags": tags or [],
        "related_projects": related_projects or [],
        "next_steps": next_steps or "",
        "notes": notes or "",
        "claude_project_id": claude_project_id or "",
        "created_at": now,
        "updated_at": now,
    }
    t.insert([entry])
    return json.dumps({"status": "ok", "project": entry}, ensure_ascii=False, indent=2)


def _do_project_update(row_id: str, name: Optional[str], description: Optional[str],
                        status: Optional[str], category: Optional[str], priority: Optional[str],
                        paths: Optional[list], technologies: Optional[list], tags: Optional[list],
                        related_projects: Optional[list], next_steps: Optional[str],
                        notes: Optional[str]) -> str:
    t = pxt.get_table("memory.projects")
    matches = t.where(t.row_id == row_id).collect()
    if len(matches) == 0:
        return json.dumps({"status": "error", "message": f"No project found with row_id: {row_id}"})

    updates = {"updated_at": _now_iso()}
    if name is not None:
        updates["name"] = name
    if description is not None:
        updates["description"] = description
    if status is not None:
        updates["status"] = status
    if category is not None:
        updates["category"] = category
    if priority is not None:
        updates["priority"] = priority
    if paths is not None:
        updates["paths"] = paths
    if technologies is not None:
        updates["technologies"] = technologies
    if tags is not None:
        updates["tags"] = tags
    if related_projects is not None:
        updates["related_projects"] = related_projects
    if next_steps is not None:
        updates["next_steps"] = next_steps
    if notes is not None:
        updates["notes"] = notes

    t.where(t.row_id == row_id).update(updates)
    updated = t.where(t.row_id == row_id).collect()
    return json.dumps({"status": "ok", "updated": _format_rows(updated)[0]}, ensure_ascii=False, indent=2)


def _do_project_delete(row_id: str) -> str:
    t = pxt.get_table("memory.projects")
    matches = t.where(t.row_id == row_id).collect()
    if len(matches) == 0:
        return json.dumps({"status": "error", "message": f"No project found with row_id: {row_id}"})

    deleted_name = matches[0].get("name", "")[:80]
    t.where(t.row_id == row_id).delete()
    return json.dumps({"status": "ok", "deleted_row_id": row_id, "name_preview": deleted_name})


# ══════════════════════════════════════════════════════════════
# DOCUMENT operations
# ══════════════════════════════════════════════════════════════

def _do_document_search(query: str, limit: int) -> str:
    t = pxt.get_table("memory.documents")
    results = t.where(
        (t.title.contains(query))
        | (t.description.contains(query))
        | (t.path.contains(query))
    ).order_by(t.created_at, asc=False).limit(limit).collect()
    return json.dumps(_format_rows(results), ensure_ascii=False, indent=2)


def _do_document_list(limit: int, doc_type: Optional[str], project: Optional[str]) -> str:
    t = pxt.get_table("memory.documents")
    q = t
    if doc_type:
        q = q.where(t.doc_type == doc_type)
    results = q.order_by(t.created_at, asc=False).limit(limit).collect()
    rows = _format_rows(results)
    if project:
        rows = [r for r in rows if project in (r.get("projects") or [])]
    return json.dumps(rows, ensure_ascii=False, indent=2)


def _do_document_add(path, title, description, doc_type, projects, tags, source) -> str:
    t = pxt.get_table("memory.documents")
    now = _now_iso()
    row_id = _new_row_id()
    entry = {
        "row_id": row_id,
        "path": path,
        "title": title,
        "description": description,
        "doc_type": doc_type,
        "projects": projects or [],
        "tags": tags or [],
        "source": source,
        "created_at": now,
        "updated_at": now,
    }
    t.insert([entry])
    return json.dumps({"status": "ok", "document": entry}, ensure_ascii=False, indent=2)


def _do_document_update(row_id: str, path: Optional[str], title: Optional[str],
                         description: Optional[str], doc_type: Optional[str],
                         projects: Optional[list], tags: Optional[list]) -> str:
    t = pxt.get_table("memory.documents")
    matches = t.where(t.row_id == row_id).collect()
    if len(matches) == 0:
        return json.dumps({"status": "error", "message": f"No document found with row_id: {row_id}"})

    updates = {"updated_at": _now_iso()}
    if path is not None:
        updates["path"] = path
    if title is not None:
        updates["title"] = title
    if description is not None:
        updates["description"] = description
    if doc_type is not None:
        updates["doc_type"] = doc_type
    if projects is not None:
        updates["projects"] = projects
    if tags is not None:
        updates["tags"] = tags

    t.where(t.row_id == row_id).update(updates)
    updated = t.where(t.row_id == row_id).collect()
    return json.dumps({"status": "ok", "updated": _format_rows(updated)[0]}, ensure_ascii=False, indent=2)


def _do_document_delete(row_id: str) -> str:
    t = pxt.get_table("memory.documents")
    matches = t.where(t.row_id == row_id).collect()
    if len(matches) == 0:
        return json.dumps({"status": "error", "message": f"No document found with row_id: {row_id}"})

    deleted_title = matches[0].get("title", "")[:80]
    t.where(t.row_id == row_id).delete()
    return json.dumps({"status": "ok", "deleted_row_id": row_id, "title_preview": deleted_title})


# ══════════════════════════════════════════════════════════════
# VAULT file operations
# ══════════════════════════════════════════════════════════════

def _do_vault_read(path: str) -> str:
    p = _validate_vault_path(path)
    if not p.exists():
        return json.dumps({"error": f"File not found: {path}"})
    if not p.is_file():
        return json.dumps({"error": f"Not a file: {path}"})
    try:
        content = p.read_text(encoding="utf-8")
        return json.dumps({"path": str(p), "content": content}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"Read error: {str(e)}"})


def _do_vault_write(path: str, content: str) -> str:
    p = _validate_vault_path(path)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return json.dumps({"status": "ok", "path": str(p), "bytes": len(content.encode("utf-8"))})
    except Exception as e:
        return json.dumps({"error": f"Write error: {str(e)}"})


def _do_vault_list(path: str) -> str:
    p = _validate_vault_path(path)
    if not p.exists():
        return json.dumps({"error": f"Path not found: {path}"})
    if not p.is_dir():
        return json.dumps({"error": f"Not a directory: {path}"})
    entries = []
    for item in sorted(p.iterdir()):
        if item.name.startswith("."):
            continue
        entries.append({
            "name": item.name,
            "type": "dir" if item.is_dir() else "file",
            "size": item.stat().st_size if item.is_file() else None,
        })
    return json.dumps({"path": str(p), "entries": entries}, ensure_ascii=False, indent=2)


# ══════════════════════════════════════════════════════════════
# SCHEMA introspection
# ══════════════════════════════════════════════════════════════

def _do_get_schema(table_name: str) -> str:
    valid_tables = ("memory.memories", "memory.bookmarks", "memory.chats", "memory.projects", "memory.documents")
    if table_name not in valid_tables:
        return json.dumps({"error": f"Unknown table: {table_name}. Options: {', '.join(valid_tables)}"})
    t = pxt.get_table(table_name)
    schema = {}
    for col_name in t.columns():
        col_expr = getattr(t, col_name)
        schema[col_name] = str(col_expr.col_type)
    return json.dumps({"table": table_name, "columns": schema}, ensure_ascii=False, indent=2)


# ══════════════════════════════════════════════════════════════
# Tool registration (async wrappers)
# ══════════════════════════════════════════════════════════════

def register_tools(mcp: FastMCP):
    """Register all PixelMemory tools on the MCP server."""

    # ── Memory tools ──────────────────────────────────────────

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
            Confirmation with the stored memory including row_id.
        """
        return await _run_sync(_do_memory_add, content, memory_type, projects, tags, source)

    @mcp.tool()
    async def memory_update(
        row_id: str,
        content: Optional[str] = None,
        memory_type: Optional[str] = None,
        projects: Optional[list[str]] = None,
        tags: Optional[list[str]] = None,
    ) -> str:
        """Update an existing memory entry by row_id. Only provided fields are changed.

        Args:
            row_id: The unique row identifier (from search/list results)
            content: New content text (optional)
            memory_type: New type (optional)
            projects: New project list - replaces existing (optional)
            tags: New tag list - replaces existing (optional)

        Returns:
            Updated memory entry or error if row_id not found.
        """
        return await _run_sync(_do_memory_update, row_id, content, memory_type, projects, tags)

    @mcp.tool()
    async def memory_delete(row_id: str) -> str:
        """Delete a memory entry by row_id.

        Args:
            row_id: The unique row identifier (from search/list results)

        Returns:
            Confirmation with deleted row_id and content preview, or error if not found.
        """
        return await _run_sync(_do_memory_delete, row_id)

    # ── Bookmark tools ────────────────────────────────────────

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
            Confirmation with the stored bookmark including row_id.
        """
        return await _run_sync(_do_bookmark_add, url, title, description, bookmark_type, projects, tags, source, language)

    @mcp.tool()
    async def bookmark_update(
        row_id: str,
        url: Optional[str] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
        bookmark_type: Optional[str] = None,
        projects: Optional[list[str]] = None,
        tags: Optional[list[str]] = None,
    ) -> str:
        """Update an existing bookmark by row_id. Only provided fields are changed.

        Args:
            row_id: The unique row identifier
            url: New URL (optional)
            title: New title (optional)
            description: New description (optional)
            bookmark_type: New type (optional)
            projects: New project list (optional)
            tags: New tag list (optional)

        Returns:
            Updated bookmark or error if not found.
        """
        return await _run_sync(_do_bookmark_update, row_id, url, title, description, bookmark_type, projects, tags)

    @mcp.tool()
    async def bookmark_delete(row_id: str) -> str:
        """Delete a bookmark by row_id.

        Args:
            row_id: The unique row identifier

        Returns:
            Confirmation or error if not found.
        """
        return await _run_sync(_do_bookmark_delete, row_id)

    # ── Chat tools ────────────────────────────────────────────

    @mcp.tool()
    async def chat_search(query: str, limit: int = 20) -> str:
        """Search chats by title, project slug, or chat ID.

        Args:
            query: Search text to find in chat title, project slug, or chat ID
            limit: Maximum number of results (default: 20)

        Returns:
            JSON array of matching chats.
        """
        return await _run_sync(_do_chat_search, query, limit)

    @mcp.tool()
    async def chat_list(
        limit: int = 20,
        project_slug: Optional[str] = None,
        active: Optional[str] = None,
    ) -> str:
        """List registered chats, optionally filtered by project or status.

        Args:
            limit: Maximum number of results (default: 20)
            project_slug: Filter by project slug (e.g. 'claude', 'delphi')
            active: Filter by active status ('yes' or 'no')

        Returns:
            JSON array of chats, newest first.
        """
        return await _run_sync(_do_chat_list, limit, project_slug, active)

    @mcp.tool()
    async def chat_add(
        chat_id: str,
        chat_title: str,
        project_slug: str,
        active: str = "yes",
        source: str = "claude-web",
    ) -> str:
        """Register a new chat in PixelMemory.

        Args:
            chat_id: The chat UUID from the Claude.ai URL
            chat_title: Human-readable chat title
            project_slug: Project slug this chat belongs to (e.g. 'claude', 'delphi')
            active: Chat status - 'yes' or 'no' (default: 'yes')
            source: Source identifier (default: 'claude-web')

        Returns:
            Confirmation with the stored chat entry including row_id.
        """
        return await _run_sync(_do_chat_add, chat_id, chat_title, project_slug, active, source)

    @mcp.tool()
    async def chat_update(
        row_id: str,
        chat_title: Optional[str] = None,
        project_slug: Optional[str] = None,
        active: Optional[str] = None,
    ) -> str:
        """Update an existing chat entry by row_id.

        Args:
            row_id: The unique row identifier
            chat_title: New title (optional)
            project_slug: New project slug (optional)
            active: New status 'yes'/'no' (optional)

        Returns:
            Updated chat or error if not found.
        """
        return await _run_sync(_do_chat_update, row_id, chat_title, project_slug, active)

    @mcp.tool()
    async def chat_delete(row_id: str) -> str:
        """Delete a chat entry by row_id.

        Args:
            row_id: The unique row identifier

        Returns:
            Confirmation or error if not found.
        """
        return await _run_sync(_do_chat_delete, row_id)

    # ── Project tools ─────────────────────────────────────────

    @mcp.tool()
    async def project_search(query: str, limit: int = 20) -> str:
        """Search projects by name, slug, or description.

        Args:
            query: Search text to find in project name, slug, or description
            limit: Maximum number of results (default: 20)

        Returns:
            JSON array of matching projects with all fields including claude_project_id.
        """
        return await _run_sync(_do_project_search, query, limit)

    @mcp.tool()
    async def project_list(
        limit: int = 20,
        status: Optional[str] = None,
        category: Optional[str] = None,
    ) -> str:
        """List registered projects, optionally filtered by status or category.

        Args:
            limit: Maximum number of results (default: 20)
            status: Filter by status (e.g. 'active', 'paused', 'completed')
            category: Filter by category

        Returns:
            JSON array of projects, newest first.
        """
        return await _run_sync(_do_project_list, limit, status, category)

    @mcp.tool()
    async def project_add(
        name: str,
        slug: str,
        description: str = "",
        status: str = "active",
        category: Optional[str] = None,
        priority: str = "normal",
        paths: Optional[list[str]] = None,
        technologies: Optional[list[str]] = None,
        tags: Optional[list[str]] = None,
        related_projects: Optional[list[str]] = None,
        next_steps: Optional[str] = None,
        notes: Optional[str] = None,
        claude_project_id: Optional[str] = None,
    ) -> str:
        """Register a new project in PixelMemory.

        Args:
            name: Human-readable project name (e.g. 'Development')
            slug: URL-safe identifier (e.g. 'development')
            description: Brief project description
            status: Project status (e.g. 'active', 'paused', 'completed')
            category: Project category
            priority: Priority level (e.g. 'low', 'normal', 'high', 'critical')
            paths: List of file system paths related to this project
            technologies: List of technologies used (e.g. ['rust', 'tauri', 'python'])
            tags: List of tags for categorization
            related_projects: List of related project slugs
            next_steps: Description of next planned steps
            notes: Additional notes
            claude_project_id: The Claude.ai project UUID for direct linking

        Returns:
            Confirmation with the stored project entry including row_id.
        """
        return await _run_sync(
            _do_project_add, name, slug, description, status, category, priority,
            paths, technologies, tags, related_projects, next_steps, notes, claude_project_id,
        )

    @mcp.tool()
    async def project_update(
        row_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
        category: Optional[str] = None,
        priority: Optional[str] = None,
        paths: Optional[list[str]] = None,
        technologies: Optional[list[str]] = None,
        tags: Optional[list[str]] = None,
        related_projects: Optional[list[str]] = None,
        next_steps: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> str:
        """Update an existing project by row_id. Only provided fields are changed.

        Args:
            row_id: The unique row identifier
            name: New name (optional)
            description: New description (optional)
            status: New status (optional)
            category: New category (optional)
            priority: New priority (optional)
            paths: New paths list (optional)
            technologies: New technologies list (optional)
            tags: New tags list (optional)
            related_projects: New related projects list (optional)
            next_steps: New next steps (optional)
            notes: New notes (optional)

        Returns:
            Updated project or error if not found.
        """
        return await _run_sync(
            _do_project_update, row_id, name, description, status, category, priority,
            paths, technologies, tags, related_projects, next_steps, notes,
        )

    @mcp.tool()
    async def project_delete(row_id: str) -> str:
        """Delete a project entry by row_id.

        Args:
            row_id: The unique row identifier

        Returns:
            Confirmation or error if not found.
        """
        return await _run_sync(_do_project_delete, row_id)

    # ── Document tools ────────────────────────────────────────

    @mcp.tool()
    async def document_search(query: str, limit: int = 20) -> str:
        """Search documents by title, description, or path.

        Args:
            query: Search text to find in document title, description, or path
            limit: Maximum number of results (default: 20)

        Returns:
            JSON array of matching documents.
        """
        return await _run_sync(_do_document_search, query, limit)

    @mcp.tool()
    async def document_list(
        limit: int = 20,
        doc_type: Optional[str] = None,
        project: Optional[str] = None,
    ) -> str:
        """List registered documents, optionally filtered by type or project.

        Args:
            limit: Maximum number of results (default: 20)
            doc_type: Filter by type (e.g. 'artifact', 'report', 'template', 'reference', 'external')
            project: Filter by project name

        Returns:
            JSON array of documents, newest first.
        """
        return await _run_sync(_do_document_list, limit, doc_type, project)

    @mcp.tool()
    async def document_add(
        path: str,
        title: str,
        description: str = "",
        doc_type: str = "artifact",
        projects: Optional[list[str]] = None,
        tags: Optional[list[str]] = None,
        source: str = "claude-web",
    ) -> str:
        """Register a document in PixelMemory (index entry, not the file itself).

        Args:
            path: File path in vault or external URL
            title: Document title
            description: Brief description of the content
            doc_type: Type (e.g. 'artifact', 'report', 'template', 'reference', 'external')
            projects: List of related project names
            tags: List of tags for categorization
            source: Chat UUID where document was created (default: 'claude-web')

        Returns:
            Confirmation with the stored document entry including row_id.
        """
        return await _run_sync(_do_document_add, path, title, description, doc_type, projects, tags, source)

    @mcp.tool()
    async def document_update(
        row_id: str,
        path: Optional[str] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
        doc_type: Optional[str] = None,
        projects: Optional[list[str]] = None,
        tags: Optional[list[str]] = None,
    ) -> str:
        """Update an existing document by row_id. Only provided fields are changed.

        Args:
            row_id: The unique row identifier
            path: New path (optional)
            title: New title (optional)
            description: New description (optional)
            doc_type: New type (optional)
            projects: New project list (optional)
            tags: New tag list (optional)

        Returns:
            Updated document or error if not found.
        """
        return await _run_sync(_do_document_update, row_id, path, title, description, doc_type, projects, tags)

    @mcp.tool()
    async def document_delete(row_id: str) -> str:
        """Delete a document entry by row_id.

        Args:
            row_id: The unique row identifier

        Returns:
            Confirmation or error if not found.
        """
        return await _run_sync(_do_document_delete, row_id)

    # ── Vault tools ───────────────────────────────────────────

    @mcp.tool()
    async def vault_read(path: str) -> str:
        """Read a file from the Obsidian Vault (AINAVault).

        Args:
            path: File path within /Users/jung/Documents/AINAVault

        Returns:
            JSON with file path and content.
        """
        return await _run_sync(_do_vault_read, path)

    @mcp.tool()
    async def vault_write(path: str, content: str) -> str:
        """Write a file to the Obsidian Vault (AINAVault). Creates parent directories if needed.

        Args:
            path: File path within /Users/jung/Documents/AINAVault
            content: Text content to write

        Returns:
            Confirmation with path and byte count.
        """
        return await _run_sync(_do_vault_write, path, content)

    @mcp.tool()
    async def vault_list(path: str = "/Users/jung/Documents/AINAVault") -> str:
        """List contents of a directory in the Obsidian Vault (AINAVault).

        Args:
            path: Directory path within /Users/jung/Documents/AINAVault (default: vault root)

        Returns:
            JSON with directory entries (name, type, size).
        """
        return await _run_sync(_do_vault_list, path)

    # ── Schema tool ───────────────────────────────────────────

    @mcp.tool()
    async def get_schema(table_name: str = "memory.memories") -> str:
        """Get the schema of a PixelMemory table.

        Args:
            table_name: Table path (default: 'memory.memories'). Options: 'memory.memories', 'memory.bookmarks', 'memory.chats', 'memory.projects', 'memory.documents'

        Returns:
            JSON object with column names and types.
        """
        return await _run_sync(_do_get_schema, table_name)
