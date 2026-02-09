"""Setup PixelMemory Schema v2: All 5 tables with row_id.

Run this script ONCE to create the PixelMemory database schema from scratch.
For existing installations, use migrate_add_row_id.py instead.

Usage:
    cd /Volumes/AINA/aina-gateway
    source .venv/bin/activate
    python scripts/setup_schema.py

Creates:
    memory.memories   - Knowledge, decisions, learnings, notes
    memory.bookmarks  - External URLs and references
    memory.chats      - Claude.ai chat references
    memory.projects   - Project registry
    memory.documents  - Document index (vault files, artifacts)
"""

import pixeltable as pxt


def create_schema():
    """Create the complete PixelMemory schema."""
    
    pxt.init()
    
    # Create directory (namespace)
    try:
        pxt.create_dir("memory")
        print("✅ Created directory: memory")
    except Exception:
        print("ℹ️  Directory 'memory' already exists")

    # ── memory.memories ──────────────────────────────────────
    try:
        pxt.create_table("memory.memories", {
            "row_id":       pxt.String,
            "content":      pxt.String,
            "memory_type":  pxt.String,   # learning, status, decision, note, preference, reference
            "projects":     pxt.Json,     # ["project-slug", ...]
            "tags":         pxt.Json,     # ["tag1", "tag2", ...]
            "source":       pxt.String,   # chat UUID or "claude-web"
            "created_at":   pxt.String,   # ISO 8601
            "updated_at":   pxt.String,   # ISO 8601
        })
        print("✅ Created table: memory.memories")
    except Exception as e:
        print(f"ℹ️  memory.memories: {e}")

    # ── memory.bookmarks ─────────────────────────────────────
    try:
        pxt.create_table("memory.bookmarks", {
            "row_id":         pxt.String,
            "url":            pxt.String,
            "title":          pxt.String,
            "description":    pxt.String,
            "bookmark_type":  pxt.String,   # reference, tool, article, documentation
            "projects":       pxt.Json,
            "tags":           pxt.Json,
            "source":         pxt.String,
            "language":       pxt.String,   # "en", "de", ...
            "created_at":     pxt.String,
            "updated_at":     pxt.String,
        })
        print("✅ Created table: memory.bookmarks")
    except Exception as e:
        print(f"ℹ️  memory.bookmarks: {e}")

    # ── memory.chats ─────────────────────────────────────────
    try:
        pxt.create_table("memory.chats", {
            "row_id":        pxt.String,
            "chat_id":       pxt.String,   # Claude.ai UUID
            "chat_title":    pxt.String,
            "project_slug":  pxt.String,
            "active":        pxt.String,   # "yes" or "no"
            "source":        pxt.String,
            "created_at":    pxt.String,
            "updated_at":    pxt.String,
        })
        print("✅ Created table: memory.chats")
    except Exception as e:
        print(f"ℹ️  memory.chats: {e}")

    # ── memory.projects ──────────────────────────────────────
    try:
        pxt.create_table("memory.projects", {
            "row_id":             pxt.String,
            "name":               pxt.String,
            "slug":               pxt.String,   # URL-safe identifier
            "description":        pxt.String,
            "status":             pxt.String,   # active, paused, completed
            "category":           pxt.String,
            "priority":           pxt.String,   # low, normal, high, critical
            "paths":              pxt.Json,     # file system paths
            "technologies":       pxt.Json,     # ["python", "rust", ...]
            "tags":               pxt.Json,
            "related_projects":   pxt.Json,     # ["slug1", "slug2"]
            "next_steps":         pxt.String,
            "notes":              pxt.String,
            "claude_project_id":  pxt.String,   # Claude.ai project UUID
            "created_at":         pxt.String,
            "updated_at":         pxt.String,
        })
        print("✅ Created table: memory.projects")
    except Exception as e:
        print(f"ℹ️  memory.projects: {e}")

    # ── memory.documents ─────────────────────────────────────
    try:
        pxt.create_table("memory.documents", {
            "row_id":       pxt.String,
            "path":         pxt.String,   # vault path or external URL
            "title":        pxt.String,
            "description":  pxt.String,
            "doc_type":     pxt.String,   # artifact, report, template, reference, external
            "projects":     pxt.Json,
            "tags":         pxt.Json,
            "source":       pxt.String,
            "created_at":   pxt.String,
            "updated_at":   pxt.String,
        })
        print("✅ Created table: memory.documents")
    except Exception as e:
        print(f"ℹ️  memory.documents: {e}")

    print("\n✅ Schema setup complete!")
    print("\nTables created:")
    for t_name in ["memory.memories", "memory.bookmarks", "memory.chats", 
                    "memory.projects", "memory.documents"]:
        try:
            t = pxt.get_table(t_name)
            cols = t.columns()
            print(f"  📋 {t_name}: {len(cols)} columns ({', '.join(cols)})")
        except Exception:
            print(f"  ❌ {t_name}: not found")


if __name__ == "__main__":
    create_schema()
