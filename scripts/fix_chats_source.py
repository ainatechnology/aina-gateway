"""Quick fix: Add missing 'source' column to memory.chats.

The chat_add tool sends a 'source' parameter, but the table was originally
created without this column. This adds it.

Usage:
    cd /Volumes/AINA/aina-gateway
    source .venv/bin/activate
    python scripts/fix_chats_source.py
"""

import pixeltable as pxt


def main():
    print("🔧 Fix: Adding 'source' column to memory.chats\n")

    pxt.init()

    t = pxt.get_table("memory.chats")
    cols = t.columns()

    if "source" in cols:
        print("ℹ️  'source' column already exists. Nothing to do.")
        return

    t.add_column(source=pxt.String)
    print("✅ 'source' column added to memory.chats")

    # Verify
    cols_after = t.columns()
    print(f"   Columns: {', '.join(cols_after)}")


if __name__ == "__main__":
    main()
