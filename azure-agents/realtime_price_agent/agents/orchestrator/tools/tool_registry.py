"""Tool registry for managing MCP server connections.

This module provides a centralized registry for MCP tool servers,
using Microsoft Agent Framework's built-in MCPStreamableHTTPTool.
"""

import asyncio
import logging
from typing import Optional, Any, Dict

try:
    from agent_framework import MCPStreamableHTTPTool
except ImportError:
    raise ImportError(
        "Microsoft Agent Framework SDK is required. Install with: pip install agent-framework>=1.0.0b251001"
    )

from .tool_config import MCP_TOOLS_CONFIG, McpServerName

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Registry for managing MCP tool server metadata.

    Stores metadata about MCP servers. Each agent creates its own
    MCPStreamableHTTPTool instances and manages their lifecycle using
    async context managers, following Microsoft Agent Framework best practices.
    """

    def __init__(self) -> None:
        """Initialize the tool registry with server metadata."""
        self._server_metadata: Dict[str, Dict[str, Any]] = {}
        self._initialize_metadata()
        logger.info("MCP tool registry initialized")

    def _initialize_metadata(self) -> None:
        """Initialize server metadata from configuration."""
        for server_id, server_def in MCP_TOOLS_CONFIG.items():
            config = server_def["config"]
            name = server_def["name"]

            self._server_metadata[server_id] = {
                "id": server_id,
                "name": name,
                "url": config["url"],
                "type": config.get("type", "http"),
                "selected": True,
            }

            logger.info(f"Registered MCP server '{name}' ({server_id}) at {config['url']}")

        logger.info(f"Tool registry ready with {len(self._server_metadata)} MCP servers")

    def create_mcp_tool(self, server_id: McpServerName) -> Optional[MCPStreamableHTTPTool]:
        """Create a new MCP tool instance for a server.

        Args:
            server_id: The ID of the MCP server

        Returns:
            New MCPStreamableHTTPTool instance or None if server not found
        """
        metadata = self._server_metadata.get(server_id)
        if not metadata:
            logger.warning(f"MCP server '{server_id}' not found in registry")
            return None

        return MCPStreamableHTTPTool(
            name=metadata["name"],
            url=metadata["url"],
            headers=None,
            load_tools=True,
            load_prompts=False,
            request_timeout=30,
            approval_mode="never_require",
        )

    def get_server_metadata(self, server_id: McpServerName) -> Optional[Dict[str, Any]]:
        """Get metadata for a server without creating a connection.

        Args:
            server_id: The ID of the MCP server

        Returns:
            Server metadata dictionary or None if not found
        """
        return self._server_metadata.get(server_id)

    async def list_tools(self) -> Dict[str, Any]:
        """List all available MCP tools with reachability checks.

        Returns:
            Dictionary with tools array for frontend consumption
        """

        async def check_server(server_id: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
            """Check if MCP server is reachable and list its tools."""
            server_info = {
                "id": server_id,
                "name": metadata["name"],
                "url": metadata["url"],
                "type": metadata["type"],
                "reachable": False,
                "selected": metadata["selected"],
                "tools": [],
            }

            try:
                mcp_tool = self.create_mcp_tool(server_id)
                if not mcp_tool:
                    return server_info

                async with mcp_tool:
                    server_info["reachable"] = True

                    if hasattr(mcp_tool, "_tools") and mcp_tool._tools:
                        tools_list = []
                        for tool in mcp_tool._tools:
                            tool_info = {
                                "name": tool.metadata.name if hasattr(tool, "metadata") else str(tool),
                                "description": tool.metadata.description if hasattr(tool, "metadata") else "",
                            }
                            tools_list.append(tool_info)
                        server_info["tools"] = tools_list

            except Exception as error:
                logger.warning(f"MCP server {metadata['name']} not reachable: {error}")
                server_info["error"] = str(error)

            return server_info

        # Check all servers concurrently
        tasks = [
            asyncio.create_task(check_server(server_id, metadata))
            for server_id, metadata in self._server_metadata.items()
        ]

        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=10.0,
            )
        except asyncio.TimeoutError:
            logger.warning("Tool list timeout - returning partial results")
            results = []

        tools_list = [r for r in results if isinstance(r, dict)]

        return {"tools": tools_list}

    async def close_all(self) -> None:
        """Cleanup resources."""
        logger.info("Cleaning up tool registry...")
        self._server_metadata.clear()
        logger.info("Tool registry cleaned up")


# Global tool registry instance
tool_registry = ToolRegistry()
