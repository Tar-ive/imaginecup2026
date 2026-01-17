#!/usr/bin/env python3
"""
Test script for MCP servers.
Validates that all servers are running and responding correctly.
"""

import requests
import sys
from typing import Dict, List

# MCP Server endpoints
MCP_SERVERS = {
    "Supplier Data": "http://localhost:3001",
    "Inventory Management": "http://localhost:3002",
    "Finance Data": "http://localhost:3003",
    "Analytics & Forecasting": "http://localhost:3004",
    "Integrations": "http://localhost:3005"
}


def test_health_endpoint(name: str, base_url: str) -> bool:
    """Test the /health endpoint of an MCP server."""
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ {name}: HEALTHY")
            print(f"   Service: {data.get('service')}")
            print(f"   Tools: {data.get('tools_count')}")
            return True
        else:
            print(f"❌ {name}: UNHEALTHY (status {response.status_code})")
            return False
    except Exception as e:
        print(f"❌ {name}: NOT REACHABLE - {e}")
        return False


def test_tools_list(name: str, base_url: str) -> bool:
    """Test the MCP tools/list endpoint."""
    try:
        response = requests.post(
            f"{base_url}/mcp",
            json={"method": "tools/list"},
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            tools = data.get("tools", [])
            print(f"✅ {name}: MCP tools/list works ({len(tools)} tools)")
            for tool in tools:
                print(f"   - {tool.get('name')}")
            return True
        else:
            print(f"❌ {name}: MCP tools/list failed (status {response.status_code})")
            return False
    except Exception as e:
        print(f"❌ {name}: MCP tools/list error - {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("MCP SERVERS TEST SUITE")
    print("=" * 60)
    print()

    results: Dict[str, Dict[str, bool]] = {}

    for name, base_url in MCP_SERVERS.items():
        print(f"\n🔍 Testing {name} ({base_url})")
        print("-" * 60)

        health_ok = test_health_endpoint(name, base_url)
        print()

        tools_ok = test_tools_list(name, base_url)
        print()

        results[name] = {
            "health": health_ok,
            "tools": tools_ok
        }

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    all_passed = True
    for name, result in results.items():
        status = "✅ PASS" if all(result.values()) else "❌ FAIL"
        print(f"{status} {name}")
        all_passed = all_passed and all(result.values())

    print()
    if all_passed:
        print("🎉 All MCP servers are working correctly!")
        sys.exit(0)
    else:
        print("⚠️  Some MCP servers have issues. Check logs above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
