"""
Integrations MCP Server
========================
Provides MCP tools for external system integrations (EDI, email, APIs).

Tools:
- send_purchase_order_edi: Send purchase order via EDI transmission
- send_purchase_order_api: Send purchase order via supplier API
- send_purchase_order_email: Send purchase order via email
- send_email: Send notification email
- sync_amazon_prices: Sync product prices from Amazon API

Port: 3005
Endpoint: /mcp
"""

import os
import sys
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
import requests

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from database.config import get_db
from database.models import Product, PurchaseOrder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Integrations MCP Server",
    description="MCP tools for external system integrations",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Amazon API endpoint
AMAZON_API_URL = "https://amazon-api-app.purplepebble-8d2a2163.eastus.azurecontainerapps.io/products"


# ============================================================================
# MCP Protocol Models
# ============================================================================

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

INTEGRATION_TOOLS = [
    {
        "name": "send_purchase_order_edi",
        "description": "Send purchase order to supplier via EDI (Electronic Data Interchange)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "supplier": {
                    "type": "string",
                    "description": "Supplier ID or name"
                },
                "order_data": {
                    "type": "object",
                    "description": "Purchase order details",
                    "properties": {
                        "order_id": {"type": "string"},
                        "items": {"type": "array"},
                        "total": {"type": "number"},
                        "delivery_date": {"type": "string"}
                    }
                }
            },
            "required": ["supplier", "order_data"]
        }
    },
    {
        "name": "send_purchase_order_api",
        "description": "Send purchase order to supplier via their REST API",
        "inputSchema": {
            "type": "object",
            "properties": {
                "supplier": {
                    "type": "string",
                    "description": "Supplier ID or name"
                },
                "order_data": {
                    "type": "object",
                    "description": "Purchase order details"
                }
            },
            "required": ["supplier", "order_data"]
        }
    },
    {
        "name": "send_purchase_order_email",
        "description": "Send purchase order to supplier via email (PDF attachment)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "supplier": {
                    "type": "string",
                    "description": "Supplier ID or name"
                },
                "order_data": {
                    "type": "object",
                    "description": "Purchase order details"
                }
            },
            "required": ["supplier", "order_data"]
        }
    },
    {
        "name": "send_email",
        "description": "Send notification email to specified recipient",
        "inputSchema": {
            "type": "object",
            "properties": {
                "to": {
                    "type": "string",
                    "description": "Recipient email address"
                },
                "subject": {
                    "type": "string",
                    "description": "Email subject line"
                },
                "body": {
                    "type": "string",
                    "description": "Email body content"
                }
            },
            "required": ["to", "subject", "body"]
        }
    },
    {
        "name": "sync_amazon_prices",
        "description": "Sync product prices from Amazon API for specified products",
        "inputSchema": {
            "type": "object",
            "properties": {
                "sku_list": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of product ASINs to sync (optional, syncs all if not provided)"
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
    """Main MCP protocol endpoint."""
    method = request.method
    params = request.params or {}

    logger.info(f"MCP request: method={method}, params={params}")

    if method == "tools/list":
        return MCPListToolsResponse(
            tools=[MCPToolDefinition(**tool) for tool in INTEGRATION_TOOLS]
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

    if tool_name == "send_purchase_order_edi":
        supplier = arguments.get("supplier")
        order_data = arguments.get("order_data")

        # Placeholder EDI transmission
        # In production, integrate with EDI provider (Ariba, Coupa, etc.)
        logger.info(f"Sending EDI purchase order to {supplier}: {order_data}")

        return {
            "success": True,
            "method": "EDI",
            "supplier": supplier,
            "order_id": order_data.get("order_id"),
            "transmission_id": f"EDI-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "status": "transmitted",
            "timestamp": datetime.now().isoformat()
        }

    elif tool_name == "send_purchase_order_api":
        supplier = arguments.get("supplier")
        order_data = arguments.get("order_data")

        # Placeholder API call
        # In production, call actual supplier API
        logger.info(f"Sending API purchase order to {supplier}: {order_data}")

        return {
            "success": True,
            "method": "API",
            "supplier": supplier,
            "order_id": order_data.get("order_id"),
            "api_response": {
                "confirmation_number": f"API-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "status": "accepted"
            },
            "timestamp": datetime.now().isoformat()
        }

    elif tool_name == "send_purchase_order_email":
        supplier = arguments.get("supplier")
        order_data = arguments.get("order_data")

        # Placeholder email send
        # In production, integrate with email service (SendGrid, SES, etc.)
        logger.info(f"Sending email purchase order to {supplier}: {order_data}")

        return {
            "success": True,
            "method": "EMAIL",
            "supplier": supplier,
            "order_id": order_data.get("order_id"),
            "email_sent": True,
            "recipient": f"orders@{supplier}.com",
            "message_id": f"EMAIL-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "timestamp": datetime.now().isoformat()
        }

    elif tool_name == "send_email":
        to = arguments.get("to")
        subject = arguments.get("subject")
        body = arguments.get("body")

        # Placeholder email send
        logger.info(f"Sending email to {to}: {subject}")

        return {
            "success": True,
            "recipient": to,
            "subject": subject,
            "message_id": f"MSG-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "timestamp": datetime.now().isoformat()
        }

    elif tool_name == "sync_amazon_prices":
        sku_list = arguments.get("sku_list", None)

        # Get products to sync
        if sku_list:
            products = db.query(Product).filter(Product.asin.in_(sku_list)).all()
        else:
            products = db.query(Product).filter(Product.is_active == True).limit(50).all()

        synced_count = 0
        updated_count = 0
        errors = []

        for product in products:
            try:
                # Fetch price from Amazon API
                response = requests.get(f"{AMAZON_API_URL}/{product.asin}", timeout=5)

                if response.status_code == 200:
                    data = response.json()
                    new_price = data.get("price")

                    if new_price and new_price != product.price:
                        old_price = product.price
                        product.price = new_price
                        product.last_updated = datetime.now()
                        updated_count += 1

                        logger.info(f"Updated price for {product.asin}: ${old_price} -> ${new_price}")

                    synced_count += 1

            except Exception as e:
                logger.error(f"Error syncing {product.asin}: {e}")
                errors.append({
                    "sku": product.asin,
                    "error": str(e)
                })

        # Commit changes
        if updated_count > 0:
            db.commit()

        return {
            "total_products": len(products),
            "synced_successfully": synced_count,
            "prices_updated": updated_count,
            "errors": len(errors),
            "error_details": errors[:10],  # First 10 errors
            "timestamp": datetime.now().isoformat()
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
        "service": "integrations-mcp",
        "tools_count": len(INTEGRATION_TOOLS),
        "amazon_api_url": AMAZON_API_URL,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/")
async def root():
    """Root endpoint with server info."""
    return {
        "name": "Integrations MCP Server",
        "version": "1.0.0",
        "tools": len(INTEGRATION_TOOLS),
        "mcp_endpoint": "/mcp",
        "available_tools": [tool["name"] for tool in INTEGRATION_TOOLS]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3005)
