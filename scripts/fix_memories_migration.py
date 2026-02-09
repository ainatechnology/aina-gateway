"""Fix migration for memory.memories: Export → Drop → Recreate with row_id → Re-import.

The row-by-row update approach failed because multiple memories share the same
created_at + memory_type combination, causing duplicate row_ids.

This script:
1. Exports all rows from memory.memories to JSON backup
2. Drops the table
3. Recreates it with row_id as first column
4. Re-imports all rows with unique row_ids
5. Verifies row count and uniqueness

Usage:
    cd /Volumes/AINA/aina-gateway
    source .venv/bin/activate
    python scripts/fix_memories_migration.py
"""

import json
import uuid
from pathlib import Path

import pixeltable as pxt

BACKUP_PATH = Path("scripts/memories_backup.json")


def main():
    print("🔧 Fix migration: memory.memories\n")

    pxt.init()

    # ── Step 1: Export ────────────────────────────────────────
    print("📤 Step 1: Exporting all rows...")
    t = pxt.get_table("memory.memories")
    
    # Get all columns except row_id (which has duplicates)
    rows = t.collect()
    exported = []
    for row in rows:
        entry = {
            "content":     row.get("content", ""),
            "memory_type": row.get("memory_type", "note"),
            "projects":    row.get("projects", []),
            "tags":        row.get("tags", []),
            "source":      row.get("source", ""),
            "created_at":  row.get("created_at", ""),
            "updated_at":  row.get("updated_at", ""),
        }
        exported.append(entry)

    # Save backup
    BACKUP_PATH.parent.mkdir(parents=True, exist_ok=True)
    BACKUP_PATH.write_text(
        json.dumps(exported, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"   ✅ Exported {len(exported)} rows to {BACKUP_PATH}")

    # ── Step 2: Drop table ────────────────────────────────────
    print("\n🗑️  Step 2: Dropping memory.memories...")
    pxt.drop_table("memory.memories")
    print("   ✅ Table dropped")

    # ── Step 3: Recreate with row_id ──────────────────────────
    print("\n📋 Step 3: Recreating memory.memories with row_id...")
    pxt.create_table("memory.memories", {
        "row_id":      pxt.String,
        "content":     pxt.String,
        "memory_type": pxt.String,
        "projects":    pxt.Json,
        "tags":        pxt.Json,
        "source":      pxt.String,
        "created_at":  pxt.String,
        "updated_at":  pxt.String,
    })
    print("   ✅ Table recreated")

    # ── Step 4: Re-import with unique row_ids ─────────────────
    print(f"\n📥 Step 4: Re-importing {len(exported)} rows with unique row_ids...")
    t = pxt.get_table("memory.memories")

    import_rows = []
    for entry in exported:
        entry["row_id"] = uuid.uuid4().hex[:16]
        import_rows.append(entry)

    t.insert(import_rows)
    print(f"   ✅ Inserted {len(import_rows)} rows")

    # ── Step 5: Verify ────────────────────────────────────────
    print("\n🔍 Step 5: Verification...")
    rows = t.select(t.row_id).collect()
    ids = [r["row_id"] for r in rows]

    count_ok = len(ids) == len(exported)
    empty = [i for i in ids if not i]
    unique = len(ids) == len(set(ids))

    print(f"   Row count: {len(ids)} (expected {len(exported)}) {'✅' if count_ok else '❌'}")
    print(f"   Empty row_ids: {len(empty)} {'✅' if not empty else '❌'}")
    print(f"   Unique row_ids: {'✅' if unique else '❌ DUPLICATES FOUND'}")

    print("\n" + "=" * 60)
    if count_ok and not empty and unique:
        print("✅ memory.memories migration complete! All rows have unique row_ids.")
        print(f"\n   Backup saved at: {BACKUP_PATH}")
    else:
        print("❌ Migration has issues. Backup available for recovery.")
        print(f"   Backup: {BACKUP_PATH}")


if __name__ == "__main__":
    main()
