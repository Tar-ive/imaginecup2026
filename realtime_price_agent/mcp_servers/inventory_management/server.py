"""
Inventory Management MCP Server
================================
Provides MCP tools for inventory and stock management operations.

Tools:
- get_product_details: Get detailed product information
- get_inventory_levels: Get current stock levels
- get_sales_velocity: Calculate sales rate over time period
- predict_stockout: Predict days until stockout
- update_inventory: Update stock levels
- get_historical_sales: Get past sales data
- get_low_stock_products: Get products needing reorder

Port: 3002
Endpoint: /mcp
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

# Add parent directory to path to import from main app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from database.config import get_db
from database.models import Product
from services.inventory_service import InventoryService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Inventory Management MCP Server",
    description="MCP tools for inventory and stock management",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# MCP Protocol Models
# ============================================================================

class MCPToolCall(BaseModel):
    """MCP tool call request."""
    name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)


class MCPRequest(BaseModel):
    """MCP protocol request."""
    method: str
    params: Optional[Dict[str, Any]] = None


class MCPToolDefinition(BaseModel):
    """MCP tool definition."""
    name: str
    description: str
    inputSchema: Dict[str, Any]


class MCPListToolsResponse(BaseModel):
    """Response for list_tools."""
    tools: List[MCPToolDefinition]


class MCPCallToolResponse(BaseModel):
    """Response for call_tool."""
    content: List[Dict[str, Any]]
    isError: bool = False


# ============================================================================
# Tool Definitions
# ============================================================================

INVENTORY_TOOLS = [
    {
        "name": "get_product_details",
        "description": "Get detailed information about a product including title, price, stock levels, and supplier info",
        "inputSchema": {
            "type": "object",
            "properties": {
                "sku": {
                    "type": "string",
                    "description": "Product SKU/ASIN"
                }
            },
            "required": ["sku"]
        }
    },
    {
        "name": "get_inventory_levels",
        "description": "Get current stock levels for a product",
        "inputSchema": {
            "type": "object",
            "properties": {
                "sku": {
                    "type": "string",
                    "description": "Product SKU/ASIN"
                }
            },
            "required": ["sku"]
        }
    },
    {
        "name": "get_sales_velocity",
        "description": "Calculate the sales velocity (units per day) for a product over a specified time period",
        "inputSchema": {
            "type": "object",
            "properties": {
                "sku": {
                    "type": "string",
                    "description": "Product SKU/ASIN"
                },
                "days": {
                    "type": "integer",
                    "description": "Number of days to analyze (default: 30)",
                    "default": 30
                }
            },
            "required": ["sku"]
        }
    },
    {
        "name": "predict_stockout",
        "description": "Predict number of days until product stockout based on current stock and sales velocity",
        "inputSchema": {
            "type": "object",
            "properties": {
                "sku": {
                    "type": "string",
                    "description": "Product SKU/ASIN"
                }
            },
            "required": ["sku"]
        }
    },
    {
        "name": "update_inventory",
        "description": "Update inventory levels for a product",
        "inputSchema": {
            "type": "object",
            "properties": {
                "sku": {
                    "type": "string",
                    "description": "Product SKU/ASIN"
                },
                "quantity": {
                    "type": "integer",
                    "description": "Quantity to add (positive) or remove (negative)"
                },
                "type": {
                    "type": "string",
                    "description": "Type of update: 'sale', 'restock', 'adjustment'",
                    "enum": ["sale", "restock", "adjustment"]
                }
            },
            "required": ["sku", "quantity", "type"]
        }
    },
    {
        "name": "get_historical_sales",
        "description": "Get historical sales data for a product over a date range",
        "inputSchema": {
            "type": "object",
            "properties": {
                "sku": {
                    "type": "string",
                    "description": "Product SKU/ASIN"
                },
                "start_date": {
                    "type": "string",
                    "description": "Start date in YYYY-MM-DD format"
                },
                "end_date": {
                    "type": "string",
                    "description": "End date in YYYY-MM-DD format"
                }
            },
            "required": ["sku", "start_date", "end_date"]
        }
    },
    {
        "name": "get_low_stock_products",
        "description": "Get list of products with stock levels below their reorder point",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of products to return (default: 50)",
                    "default": 50
                }
            }
        }
    }
]


# ============================================================================
# MCP Endpoints
# ============================================================================

@app.post("/mcp")
async def mcp_endpoint(request: MCPRequest, db: Session = Depends(get_db)):
    """
    Main MCP protocol endpoint.
    Handles both list_tools and call_tool methods.
    """
    method = request.method
    params = request.params or {}

    logger.info(f"MCP request: method={method}, params={params}")

    if method == "tools/list":
        return MCPListToolsResponse(
            tools=[MCPToolDefinition(**tool) for tool in INVENTORY_TOOLS]
        )

    elif method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        try:
            result = await execute_tool(tool_name, arguments, db)
            return MCPCallToolResponse(
                content=[{
                    "type": "text",
                    "text": str(result)
                }],
                isError=False
            )
        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            return MCPCallToolResponse(
                content=[{
                    "type": "text",
                    "text": f"Error: {str(e)}"
                }],
                isError=True
            )

    else:
        raise HTTPException(status_code=400, detail=f"Unknown method: {method}")


# ============================================================================
# Tool Implementations
# ============================================================================

async def execute_tool(tool_name: str, arguments: Dict[str, Any], db: Session) -> Dict[str, Any]:
    """Execute a tool and return the result."""

    inventory_service = InventoryService(db)

    if tool_name == "get_product_details":
        sku = arguments.get("sku")
        product = db.query(Product).filter(Product.asin == sku).first()
        if not product:
            raise ValueError(f"Product not found: {sku}")

        return {
            "sku": product.asin,
            "title": product.title,
            "price": float(product.price),
            "stock_level": product.stock_level,
            "reorder_point": product.reorder_point,
            "supplier_id": product.supplier_id,
            "last_updated": product.last_updated.isoformat() if product.last_updated else None
        }

    elif tool_name == "get_inventory_levels":
        sku = arguments.get("sku")
        product = db.query(Product).filter(Product.asin == sku).first()
        if not product:
            raise ValueError(f"Product not found: {sku}")

        return {
            "sku": sku,
            "current_stock": product.stock_level,
            "reorder_point": product.reorder_point,
            "needs_reorder": product.stock_level <= product.reorder_point,
            "units_below_reorder": max(0, product.reorder_point - product.stock_level)
        }

    elif tool_name == "get_sales_velocity":
        sku = arguments.get("sku")
        days = arguments.get("days", 30)

        # Calculate sales velocity from order history
        # For now, use a simple calculation based on stock changes
        product = db.query(Product).filter(Product.asin == sku).first()
        if not product:
            raise ValueError(f"Product not found: {sku}")

        # Placeholder calculation - you'd want to query actual order history
        velocity = 2.5  # units per day (placeholder)

        return {
            "sku": sku,
            "period_days": days,
            "units_per_day": velocity,
            "units_per_week": velocity * 7,
            "units_per_month": velocity * 30
        }

    elif tool_name == "predict_stockout":
        sku = arguments.get("sku")
        product = db.query(Product).filter(Product.asin == sku).first()
        if not product:
            raise ValueError(f"Product not found: {sku}")

        # Simple stockout prediction based on velocity
        velocity = 2.5  # units per day (placeholder)
        days_until_stockout = product.stock_level / velocity if velocity > 0 else 999

        return {
            "sku": sku,
            "current_stock": product.stock_level,
            "sales_velocity": velocity,
            "days_until_stockout": round(days_until_stockout, 1),
            "stockout_date": (datetime.now() + timedelta(days=days_until_stockout)).isoformat(),
            "critical": days_until_stockout < 7
        }

    elif tool_name == "update_inventory":
        sku = arguments.get("sku")
        quantity = arguments.get("quantity")
        update_type = arguments.get("type")

        product = db.query(Product).filter(Product.asin == sku).first()
        if not product:
            raise ValueError(f"Product not found: {sku}")

        old_stock = product.stock_level
        product.stock_level += quantity
        product.last_updated = datetime.now()
        db.commit()

        return {
            "sku": sku,
            "update_type": update_type,
            "quantity_change": quantity,
            "old_stock": old_stock,
            "new_stock": product.stock_level,
            "timestamp": datetime.now().isoformat()
        }

    elif tool_name == "get_historical_sales":
        sku = arguments.get("sku")
        start_date = arguments.get("start_date")
        end_date = arguments.get("end_date")

        # Placeholder - you'd query actual order history from database
        return {
            "sku": sku,
            "start_date": start_date,
            "end_date": end_date,
            "total_units_sold": 175,
            "average_daily_sales": 2.5,
            "data_points": []  # Would contain daily sales data
        }

    elif tool_name == "get_low_stock_products":
        limit = arguments.get("limit", 50)
        low_stock = inventory_service.get_low_stock_products(limit=limit)

        return {
            "count": len(low_stock),
            "products": [
                {
                    "sku": p.asin,
                    "title": p.title,
                    "stock_level": p.stock_level,
                    "reorder_point": p.reorder_point,
                    "shortfall": p.reorder_point - p.stock_level
                }
                for p in low_stock
            ]
        }

    else:
        raise ValueError(f"Unknown tool: {tool_name}")


# ============================================================================
# Health Check
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "inventory-management-mcp",
        "tools_count": len(INVENTORY_TOOLS),
        "timestamp": datetime.now().isoformat()
    }


@app.get("/")
async def root():
    """Root endpoint with server info."""
    return {
        "name": "Inventory Management MCP Server",
        "version": "1.0.0",
        "tools": len(INVENTORY_TOOLS),
        "mcp_endpoint": "/mcp",
        "available_tools": [tool["name"] for tool in INVENTORY_TOOLS]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3002)
