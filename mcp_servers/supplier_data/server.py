"""
Supplier Data MCP Server
=========================
Provides MCP tools for supplier pricing, reliability, and comparison operations.

Tools:
- get_supplier_prices: Get current prices from a supplier for specific SKUs
- fuzzy_match_product: Match SKUs across different suppliers
- get_supplier_reliability: Get supplier quality and delivery metrics
- compare_suppliers: Rank suppliers by price, delivery, and quality
- get_alternative_suppliers: Find backup suppliers for a product
- get_supplier_payment_terms: Get payment terms for a supplier
- get_supplier_min_order: Get minimum order quantity requirements

Port: 3001
Endpoint: /mcp
"""

import os
import sys
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from database.config import get_db
from database.models import Supplier, Product
from services.supplier_service import SupplierService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Supplier Data MCP Server",
    description="MCP tools for supplier pricing and comparison",
    version="1.0.0"
)

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

SUPPLIER_TOOLS = [
    {
        "name": "get_supplier_prices",
        "description": "Get current prices from a specific supplier for a list of SKUs",
        "inputSchema": {
            "type": "object",
            "properties": {
                "supplier_name": {
                    "type": "string",
                    "description": "Supplier name or ID"
                },
                "sku_list": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of product SKUs/ASINs"
                }
            },
            "required": ["supplier_name", "sku_list"]
        }
    },
    {
        "name": "fuzzy_match_product",
        "description": "Match a product SKU across multiple suppliers using fuzzy matching on product titles",
        "inputSchema": {
            "type": "object",
            "properties": {
                "sku": {
                    "type": "string",
                    "description": "Product SKU/ASIN to match"
                },
                "suppliers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of supplier names/IDs to search (optional)"
                }
            },
            "required": ["sku"]
        }
    },
    {
        "name": "get_supplier_reliability",
        "description": "Get supplier quality and delivery performance metrics",
        "inputSchema": {
            "type": "object",
            "properties": {
                "supplier_name": {
                    "type": "string",
                    "description": "Supplier name or ID"
                }
            },
            "required": ["supplier_name"]
        }
    },
    {
        "name": "compare_suppliers",
        "description": "Compare suppliers for a specific product based on price, delivery time, and quality rating",
        "inputSchema": {
            "type": "object",
            "properties": {
                "sku": {
                    "type": "string",
                    "description": "Product SKU/ASIN"
                },
                "criteria": {
                    "type": "object",
                    "description": "Weighting criteria (default: price=50%, delivery=30%, quality=20%)",
                    "properties": {
                        "price_weight": {"type": "number", "default": 0.5},
                        "delivery_weight": {"type": "number", "default": 0.3},
                        "quality_weight": {"type": "number", "default": 0.2}
                    }
                }
            },
            "required": ["sku"]
        }
    },
    {
        "name": "get_alternative_suppliers",
        "description": "Find alternative suppliers for a product (backup suppliers)",
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
        "name": "get_supplier_payment_terms",
        "description": "Get payment terms and conditions for a supplier",
        "inputSchema": {
            "type": "object",
            "properties": {
                "supplier_name": {
                    "type": "string",
                    "description": "Supplier name or ID"
                }
            },
            "required": ["supplier_name"]
        }
    },
    {
        "name": "get_supplier_min_order",
        "description": "Get minimum order quantity requirements for a supplier and product",
        "inputSchema": {
            "type": "object",
            "properties": {
                "supplier_name": {
                    "type": "string",
                    "description": "Supplier name or ID"
                },
                "sku": {
                    "type": "string",
                    "description": "Product SKU/ASIN"
                }
            },
            "required": ["supplier_name", "sku"]
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
            tools=[MCPToolDefinition(**tool) for tool in SUPPLIER_TOOLS]
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

    supplier_service = SupplierService(db)

    if tool_name == "get_supplier_prices":
        supplier_name = arguments.get("supplier_name")
        sku_list = arguments.get("sku_list", [])

        # Find supplier
        supplier = db.query(Supplier).filter(
            (Supplier.supplier_name == supplier_name) | (Supplier.supplier_id == supplier_name)
        ).first()

        if not supplier:
            raise ValueError(f"Supplier not found: {supplier_name}")

        # Get prices for products
        prices = []
        for sku in sku_list:
            product = db.query(Product).filter(
                Product.asin == sku,
                Product.supplier_id == supplier.supplier_id
            ).first()

            if product:
                prices.append({
                    "sku": sku,
                    "price": float(product.price),
                    "available": True,
                    "lead_time_days": supplier.default_lead_time_days
                })
            else:
                prices.append({
                    "sku": sku,
                    "available": False
                })

        return {
            "supplier_id": supplier.supplier_id,
            "supplier_name": supplier.supplier_name,
            "prices": prices,
            "currency": "USD"
        }

    elif tool_name == "fuzzy_match_product":
        sku = arguments.get("sku")
        suppliers = arguments.get("suppliers", None)

        # Get the product to match
        product = db.query(Product).filter(Product.asin == sku).first()
        if not product:
            raise ValueError(f"Product not found: {sku}")

        # Find similar products (simple title matching)
        query = db.query(Product).filter(Product.asin != sku)
        if suppliers:
            query = query.join(Supplier).filter(Supplier.supplier_name.in_(suppliers))

        # Simple fuzzy match on title (would use proper fuzzy matching in production)
        matches = []
        for other_product in query.all():
            similarity = _calculate_title_similarity(product.title, other_product.title)
            if similarity > 0.7:  # 70% threshold
                matches.append({
                    "sku": other_product.asin,
                    "title": other_product.title,
                    "supplier": other_product.supplier_id,
                    "similarity_score": similarity,
                    "price": float(other_product.price)
                })

        return {
            "original_sku": sku,
            "original_title": product.title,
            "matches": sorted(matches, key=lambda x: x["similarity_score"], reverse=True)
        }

    elif tool_name == "get_supplier_reliability":
        supplier_name = arguments.get("supplier_name")

        performance = supplier_service.get_supplier_performance(supplier_name)
        if not performance:
            # Try by name
            supplier = db.query(Supplier).filter(Supplier.supplier_name == supplier_name).first()
            if supplier:
                performance = supplier_service.get_supplier_performance(supplier.supplier_id)

        if not performance:
            raise ValueError(f"Supplier not found: {supplier_name}")

        return {
            "supplier_id": performance["supplier_id"],
            "supplier_name": performance["supplier_name"],
            "on_time_delivery_rate": performance["on_time_delivery_rate"],
            "quality_rating": performance["quality_rating"],
            "total_orders": performance["total_orders"],
            "avg_order_value": performance["avg_order_value"],
            "reliability_score": (performance["on_time_delivery_rate"] + performance["quality_rating"]) / 2
        }

    elif tool_name == "compare_suppliers":
        sku = arguments.get("sku")
        criteria = arguments.get("criteria", {})

        price_weight = criteria.get("price_weight", 0.5)
        delivery_weight = criteria.get("delivery_weight", 0.3)
        quality_weight = criteria.get("quality_weight", 0.2)

        # Get product
        product = db.query(Product).filter(Product.asin == sku).first()
        if not product:
            raise ValueError(f"Product not found: {sku}")

        # Get all suppliers for this product (in reality, you'd match across suppliers)
        suppliers_data = []
        suppliers = db.query(Supplier).filter(Supplier.is_active == True).all()

        for supplier in suppliers:
            # Check if they have this product
            supplier_product = db.query(Product).filter(
                Product.supplier_id == supplier.supplier_id,
                Product.asin == sku
            ).first()

            if supplier_product:
                # Calculate composite score
                price_score = 1.0 / float(supplier_product.price) if supplier_product.price > 0 else 0
                delivery_score = 1.0 / supplier.default_lead_time_days if supplier.default_lead_time_days > 0 else 0
                quality_score = float(supplier.quality_rating or 0) / 5.0

                composite_score = (
                    price_weight * price_score +
                    delivery_weight * delivery_score +
                    quality_weight * quality_score
                )

                suppliers_data.append({
                    "supplier_id": supplier.supplier_id,
                    "supplier_name": supplier.supplier_name,
                    "price": float(supplier_product.price),
                    "lead_time_days": supplier.default_lead_time_days,
                    "quality_rating": float(supplier.quality_rating or 0),
                    "on_time_delivery_rate": float(supplier.on_time_delivery_rate or 0),
                    "composite_score": composite_score
                })

        return {
            "sku": sku,
            "suppliers": sorted(suppliers_data, key=lambda x: x["composite_score"], reverse=True),
            "criteria": {
                "price_weight": price_weight,
                "delivery_weight": delivery_weight,
                "quality_weight": quality_weight
            }
        }

    elif tool_name == "get_alternative_suppliers":
        sku = arguments.get("sku")

        # Get product
        product = db.query(Product).filter(Product.asin == sku).first()
        if not product:
            raise ValueError(f"Product not found: {sku}")

        # Get all other suppliers (excluding current supplier)
        alternatives = []
        all_suppliers = db.query(Supplier).filter(
            Supplier.is_active == True,
            Supplier.supplier_id != product.supplier_id
        ).all()

        for supplier in all_suppliers:
            alternatives.append({
                "supplier_id": supplier.supplier_id,
                "supplier_name": supplier.supplier_name,
                "quality_rating": float(supplier.quality_rating or 0),
                "on_time_delivery_rate": float(supplier.on_time_delivery_rate or 0),
                "lead_time_days": supplier.default_lead_time_days,
                "payment_terms": supplier.payment_terms
            })

        return {
            "sku": sku,
            "current_supplier": product.supplier_id,
            "alternatives": alternatives,
            "count": len(alternatives)
        }

    elif tool_name == "get_supplier_payment_terms":
        supplier_name = arguments.get("supplier_name")

        supplier = db.query(Supplier).filter(
            (Supplier.supplier_name == supplier_name) | (Supplier.supplier_id == supplier_name)
        ).first()

        if not supplier:
            raise ValueError(f"Supplier not found: {supplier_name}")

        return {
            "supplier_id": supplier.supplier_id,
            "supplier_name": supplier.supplier_name,
            "payment_terms": supplier.payment_terms,
            "default_lead_time_days": supplier.default_lead_time_days,
            "contact_email": supplier.email,
            "contact_phone": supplier.phone
        }

    elif tool_name == "get_supplier_min_order":
        supplier_name = arguments.get("supplier_name")
        sku = arguments.get("sku")

        supplier = db.query(Supplier).filter(
            (Supplier.supplier_name == supplier_name) | (Supplier.supplier_id == supplier_name)
        ).first()

        if not supplier:
            raise ValueError(f"Supplier not found: {supplier_name}")

        # In a real system, you'd have MOQ per product
        # For now, return a placeholder
        return {
            "supplier_id": supplier.supplier_id,
            "supplier_name": supplier.supplier_name,
            "sku": sku,
            "minimum_order_quantity": 10,  # Placeholder
            "unit": "units"
        }

    else:
        raise ValueError(f"Unknown tool: {tool_name}")


def _calculate_title_similarity(title1: str, title2: str) -> float:
    """Simple title similarity calculation (placeholder for real fuzzy matching)."""
    words1 = set(title1.lower().split())
    words2 = set(title2.lower().split())

    if not words1 or not words2:
        return 0.0

    intersection = words1.intersection(words2)
    union = words1.union(words2)

    return len(intersection) / len(union) if union else 0.0


# ============================================================================
# Health Check
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "supplier-data-mcp",
        "tools_count": len(SUPPLIER_TOOLS),
        "timestamp": datetime.now().isoformat()
    }


@app.get("/")
async def root():
    """Root endpoint with server info."""
    return {
        "name": "Supplier Data MCP Server",
        "version": "1.0.0",
        "tools": len(SUPPLIER_TOOLS),
        "mcp_endpoint": "/mcp",
        "available_tools": [tool["name"] for tool in SUPPLIER_TOOLS]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3001)
