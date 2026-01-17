"""
Finance Data MCP Server
========================
Provides MCP tools for financial calculations, cash management, cost analysis,
and AP2 payment mandate creation.

Existing Tools:
- get_cash_position: Get current available cash and financial capacity
- calculate_margin_impact: Calculate profit impact of price changes
- get_product_cost_structure: Get detailed cost breakdown for a product
- calculate_payment_terms_value: Calculate NPV of payment terms
- get_accounts_payable: Get outstanding payment obligations
- convert_currency: Convert amounts between currencies

NEW AP2 Payment Tools:
- create_payment_mandate: Create AP2 payment mandate with cryptographic signature
- verify_payment_mandate: Verify AP2 mandate signature and validity
- execute_payment_with_mandate: Execute payment using verified mandate

Port: 3003
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
from sqlalchemy import func

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from database.config import get_db
from database.models import Product, PurchaseOrder
from services.ap2_service import AP2Service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Finance Data MCP Server",
    description="MCP tools for financial calculations and cost analysis",
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

FINANCE_TOOLS = [
    {
        "name": "get_cash_position",
        "description": "Get current cash position and available purchasing capacity",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "calculate_margin_impact",
        "description": "Calculate profit margin impact of price changes for products",
        "inputSchema": {
            "type": "object",
            "properties": {
                "price_changes": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "sku": {"type": "string"},
                            "old_price": {"type": "number"},
                            "new_price": {"type": "number"}
                        }
                    },
                    "description": "List of price changes"
                },
                "products": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of product SKUs to analyze"
                }
            },
            "required": ["price_changes"]
        }
    },
    {
        "name": "get_product_cost_structure",
        "description": "Get detailed cost breakdown for a product (COGS, overhead, shipping, etc.)",
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
        "name": "calculate_payment_terms_value",
        "description": "Calculate Net Present Value (NPV) of payment terms",
        "inputSchema": {
            "type": "object",
            "properties": {
                "amount": {
                    "type": "number",
                    "description": "Payment amount"
                },
                "terms": {
                    "type": "string",
                    "description": "Payment terms (e.g., 'Net 30', '2/10 Net 30')"
                }
            },
            "required": ["amount", "terms"]
        }
    },
    {
        "name": "get_accounts_payable",
        "description": "Get outstanding payment obligations and upcoming due dates",
        "inputSchema": {
            "type": "object",
            "properties": {
                "days_ahead": {
                    "type": "integer",
                    "description": "Number of days ahead to look (default: 30)",
                    "default": 30
                }
            }
        }
    },
    {
        "name": "convert_currency",
        "description": "Convert amount between currencies using current exchange rates",
        "inputSchema": {
            "type": "object",
            "properties": {
                "amount": {
                    "type": "number",
                    "description": "Amount to convert"
                },
                "from_currency": {
                    "type": "string",
                    "description": "Source currency code (e.g., USD, EUR)"
                },
                "to_currency": {
                    "type": "string",
                    "description": "Target currency code"
                }
            },
            "required": ["amount", "from_currency", "to_currency"]
        }
    },
    # ===== AP2 PAYMENT MANDATE TOOLS =====
    {
        "name": "create_payment_mandate",
        "description": "Create AP2 payment mandate with cryptographic signature for secure agent-led payment",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Negotiation session ID (optional, for linking)"
                },
                "supplier_id": {
                    "type": "string",
                    "description": "Supplier/merchant ID"
                },
                "amount": {
                    "type": "number",
                    "description": "Payment amount",
                    "minimum": 0
                },
                "currency": {
                    "type": "string",
                    "default": "USD",
                    "description": "Currency code"
                },
                "order_details": {
                    "type": "object",
                    "description": "Order line items and metadata"
                },
                "user_consent": {
                    "type": "boolean",
                    "description": "User has provided consent for this payment (REQUIRED)"
                }
            },
            "required": ["supplier_id", "amount", "order_details", "user_consent"]
        }
    },
    {
        "name": "verify_payment_mandate",
        "description": "Verify the cryptographic signature and validity of an AP2 payment mandate",
        "inputSchema": {
            "type": "object",
            "properties": {
                "mandate_id": {
                    "type": "string",
                    "description": "Payment mandate ID"
                },
                "merchant_authorization": {
                    "type": "string",
                    "description": "Merchant's signed authorization response (optional)"
                }
            },
            "required": ["mandate_id"]
        }
    },
    {
        "name": "execute_payment_with_mandate",
        "description": "Execute payment using a verified AP2 mandate",
        "inputSchema": {
            "type": "object",
            "properties": {
                "mandate_id": {
                    "type": "string",
                    "description": "Payment mandate ID"
                },
                "po_number": {
                    "type": "string",
                    "description": "Purchase order number to link"
                }
            },
            "required": ["mandate_id", "po_number"]
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
            tools=[MCPToolDefinition(**tool) for tool in FINANCE_TOOLS]
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

    if tool_name == "get_cash_position":
        # Placeholder - in production, integrate with accounting system
        total_pending_orders = db.query(func.sum(PurchaseOrder.total_cost)).filter(
            PurchaseOrder.status.in_(['pending', 'approved'])
        ).scalar() or 0

        return {
            "available_cash": 500000.00,  # Placeholder
            "committed_cash": float(total_pending_orders),
            "uncommitted_cash": 500000.00 - float(total_pending_orders),
            "credit_limit": 100000.00,
            "total_capacity": 600000.00 - float(total_pending_orders),
            "currency": "USD",
            "as_of": datetime.now().isoformat()
        }

    elif tool_name == "calculate_margin_impact":
        price_changes = arguments.get("price_changes", [])

        total_impact = 0
        product_impacts = []

        for change in price_changes:
            sku = change.get("sku")
            old_price = change.get("old_price")
            new_price = change.get("new_price")

            product = db.query(Product).filter(Product.asin == sku).first()
            if not product:
                continue

            # Assuming 40% markup on cost (placeholder)
            estimated_cost = float(old_price) * 0.6
            old_margin = old_price - estimated_cost
            new_margin = new_price - estimated_cost

            margin_change = new_margin - old_margin
            margin_change_pct = (margin_change / old_margin * 100) if old_margin > 0 else 0

            # Estimate annual volume (placeholder)
            annual_volume = 365 * 2.5  # units per year

            annual_impact = margin_change * annual_volume
            total_impact += annual_impact

            product_impacts.append({
                "sku": sku,
                "title": product.title,
                "old_price": old_price,
                "new_price": new_price,
                "estimated_cost": estimated_cost,
                "old_margin": round(old_margin, 2),
                "new_margin": round(new_margin, 2),
                "margin_change": round(margin_change, 2),
                "margin_change_pct": round(margin_change_pct, 2),
                "annual_impact": round(annual_impact, 2)
            })

        return {
            "products_analyzed": len(product_impacts),
            "total_annual_impact": round(total_impact, 2),
            "currency": "USD",
            "product_impacts": product_impacts
        }

    elif tool_name == "get_product_cost_structure":
        sku = arguments.get("sku")

        product = db.query(Product).filter(Product.asin == sku).first()
        if not product:
            raise ValueError(f"Product not found: {sku}")

        # Placeholder cost structure (in production, get from ERP/accounting system)
        unit_price = float(product.price)
        cogs = unit_price * 0.50  # 50% COGS
        overhead = unit_price * 0.10  # 10% overhead
        shipping = unit_price * 0.08  # 8% shipping
        margin = unit_price * 0.32  # 32% margin

        return {
            "sku": sku,
            "title": product.title,
            "unit_price": unit_price,
            "cost_breakdown": {
                "cogs": round(cogs, 2),
                "overhead": round(overhead, 2),
                "shipping": round(shipping, 2),
                "total_cost": round(cogs + overhead + shipping, 2)
            },
            "margin": round(margin, 2),
            "margin_percentage": round((margin / unit_price * 100), 2),
            "currency": "USD"
        }

    elif tool_name == "calculate_payment_terms_value":
        amount = arguments.get("amount")
        terms = arguments.get("terms")

        # Simple NPV calculation
        # Assumes 10% annual discount rate
        discount_rate_annual = 0.10

        if "Net 30" in terms:
            days = 30
            if "2/10" in terms:
                # 2% discount if paid in 10 days
                early_payment_discount = amount * 0.02
                early_npv = (amount - early_payment_discount) / (1 + (discount_rate_annual * 10 / 365))
                standard_npv = amount / (1 + (discount_rate_annual * 30 / 365))

                return {
                    "amount": amount,
                    "terms": terms,
                    "early_payment_option": {
                        "days": 10,
                        "discount_pct": 2.0,
                        "discount_amount": round(early_payment_discount, 2),
                        "net_amount": round(amount - early_payment_discount, 2),
                        "npv": round(early_npv, 2)
                    },
                    "standard_payment": {
                        "days": 30,
                        "amount": amount,
                        "npv": round(standard_npv, 2)
                    },
                    "recommendation": "Take early payment discount" if early_npv < standard_npv else "Pay on standard terms"
                }
            else:
                npv = amount / (1 + (discount_rate_annual * days / 365))
                return {
                    "amount": amount,
                    "terms": terms,
                    "payment_days": days,
                    "npv": round(npv, 2)
                }
        else:
            # Default to immediate payment
            return {
                "amount": amount,
                "terms": terms,
                "payment_days": 0,
                "npv": amount
            }

    elif tool_name == "get_accounts_payable":
        days_ahead = arguments.get("days_ahead", 30)

        # Get pending orders
        cutoff_date = datetime.now() + timedelta(days=days_ahead)
        pending_orders = db.query(PurchaseOrder).filter(
            PurchaseOrder.status.in_(['pending', 'approved']),
            PurchaseOrder.order_date <= cutoff_date
        ).all()

        payables = []
        total_due = 0

        for order in pending_orders:
            # Estimate due date (30 days from order)
            due_date = order.order_date + timedelta(days=30)
            days_until_due = (due_date - datetime.now()).days

            payables.append({
                "order_id": order.order_id,
                "supplier_id": order.supplier_id,
                "amount": float(order.total_cost),
                "order_date": order.order_date.isoformat(),
                "due_date": due_date.isoformat(),
                "days_until_due": days_until_due,
                "overdue": days_until_due < 0
            })

            total_due += float(order.total_cost)

        return {
            "days_ahead": days_ahead,
            "total_payables": len(payables),
            "total_amount_due": round(total_due, 2),
            "overdue_count": len([p for p in payables if p["overdue"]]),
            "payables": sorted(payables, key=lambda x: x["days_until_due"]),
            "currency": "USD"
        }

    elif tool_name == "convert_currency":
        amount = arguments.get("amount")
        from_currency = arguments.get("from_currency")
        to_currency = arguments.get("to_currency")

        # Placeholder exchange rates (in production, use live API)
        exchange_rates = {
            "USD": 1.0,
            "EUR": 0.85,
            "GBP": 0.73,
            "JPY": 110.0,
            "CAD": 1.25
        }

        if from_currency not in exchange_rates or to_currency not in exchange_rates:
            raise ValueError(f"Unsupported currency: {from_currency} or {to_currency}")

        # Convert through USD
        usd_amount = amount / exchange_rates[from_currency]
        converted_amount = usd_amount * exchange_rates[to_currency]

        return {
            "original_amount": amount,
            "original_currency": from_currency,
            "converted_amount": round(converted_amount, 2),
            "target_currency": to_currency,
            "exchange_rate": round(exchange_rates[to_currency] / exchange_rates[from_currency], 4),
            "timestamp": datetime.now().isoformat()
        }

    # ===== AP2 PAYMENT MANDATE TOOLS =====
    elif tool_name == "create_payment_mandate":
        ap2_service = AP2Service(db)

        session_id = arguments.get("session_id")
        supplier_id = arguments.get("supplier_id")
        amount = arguments.get("amount")
        currency = arguments.get("currency", "USD")
        order_details = arguments.get("order_details")
        user_consent = arguments.get("user_consent", False)

        result = ap2_service.create_mandate(
            supplier_id=supplier_id,
            amount=amount,
            currency=currency,
            order_details=order_details,
            session_id=session_id,
            user_consent=user_consent
        )

        return result

    elif tool_name == "verify_payment_mandate":
        ap2_service = AP2Service(db)

        mandate_id = arguments.get("mandate_id")
        merchant_authorization = arguments.get("merchant_authorization")

        result = ap2_service.verify_mandate(
            mandate_id=mandate_id,
            merchant_authorization=merchant_authorization
        )

        return result

    elif tool_name == "execute_payment_with_mandate":
        ap2_service = AP2Service(db)

        mandate_id = arguments.get("mandate_id")
        po_number = arguments.get("po_number")

        result = ap2_service.execute_payment(
            mandate_id=mandate_id,
            po_number=po_number
        )

        return result

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
        "service": "finance-data-mcp",
        "tools_count": len(FINANCE_TOOLS),
        "timestamp": datetime.now().isoformat()
    }


@app.get("/")
async def root():
    """Root endpoint with server info."""
    return {
        "name": "Finance Data MCP Server",
        "version": "1.0.0",
        "tools": len(FINANCE_TOOLS),
        "mcp_endpoint": "/mcp",
        "available_tools": [tool["name"] for tool in FINANCE_TOOLS]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3003)
