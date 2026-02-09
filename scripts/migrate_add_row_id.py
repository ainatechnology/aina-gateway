"""Schema Migration: Add row_id (UUID4) to all PixelMemory tables.

Run this script ONCE on the Mac where Pixeltable is installed.
It adds a `row_id` column to all 5 tables and backfills existing rows.

Usage:
    cd /Volumes/AINA/aina-gateway
    source .venv/bin/activate
    python scripts/migrate_add_row_id.py

What it does:
    1. Adds `row_id` (String) column to each table (if not exists)
    2. Backfills existing rows with generated UUID4 values
    3. Verifies all rows have unique row_ids

Safe to run multiple times (idempotent).

Fix v2: memory.memories uses created_at + memory_type instead of content match
        (content column has embedding index with 255 char limit for comparisons)
"""

import uuid
import pixeltable as pxt

TABLES = [
    "memory.memories",
    "memory.bookmarks",
    "memory.chats",
    "memory.projects",
    "memory.documents",
]


def migrate_table(table_name: str) -> dict:
    """Add row_id column and backfill existing rows for one table."""
    t = pxt.get_table(table_name)
    cols = t.columns()
    result = {"table": table_name, "had_column": False, "rows_backfilled": 0, "total_rows": 0}

    # Step 1: Add column if missing
    if "row_id" in cols:
        print(f"  ℹ️  {table_name}: row_id column already exists")
        result["had_column"] = True
    else:
        t.add_column(row_id=pxt.String)
        print(f"  ✅ {table_name}: row_id column added")

    # Step 2: Backfill rows that have no row_id
    rows = t.select(t.row_id).collect()
    total = len(rows)
    result["total_rows"] = total

    # Find rows without row_id (None or empty)
    needs_backfill = t.where(
        (t.row_id == None) | (t.row_id == "")
    ).collect()
    
    if len(needs_backfill) == 0:
        print(f"  ℹ️  {table_name}: all {total} rows already have row_id")
        return result

    backfill_count = 0
    
    if table_name == "memory.memories":
        # NOTE: content column has an embedding index with 255 char limit.
        # We use created_at + memory_type as composite key instead.
        # created_at is ISO timestamp (precise to second), combined with
        # memory_type this is effectively unique for sequential inserts.
        for row in needs_backfill:
            new_id = uuid.uuid4().hex[:16]
            t.where(
                (t.created_at == row["created_at"]) & (t.memory_type == row["memory_type"])
            ).update({"row_id": new_id})
            backfill_count += 1

    elif table_name == "memory.bookmarks":
        for row in needs_backfill:
            new_id = uuid.uuid4().hex[:16]
            t.where(
                (t.url == row["url"]) & (t.created_at == row["created_at"])
            ).update({"row_id": new_id})
            backfill_count += 1

    elif table_name == "memory.chats":
        for row in needs_backfill:
            new_id = uuid.uuid4().hex[:16]
            t.where(
                (t.chat_id == row["chat_id"]) & (t.created_at == row["created_at"])
            ).update({"row_id": new_id})
            backfill_count += 1

    elif table_name == "memory.projects":
        for row in needs_backfill:
            new_id = uuid.uuid4().hex[:16]
            t.where(
                (t.slug == row["slug"]) & (t.created_at == row["created_at"])
            ).update({"row_id": new_id})
            backfill_count += 1

    elif table_name == "memory.documents":
        for row in needs_backfill:
            new_id = uuid.uuid4().hex[:16]
            t.where(
                (t.path == row["path"]) & (t.created_at == row["created_at"])
            ).update({"row_id": new_id})
            backfill_count += 1

    result["rows_backfilled"] = backfill_count
    print(f"  ✅ {table_name}: backfilled {backfill_count} of {total} rows")
    return result


def verify_uniqueness(table_name: str) -> bool:
    """Verify all row_ids are unique and non-empty."""
    t = pxt.get_table(table_name)
    rows = t.select(t.row_id).collect()
    ids = [r["row_id"] for r in rows]
    
    # Check for None/empty
    empty = [i for i in ids if not i]
    if empty:
        print(f"  ⚠️  {table_name}: {len(empty)} rows still without row_id!")
        return False
    
    # Check uniqueness
    if len(ids) != len(set(ids)):
        print(f"  ⚠️  {table_name}: duplicate row_ids found!")
        return False
    
    print(f"  ✅ {table_name}: all {len(ids)} row_ids unique and non-empty")
    return True


def main():
    print("🚀 PixelMemory Schema Migration: Adding row_id to all tables\n")
    
    pxt.init()
    
    results = []
    for table_name in TABLES:
        print(f"\n📋 Migrating {table_name}...")
        try:
            result = migrate_table(table_name)
            results.append(result)
        except Exception as e:
            print(f"  ❌ {table_name}: Error - {e}")
            results.append({"table": table_name, "error": str(e)})

    print("\n\n🔍 Verification pass...\n")
    all_ok = True
    for table_name in TABLES:
        try:
            if not verify_uniqueness(table_name):
                all_ok = False
        except Exception as e:
            print(f"  ❌ {table_name}: Verification error - {e}")
            all_ok = False

    print("\n" + "=" * 60)
    if all_ok:
        print("✅ Migration complete! All tables have unique row_ids.")
    else:
        print("⚠️  Migration completed with warnings. Check output above.")
    
    print("\nSummary:")
    for r in results:
        if "error" in r:
            print(f"  ❌ {r['table']}: {r['error']}")
        else:
            print(f"  {'🔄' if r['rows_backfilled'] > 0 else '✅'} {r['table']}: "
                  f"{r['total_rows']} rows, {r['rows_backfilled']} backfilled")


if __name__ == "__main__":
    main()
