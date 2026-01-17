"""
Supplier Data MCP Server
=========================
Provides MCP tools for supplier pricing, reliability, comparison operations,
and automated price negotiation.

Existing Tools:
- get_supplier_prices: Get current prices from a supplier for specific SKUs
- fuzzy_match_product: Match SKUs across different suppliers
- get_supplier_reliability: Get supplier quality and delivery metrics
- compare_suppliers: Rank suppliers by price, delivery, and quality
- get_alternative_suppliers: Find backup suppliers for a product
- get_supplier_payment_terms: Get payment terms for a supplier
- get_supplier_min_order: Get minimum order quantity requirements

NEW Negotiation Tools:
- create_negotiation_session: Create a new negotiation session
- request_supplier_quote: Request a quote from a supplier
- submit_counter_offer: Submit a counter-offer to a supplier
- accept_supplier_offer: Accept the current offer and close negotiation
- get_negotiation_status: Get current status of all negotiations
- compare_negotiation_offers: Compare and rank current offers

Port: 3001
Endpoint: /mcp
"""

import os
import sys
import json
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
from services.negotiation_service import NegotiationService

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
    },
    # ===== NEGOTIATION TOOLS =====
    {
        "name": "create_negotiation_session",
        "description": "Create a new negotiation session to negotiate pricing with suppliers",
        "inputSchema": {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "description": "List of items to negotiate pricing for",
                    "items": {
                        "type": "object",
                        "properties": {
                            "sku": {"type": "string", "description": "Product SKU/ASIN"},
                            "quantity": {"type": "integer", "minimum": 1},
                            "description": {"type": "string"}
                        },
                        "required": ["sku", "quantity"]
                    }
                },
                "target_price": {
                    "type": "number",
                    "description": "Target unit price to negotiate toward (optional)"
                },
                "target_discount_percent": {
                    "type": "number",
                    "description": "Target discount percentage from current price (optional)"
                },
                "max_rounds": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 5,
                    "default": 3,
                    "description": "Maximum negotiation rounds"
                },
                "supplier_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of supplier IDs to negotiate with (optional, defaults to all active)"
                }
            },
            "required": ["items"]
        }
    },
    {
        "name": "request_supplier_quote",
        "description": "Request a quote from a supplier for items in a negotiation session (simulated instant response)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Negotiation session ID"
                },
                "supplier_id": {
                    "type": "string",
                    "description": "Supplier ID to request quote from"
                },
                "urgency": {
                    "type": "string",
                    "enum": ["low", "medium", "high"],
                    "default": "medium",
                    "description": "Urgency level for supplier response"
                }
            },
            "required": ["session_id", "supplier_id"]
        }
    },
    {
        "name": "submit_counter_offer",
        "description": "Submit a counter-offer to a supplier in response to their quote (simulated response)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Negotiation session ID"
                },
                "supplier_id": {
                    "type": "string",
                    "description": "Supplier ID to counter-offer"
                },
                "counter_price": {
                    "type": "number",
                    "description": "Counter-offer unit price",
                    "minimum": 0
                },
                "justification": {
                    "type": "string",
                    "description": "Reason for counter-offer (e.g., 'Competitor quoted 10% less', 'Target budget constraint')"
                }
            },
            "required": ["session_id", "supplier_id", "counter_price", "justification"]
        }
    },
    {
        "name": "accept_supplier_offer",
        "description": "Accept the current offer from a supplier and close the negotiation",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Negotiation session ID"
                },
                "supplier_id": {
                    "type": "string",
                    "description": "Supplier ID whose offer to accept"
                },
                "notes": {
                    "type": "string",
                    "description": "Optional notes about the acceptance decision"
                }
            },
            "required": ["session_id", "supplier_id"]
        }
    },
    {
        "name": "get_negotiation_status",
        "description": "Get current status and all rounds of negotiation for a session",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Negotiation session ID"
                }
            },
            "required": ["session_id"]
        }
    },
    {
        "name": "compare_negotiation_offers",
        "description": "Compare all current offers in a negotiation session and rank suppliers",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Negotiation session ID"
                },
                "criteria": {
                    "type": "string",
                    "enum": ["price", "quality_adjusted", "total_cost"],
                    "default": "total_cost",
                    "description": "Comparison criteria"
                }
            },
            "required": ["session_id"]
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
                    "text": json.dumps(result, default=str)
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

    # ===== NEGOTIATION TOOLS =====
    elif tool_name == "create_negotiation_session":
        negotiation_service = NegotiationService(db)

        items = arguments.get("items")
        target_price = arguments.get("target_price")
        target_discount_percent = arguments.get("target_discount_percent")
        max_rounds = arguments.get("max_rounds", 3)
        supplier_ids = arguments.get("supplier_ids")

        result = negotiation_service.create_session(
            items=items,
            target_price=target_price,
            target_discount_percent=target_discount_percent,
            max_rounds=max_rounds,
            supplier_ids=supplier_ids,
            created_by="NegotiationAgent"
        )

        return result

    elif tool_name == "request_supplier_quote":
        negotiation_service = NegotiationService(db)

        session_id = arguments.get("session_id")
        supplier_id = arguments.get("supplier_id")
        urgency = arguments.get("urgency", "medium")

        result = negotiation_service.request_quote(
            session_id=session_id,
            supplier_id=supplier_id,
            urgency=urgency
        )

        return result

    elif tool_name == "submit_counter_offer":
        negotiation_service = NegotiationService(db)

        session_id = arguments.get("session_id")
        supplier_id = arguments.get("supplier_id")
        counter_price = arguments.get("counter_price")
        justification = arguments.get("justification")

        result = negotiation_service.submit_counter(
            session_id=session_id,
            supplier_id=supplier_id,
            counter_price=counter_price,
            justification=justification
        )

        return result

    elif tool_name == "accept_supplier_offer":
        negotiation_service = NegotiationService(db)

        session_id = arguments.get("session_id")
        supplier_id = arguments.get("supplier_id")
        notes = arguments.get("notes")

        result = negotiation_service.accept_offer(
            session_id=session_id,
            supplier_id=supplier_id,
            notes=notes
        )

        return result

    elif tool_name == "get_negotiation_status":
        negotiation_service = NegotiationService(db)

        session_id = arguments.get("session_id")

        result = negotiation_service.get_status(session_id=session_id)

        return result

    elif tool_name == "compare_negotiation_offers":
        negotiation_service = NegotiationService(db)

        session_id = arguments.get("session_id")
        criteria = arguments.get("criteria", "total_cost")

        result = negotiation_service.compare_offers(
            session_id=session_id,
            criteria=criteria
        )

        return result

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
