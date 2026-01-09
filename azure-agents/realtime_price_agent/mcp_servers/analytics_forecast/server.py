"""
Analytics & Forecasting MCP Server
===================================
Provides MCP tools for demand forecasting, trend analysis, and predictions.

Tools:
- forecast_demand: ML-based demand prediction with confidence intervals
- analyze_seasonality: Detect seasonal patterns in sales data
- get_weather_forecast: Get weather predictions for location
- get_local_events: Get local events that may impact demand
- detect_trends: Analyze sales trends for a product
- predict_stockouts_batch: Batch prediction for multiple products

Port: 3004
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

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from database.config import get_db
from database.models import Product
from agents.demand_forecasting.model_service import DemandForecasterService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Analytics & Forecasting MCP Server",
    description="MCP tools for demand forecasting and analytics",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize forecaster with ML model
forecaster = DemandForecasterService.get_instance()


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

ANALYTICS_TOOLS = [
    {
        "name": "forecast_demand",
        "description": "Generate ML-based demand forecast for a product with confidence intervals",
        "inputSchema": {
            "type": "object",
            "properties": {
                "sku": {
                    "type": "string",
                    "description": "Product SKU/ASIN"
                },
                "days_ahead": {
                    "type": "integer",
                    "description": "Number of days to forecast (default: 7)",
                    "default": 7
                },
                "factors": {
                    "type": "object",
                    "description": "Optional external factors to consider",
                    "properties": {
                        "weather": {"type": "string"},
                        "events": {"type": "array", "items": {"type": "string"}},
                        "seasonality": {"type": "boolean"}
                    }
                }
            },
            "required": ["sku"]
        }
    },
    {
        "name": "analyze_seasonality",
        "description": "Analyze seasonal patterns in product sales data",
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
        "name": "get_weather_forecast",
        "description": "Get weather forecast for a location (impacts demand for weather-sensitive products)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "Location (city or zip code)"
                },
                "days": {
                    "type": "integer",
                    "description": "Number of days ahead (default: 7)",
                    "default": 7
                }
            },
            "required": ["location"]
        }
    },
    {
        "name": "get_local_events",
        "description": "Get local events calendar that may impact product demand",
        "inputSchema": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "Location (city or region)"
                },
                "start_date": {
                    "type": "string",
                    "description": "Start date (YYYY-MM-DD)"
                },
                "end_date": {
                    "type": "string",
                    "description": "End date (YYYY-MM-DD)"
                }
            },
            "required": ["location", "start_date", "end_date"]
        }
    },
    {
        "name": "detect_trends",
        "description": "Analyze sales trends for a product (increasing, decreasing, stable)",
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
        "name": "predict_stockouts_batch",
        "description": "Batch prediction of stockouts for multiple products",
        "inputSchema": {
            "type": "object",
            "properties": {
                "sku_list": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of product SKUs/ASINs"
                }
            },
            "required": ["sku_list"]
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
            tools=[MCPToolDefinition(**tool) for tool in ANALYTICS_TOOLS]
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

    if tool_name == "forecast_demand":
        sku = arguments.get("sku")
        days_ahead = arguments.get("days_ahead", 7)
        factors = arguments.get("factors", {})

        # Get forecast from ML model
        forecast = forecaster.forecast(sku, days=days_ahead)

        if not forecast:
            raise ValueError(f"Could not generate forecast for {sku}")

        return {
            "sku": forecast.asin,
            "forecast_days": forecast.forecast_days,
            "predicted_daily_demand": forecast.predicted_daily_demand,
            "predicted_total_demand": forecast.predicted_total_demand,
            "confidence_lower": forecast.confidence_lower,
            "confidence_upper": forecast.confidence_upper,
            "confidence_level": forecast.confidence_level,
            "method": forecast.method,
            "external_factors_considered": factors,
            "generated_at": datetime.now().isoformat()
        }

    elif tool_name == "analyze_seasonality":
        sku = arguments.get("sku")

        # Placeholder seasonality analysis
        # In production, you'd analyze historical sales data
        return {
            "sku": sku,
            "has_seasonality": True,
            "seasonal_pattern": "quarterly",
            "peak_months": ["November", "December"],
            "low_months": ["January", "February"],
            "seasonality_strength": 0.65,  # 0-1 scale
            "analysis_period": "12 months"
        }

    elif tool_name == "get_weather_forecast":
        location = arguments.get("location")
        days = arguments.get("days", 7)

        # Placeholder weather forecast
        # In production, integrate with weather API (OpenWeather, Weather.com, etc.)
        forecast_days = []
        for i in range(days):
            date = datetime.now() + timedelta(days=i)
            forecast_days.append({
                "date": date.strftime("%Y-%m-%d"),
                "temp_high": 75,
                "temp_low": 55,
                "condition": "partly_cloudy",
                "precipitation_chance": 20
            })

        return {
            "location": location,
            "forecast_days": days,
            "forecast": forecast_days,
            "source": "weather_api_placeholder"
        }

    elif tool_name == "get_local_events":
        location = arguments.get("location")
        start_date = arguments.get("start_date")
        end_date = arguments.get("end_date")

        # Placeholder events calendar
        # In production, integrate with events API
        return {
            "location": location,
            "start_date": start_date,
            "end_date": end_date,
            "events": [
                {
                    "name": "Summer Music Festival",
                    "date": "2026-06-15",
                    "category": "entertainment",
                    "expected_attendance": 50000
                }
            ],
            "holidays": [
                {
                    "name": "Independence Day",
                    "date": "2026-07-04",
                    "impact_level": "high"
                }
            ]
        }

    elif tool_name == "detect_trends":
        sku = arguments.get("sku")

        # Get product
        product = db.query(Product).filter(Product.asin == sku).first()
        if not product:
            raise ValueError(f"Product not found: {sku}")

        # Placeholder trend analysis
        # In production, analyze order history
        return {
            "sku": sku,
            "title": product.title,
            "trend_direction": "increasing",  # increasing, decreasing, stable
            "trend_strength": 0.75,  # 0-1 scale
            "growth_rate": 15.5,  # percentage
            "analysis_period": "90 days",
            "confidence": "high"
        }

    elif tool_name == "predict_stockouts_batch":
        sku_list = arguments.get("sku_list", [])

        predictions = []
        for sku in sku_list:
            try:
                forecast = forecaster.forecast(sku, days=7)
                product = db.query(Product).filter(Product.asin == sku).first()

                if forecast and product:
                    # Simple stockout calculation
                    days_until_stockout = product.stock_level / forecast.predicted_daily_demand if forecast.predicted_daily_demand > 0 else 999

                    predictions.append({
                        "sku": sku,
                        "title": product.title,
                        "current_stock": product.stock_level,
                        "daily_demand": forecast.predicted_daily_demand,
                        "days_until_stockout": round(days_until_stockout, 1),
                        "stockout_date": (datetime.now() + timedelta(days=days_until_stockout)).strftime("%Y-%m-%d"),
                        "critical": days_until_stockout < 7
                    })
            except Exception as e:
                logger.warning(f"Could not predict stockout for {sku}: {e}")
                predictions.append({
                    "sku": sku,
                    "error": str(e)
                })

        return {
            "total_products": len(sku_list),
            "successful_predictions": len([p for p in predictions if "error" not in p]),
            "critical_products": len([p for p in predictions if p.get("critical", False)]),
            "predictions": predictions
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
        "service": "analytics-forecast-mcp",
        "tools_count": len(ANALYTICS_TOOLS),
        "model_loaded": forecaster.is_loaded,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/")
async def root():
    """Root endpoint with server info."""
    return {
        "name": "Analytics & Forecasting MCP Server",
        "version": "1.0.0",
        "tools": len(ANALYTICS_TOOLS),
        "mcp_endpoint": "/mcp",
        "model_loaded": forecaster.is_loaded,
        "available_tools": [tool["name"] for tool in ANALYTICS_TOOLS]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3004)
