"""Test script for aina-gateway - run while server is active."""

import asyncio
import json
import sys
import traceback

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


GATEWAY_URL = "http://127.0.0.1:8008/mcp"


async def call_tool(session, name, args):
    """Call a tool and handle errors gracefully."""
    try:
        result = await session.call_tool(name, args)
        # Check for error in result
        if result.isError:
            print(f"   ⚠️  Tool returned error: {result.content[0].text}")
            return None
        return json.loads(result.content[0].text)
    except Exception as e:
        print(f"   ❌ Exception: {type(e).__name__}: {e}")
        traceback.print_exc()
        return None


async def test_gateway():
    """Connect to the running gateway and exercise all tools."""
    print(f"Connecting to {GATEWAY_URL} ...")

    async with streamablehttp_client(GATEWAY_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("✅ Connected and initialized\n")

            # List tools
            tools = await session.list_tools()
            tool_names = [t.name for t in tools.tools]
            print(f"📋 Available tools ({len(tool_names)}): {', '.join(tool_names)}\n")

            # Test: get_schema
            print("── get_schema ──")
            data = await call_tool(session, "get_schema", {"table_name": "memory.memories"})
            if data:
                print(f"   Columns: {list(data['columns'].keys())}\n")

            # Test: memory_list
            print("── memory_list ──")
            data = await call_tool(session, "memory_list", {"limit": 3})
            if data:
                print(f"   Got {len(data)} memories")
                if data:
                    content = data[0].get('content', '')
                    print(f"   First: {content[:80]}...\n")

            # Test: memory_search
            print("── memory_search ──")
            data = await call_tool(session, "memory_search", {"query": "aina", "limit": 3})
            if data:
                print(f"   Found {len(data)} results for 'aina'\n")

            # Test: bookmark_list
            print("── bookmark_list ──")
            data = await call_tool(session, "bookmark_list", {"limit": 3})
            if data:
                print(f"   Got {len(data)} bookmarks\n")

            # Test: bookmark_search
            print("── bookmark_search ──")
            data = await call_tool(session, "bookmark_search", {"query": "github", "limit": 3})
            if data:
                print(f"   Found {len(data)} results for 'github'\n")

            # Test: memory_add
            print("── memory_add ──")
            data = await call_tool(session, "memory_add", {
                "content": "Gateway-Test: aina-gateway Phase 1 erfolgreich getestet",
                "memory_type": "status",
                "projects": ["aina-gateway"],
                "tags": ["test", "gateway"],
                "source": "test-script",
            })
            if data:
                print(f"   Status: {data.get('status')}\n")

            print("✅ All tests completed!")


if __name__ == "__main__":
    try:
        asyncio.run(test_gateway())
    except ConnectionRefusedError:
        print(f"❌ Cannot connect to {GATEWAY_URL}")
        print("   Is the gateway running? Start with: python -m src.server")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")
        traceback.print_exc()
        sys.exit(1)
