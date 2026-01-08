"""MCP Tool Configuration for Supply Chain Agents."""

from typing import Literal, TypedDict, Dict, Any

from agents.config import settings

# MCP Server Names
McpServerName = Literal[
    "supplier-data",
    "inventory-mgmt",
    "finance-data",
    "analytics-forecast",
    "integrations",
]

MCP_API_HTTP_PATH = "/mcp"


class MCPServerConfig(TypedDict):
    """MCP Server Configuration."""

    url: str
    type: Literal["http", "sse"]
    verbose: bool


class MCPServerDefinition(TypedDict):
    """MCP Server Definition."""

    config: MCPServerConfig
    id: McpServerName
    name: str


def get_mcp_tools_config() -> Dict[McpServerName, MCPServerDefinition]:
    """
    Get MCP tools configuration for supply chain servers.

    Returns:
        Dictionary mapping server names to their configurations
    """
    return {
        "supplier-data": {
            "config": {
                "url": f"{settings.mcp_supplier_url}{MCP_API_HTTP_PATH}",
                "type": "http",
                "verbose": True,
            },
            "id": "supplier-data",
            "name": "Supplier Data",
        },
        "inventory-mgmt": {
            "config": {
                "url": f"{settings.mcp_inventory_url}{MCP_API_HTTP_PATH}",
                "type": "http",
                "verbose": True,
            },
            "id": "inventory-mgmt",
            "name": "Inventory Management",
        },
        "finance-data": {
            "config": {
                "url": f"{settings.mcp_finance_url}{MCP_API_HTTP_PATH}",
                "type": "http",
                "verbose": True,
            },
            "id": "finance-data",
            "name": "Finance Data",
        },
        "analytics-forecast": {
            "config": {
                "url": f"{settings.mcp_analytics_url}{MCP_API_HTTP_PATH}",
                "type": "http",
                "verbose": True,
            },
            "id": "analytics-forecast",
            "name": "Analytics & Forecasting",
        },
        "integrations": {
            "config": {
                "url": f"{settings.mcp_integrations_url}{MCP_API_HTTP_PATH}",
                "type": "http",
                "verbose": True,
            },
            "id": "integrations",
            "name": "Integrations",
        },
    }


# Export singleton instance
MCP_TOOLS_CONFIG = get_mcp_tools_config()
