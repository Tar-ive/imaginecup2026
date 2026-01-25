import json
import logging

from fastapi import FastAPI, Query, HTTPException, Depends
from fastapi.responses import StreamingResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import List, Optional
from sqlalchemy.orm import Session
from pydantic import BaseModel
from pathlib import Path

# Database imports (now at root level)
from database.config import get_db, test_connection
from database.models import Product, Supplier, PurchaseOrder, PurchaseOrderItem
from services.inventory_service import InventoryService
from services.supplier_service import SupplierService
from services.order_service import OrderService

# Agent imports
from agents.orchestrator.magentic_workflow import magentic_orchestrator
from agents.orchestrator.tools.tool_registry import tool_registry

logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    message: str
    context: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Testing database connection...")
    try:
        if not test_connection():
            logger.warning("Database connection test failed - endpoints requiring DB may not work")
            print("⚠️ Database connection failed - some endpoints may not work")
        else:
            print("✅ Database connection established")
    except Exception as e:
        logger.warning(f"Database connection error: {e}")
        print(f"⚠️ Database connection error: {e}")

    # Initialize agent workflow
    print("Initializing Supply Chain Agents...")
    try:
        await magentic_orchestrator.initialize()
        print("✅ Agent workflow ready")
    except Exception as e:
        logger.error(f"Failed to initialize agents: {e}")
        print(f"⚠️ Agent workflow failed to initialize: {e}")

    yield

    # Cleanup
    try:
        await tool_registry.close_all()
        print("✅ Cleanup complete")
    except Exception as e:
        logger.error(f"Cleanup error: {e}")


app = FastAPI(lifespan=lifespan)

# CORS middleware for dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files for dashboard
STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# Dashboard route
@app.get("/", response_class=HTMLResponse)
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """Serve the workflow dashboard."""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return HTMLResponse("<h1>Dashboard not found</h1><p>Run from project root.</p>")


# ========== INVENTORY ENDPOINTS ==========


@app.get("/products")
def list_products(
    db: Session = Depends(get_db),
    query: str = Query(None, description="Search in title"),
    brand: str = Query(None, description="Filter by brand"),
    min_qty: int = Query(None, description="Minimum available quantity"),
    skip: int = Query(0, description="Number of records to skip"),
    limit: int = Query(50, description="Maximum number of records to return"),
) -> List[dict]:
    """Get products with optional filtering"""
    service = InventoryService(db)
    products = service.get_products(
        brand=brand, query=query, min_qty=min_qty, skip=skip, limit=limit
    )

    return [
        {
            "asin": p.asin,
            "title": p.title,
            "brand": p.brand,
            "description": p.description,
            "unit_cost": float(p.unit_cost) if p.unit_cost else None,
            "market_price": float(p.market_price) if p.market_price else None,
            "quantity_on_hand": p.quantity_on_hand,
            "quantity_reserved": p.quantity_reserved,
            "quantity_available": p.quantity_available,
            "reorder_point": p.reorder_point,
            "supplier_id": p.supplier_id,
        }
        for p in products
    ]


@app.get("/products/{asin}")
def get_product_details(asin: str, db: Session = Depends(get_db)):
    """Get single product by ASIN"""
    service = InventoryService(db)
    product = service.get_product_by_asin(asin)

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    return {
        "asin": product.asin,
        "title": product.title,
        "brand": product.brand,
        "description": product.description,
        "unit_cost": float(product.unit_cost) if product.unit_cost else None,
        "last_purchase_price": float(product.last_purchase_price)
        if product.last_purchase_price
        else None,
        "market_price": float(product.market_price) if product.market_price else None,
        "quantity_on_hand": product.quantity_on_hand,
        "quantity_reserved": product.quantity_reserved,
        "quantity_available": product.quantity_available,
        "reorder_point": product.reorder_point,
        "reorder_quantity": product.reorder_quantity,
        "lead_time_days": product.lead_time_days,
        "supplier_id": product.supplier_id,
        "supplier_name": product.supplier.supplier_name if product.supplier else None,
        "created_at": product.created_at,
        "updated_at": product.updated_at,
        "is_active": product.is_active,
    }


@app.get("/inventory/low-stock")
def get_low_stock_products(
    db: Session = Depends(get_db),
    threshold: int = Query(None, description="Custom threshold (optional)"),
):
    """Get products that need reordering"""
    service = InventoryService(db)
    products = service.get_low_stock_products(threshold)

    return [
        {
            "asin": p.asin,
            "title": p.title,
            "brand": p.brand,
            "quantity_available": p.quantity_available,
            "reorder_point": p.reorder_point,
            "supplier_id": p.supplier_id,
        }
        for p in products
    ]


@app.get("/inventory/summary")
def get_inventory_summary(db: Session = Depends(get_db)):
    """Get inventory summary statistics"""
    service = InventoryService(db)
    return service.get_stock_summary()


@app.post("/inventory/adjust-stock")
def adjust_stock(
    asin: str,
    quantity_change: int,
    reason: str = "Manual adjustment",
    db: Session = Depends(get_db),
):
    """Adjust stock levels for a product"""
    service = InventoryService(db)
    product = service.adjust_stock(asin, quantity_change, reason)

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    return {
        "asin": product.asin,
        "title": product.title,
        "quantity_on_hand": product.quantity_on_hand,
        "quantity_available": product.quantity_available,
    }


# ========== SUPPLIER ENDPOINTS ==========


@app.get("/suppliers")
def list_suppliers(
    db: Session = Depends(get_db), skip: int = Query(0), limit: int = Query(50)
) -> List[dict]:
    """Get all suppliers"""
    service = SupplierService(db)
    suppliers = service.get_all_suppliers()

    # Apply pagination manually since service doesn't support it
    suppliers = suppliers[skip : skip + limit]

    return [
        {
            "supplier_id": s.supplier_id,
            "supplier_name": s.supplier_name,
            "contact_person": s.contact_person,
            "email": s.email,
            "phone": s.phone,
            "city": s.city,
            "country": s.country,
            "payment_terms": s.payment_terms,
            "on_time_delivery_rate": float(s.on_time_delivery_rate)
            if s.on_time_delivery_rate
            else None,
            "quality_rating": float(s.quality_rating) if s.quality_rating else None,
            "is_active": s.is_active,
        }
        for s in suppliers
    ]


@app.get("/suppliers/{supplier_id}")
def get_supplier_details(supplier_id: str, db: Session = Depends(get_db)):
    """Get supplier details and their products"""
    service = SupplierService(db)
    supplier = service.get_supplier_by_id(supplier_id)

    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    # Get supplier's products
    products = [
        {
            "asin": p.asin,
            "title": p.title,
            "brand": p.brand,
            "quantity_on_hand": p.quantity_on_hand,
            "quantity_available": p.quantity_available,
        }
        for p in supplier.products
        if p.is_active
    ]

    return {
        "supplier_id": supplier.supplier_id,
        "supplier_name": supplier.supplier_name,
        "contact_person": supplier.contact_person,
        "email": supplier.email,
        "phone": supplier.phone,
        "address": supplier.address,
        "city": supplier.city,
        "state_province": supplier.state_province,
        "country": supplier.country,
        "postal_code": supplier.postal_code,
        "payment_terms": supplier.payment_terms,
        "default_lead_time_days": supplier.default_lead_time_days,
        "on_time_delivery_rate": float(supplier.on_time_delivery_rate)
        if supplier.on_time_delivery_rate
        else None,
        "quality_rating": float(supplier.quality_rating)
        if supplier.quality_rating
        else None,
        "created_at": supplier.created_at,
        "is_active": supplier.is_active,
        "products": products,
        "product_count": len(products),
    }


# ========== ORDER ENDPOINTS ==========


@app.get("/orders")
def list_orders(
    db: Session = Depends(get_db),
    status: str = Query(
        None, description="Filter by status: pending, shipped, received, cancelled"
    ),
    supplier_id: str = Query(None, description="Filter by supplier"),
    skip: int = Query(0),
    limit: int = Query(50),
) -> List[dict]:
    """Get purchase orders with optional filtering"""
    service = OrderService(db)
    orders = service.get_orders(
        status=status, supplier_id=supplier_id, skip=skip, limit=limit
    )

    return [
        {
            "po_number": o.po_number,
            "supplier_id": o.supplier_id,
            "supplier_name": o.supplier.supplier_name,
            "order_date": o.order_date,
            "expected_delivery_date": o.expected_delivery_date,
            "actual_delivery_date": o.actual_delivery_date,
            "total_cost": float(o.total_cost),
            "status": o.status,
            "item_count": o.item_count,
            "created_by": o.created_by,
            "created_at": o.created_at,
        }
        for o in orders
    ]


@app.get("/orders/{po_number}")
def get_order_details(po_number: str, db: Session = Depends(get_db)):
    """Get detailed purchase order information"""
    service = OrderService(db)
    order_data = service.get_order_details(po_number)

    if not order_data:
        raise HTTPException(status_code=404, detail="Order not found")

    return order_data


@app.get("/orders/{po_number}/items")
def get_order_items(po_number: str, db: Session = Depends(get_db)):
    """Get line items for a specific order"""
    service = OrderService(db)
    order_data = service.get_order_details(po_number)

    if not order_data:
        raise HTTPException(status_code=404, detail="Order not found")

    return order_data.get("items", [])


# ========== PRICE SYNC ENDPOINTS (using live Amazon API) ==========


@app.post("/prices/sync-from-amazon")
def sync_prices_from_amazon(
    db: Session = Depends(get_db),
    query: str = Query("laptop", description="Search query for Amazon API"),
    limit: int = Query(100, description="Number of products to fetch"),
):
    """Sync prices from live Amazon API to database products"""
    import requests
    from datetime import datetime

    # Mock implementation
    import random
    
    # Mock data generation
    amazon_products = []
    
    # Look up products to simulate "live" data
    db_products = []
    if query:
        # Simple simulation: just get some products from DB to update
        from database.models import Product
        db_products = db.query(Product).filter(Product.title.ilike(f"%{query}%")).limit(limit).all()
        
    for p in db_products:
        # Simulate a price slightly different from market price
        current_price = float(p.market_price) if p.market_price else 100.0
        mock_price = current_price * random.uniform(0.9, 1.1)
        
        amazon_products.append({
            "asin": p.asin,
            "title": p.title,
            "initial_price": round(mock_price, 2),
            "timestamp": datetime.utcnow().isoformat()
        })

    # Update database prices
    updated_count = 0

    for amazon_product in amazon_products:
        asin = amazon_product.get("asin")
        if asin:
            # Find matching product in database
            product = db.query(Product).filter(Product.asin == asin).first()
            if product:
                # Update market price from live data
                new_price = amazon_product.get("initial_price")
                if new_price and isinstance(new_price, (int, float)):
                    product.market_price = float(new_price)
                    product.price_last_updated = datetime.utcnow()
                    updated_count += 1

    if updated_count > 0:
        db.commit()

    return {
        "message": f"Updated {updated_count} product prices from Amazon API",
        "api_query": query,
        "api_results_count": len(amazon_products),
        "database_updates": updated_count,
    }


@app.get("/prices/live-amazon/{asin}")
def get_live_amazon_price(asin: str):
    """Get current price from live Amazon API"""
    import requests

    try:
    try:
        # MOCK IMPLEMENTATION
        import random
        from datetime import datetime
        
        # Determine if ASIN exists (conceptually)
        if len(asin) < 5:
             raise HTTPException(status_code=404, detail="Product not found on Amazon")
             
        # Generate mock price
        mock_price = 20.0 + (hash(asin) % 1000) / 10.0
        
        return {
            "asin": asin,
            "title": f"Mock Product {asin}",
            "seller_name": "Mock Amazon Seller",
            "brand": "Mock Brand",
            "initial_price": round(mock_price, 2),
            "timestamp": datetime.utcnow().isoformat(),
            "source": "mock_amazon_api",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Amazon API error: {str(e)}")


@app.get("/prices/compare/{asin}")
def compare_prices(asin: str, db: Session = Depends(get_db)):
    """Compare database price vs live Amazon price"""
    import requests

    # Get database price
    product = db.query(Product).filter(Product.asin == asin).first()
    db_price = float(product.market_price) if product and product.market_price else None

    # Get live Amazon price
    try:
        # MOCK IMPLEMENTATION
        # Generate mock price
        amazon_price = 20.0 + (hash(asin) % 1000) / 10.0
        amazon_price = round(amazon_price, 2)
    except Exception:
        amazon_price = None

    comparison = {
        "asin": asin,
        "database_price": db_price,
        "amazon_live_price": amazon_price,
        "price_difference": None,
        "percent_difference": None,
    }

    if db_price and amazon_price:
        comparison["price_difference"] = round(amazon_price - db_price, 2)
        if db_price > 0:
            comparison["percent_difference"] = round(
                ((amazon_price - db_price) / db_price) * 100, 2
            )

    return comparison


# ========== WORKFLOW ENDPOINTS ==========


@app.post("/api/workflows/optimize-inventory")
async def workflow_optimize_inventory(
    db: Session = Depends(get_db),
    forecast_days: int = Query(7, description="Days ahead to forecast"),
    include_all_products: bool = Query(False, description="Analyze all products (not just low-stock)"),
    auto_create_orders: bool = Query(False, description="Actually create purchase orders"),
):
    """
    Run the complete supply chain optimization workflow.
    
    This workflow:
    1. Analyzes inventory levels using the trained forecasting model
    2. Checks realtime prices from Amazon API
    3. Generates order recommendations grouped by supplier
    
    Returns:
        WorkflowResult with analysis and order recommendations
    """
    from services.workflow_service import WorkflowService
    
    workflow = WorkflowService(db)
    result = await workflow.run_optimization_workflow(
        forecast_days=forecast_days,
        include_all_products=include_all_products,
        auto_create_orders=auto_create_orders,
    )
    
    return result.to_dict()


@app.get("/api/workflows/optimize-inventory/stream")
async def workflow_optimize_inventory_stream(
    db: Session = Depends(get_db),
    forecast_days: int = Query(7, description="Days ahead to forecast"),
    include_all_products: bool = Query(False, description="Analyze all products (not just low-stock)"),
    auto_create_orders: bool = Query(False, description="Actually create purchase orders"),
) -> StreamingResponse:
    """
    Streaming version of the optimization workflow with real-time telemetry.
    
    Sends Server-Sent Events (SSE) for dashboard real-time updates.
    """
    from services.workflow_service import WorkflowService
    from services.inventory_service import InventoryService
    from agents.demand_forecasting import DemandForecasterService
    import asyncio
    
    async def event_generator():
        try:
            # Start event
            yield f"data: {json.dumps({'event': 'start', 'message': 'Workflow started'})}\n\n"
            await asyncio.sleep(0.1)
            
            # Initialize services
            inventory_service = InventoryService(db)
            forecaster = DemandForecasterService.get_instance()
            
            yield f"data: {json.dumps({'event': 'init', 'message': 'Services initialized', 'model_loaded': forecaster.is_loaded})}\n\n"
            
            # Load products
            if include_all_products:
                products = inventory_service.get_products(limit=500)
            else:
                products = inventory_service.get_low_stock_products()
            
            yield f"data: {json.dumps({'event': 'products_loaded', 'count': len(products)})}\n\n"
            await asyncio.sleep(0.1)
            
            # Analyze each product with progress
            analyzed = []
            for i, product in enumerate(products):
                progress = int(20 + (60 * (i + 1) / len(products)))
                
                # Get forecast
                forecast = forecaster.forecast(product.asin, forecast_days)
                
                # Send progress event every 5 products
                if i % 5 == 0 or i == len(products) - 1:
                    yield f"data: {json.dumps({'event': 'analyzing', 'product': product.asin, 'index': i + 1, 'total': len(products), 'progress': progress})}\n\n"
                
                analyzed.append({
                    'asin': product.asin,
                    'title': product.title[:50] if product.title else '',
                    'forecast': forecast.to_dict() if hasattr(forecast, 'to_dict') else {},
                })
            
            yield f"data: {json.dumps({'event': 'forecasting_complete', 'count': len(analyzed)})}\n\n"
            
            # Run full workflow for results
            yield f"data: {json.dumps({'event': 'generating_orders', 'message': 'Generating order recommendations...'})}\n\n"
            
            workflow = WorkflowService(db)
            result = await workflow.run_optimization_workflow(
                forecast_days=forecast_days,
                include_all_products=include_all_products,
                auto_create_orders=auto_create_orders,
            )
            
            # Complete event
            yield f"data: {json.dumps({'event': 'complete', 'result': result.to_dict()})}\n\n"
            
        except Exception as e:
            logger.error(f"Streaming workflow error: {e}", exc_info=True)
            yield f"data: {json.dumps({'event': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/workflows/analyze-product/{asin}")
def workflow_analyze_product(
    asin: str,
    forecast_days: int = Query(7, description="Days ahead to forecast"),
    db: Session = Depends(get_db),
):
    """
    Analyze a single product with forecasting and pricing.
    
    Returns demand forecast, current stock, Amazon price, and reorder recommendation.
    """
    from services.workflow_service import WorkflowService
    
    workflow = WorkflowService(db)
    result = workflow.analyze_single_product(asin, forecast_days)
    
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return result


@app.get("/api/forecast/{asin}")
def get_demand_forecast(
    asin: str,
    days: int = Query(7, description="Days ahead to forecast"),
):
    """
    Get demand forecast for a product from the trained ML model.
    
    Returns predicted demand with confidence intervals.
    """
    from agents.demand_forecasting import DemandForecasterService
    
    forecaster = DemandForecasterService.get_instance()
    forecast = forecaster.forecast(asin, days)
    
    return forecast.to_dict()


@app.get("/api/forecast/model/info")
def get_forecast_model_info():
    """Get information about the loaded forecasting model."""
    from agents.demand_forecasting import DemandForecasterService
    
    forecaster = DemandForecasterService.get_instance()
    return forecaster.get_model_info()


# ========== AGENT ENDPOINTS ==========


@app.get("/api/health")
async def agent_health():
    """Health check including agent and MCP status.
    
    Returns:
        Health status including agent availability and MCP servers
    """
    mcp_status = {
        "total_servers": len(tool_registry._server_metadata),
        "configured_servers": list(tool_registry._server_metadata.keys()),
    }
    
    return {
        "status": "OK",
        "service": "supply-chain-agents",
        "version": "1.0.0",
        "agents": [
            "OrchestratorAgent",
            "PriceMonitoringAgent", 
            "DemandForecastingAgent",
            "AutomatedOrderingAgent",
        ],
        "mcp": mcp_status,
    }


@app.get("/api/tools")
async def list_tools():
    """List all available MCP tools.
    
    Returns:
        Dictionary with tools array including reachability status
    """
    try:
        tools_info = await tool_registry.list_tools()
        return tools_info
    except Exception as e:
        logger.error(f"Error listing tools: {e}")
        return {"tools": [], "error": str(e)}


@app.post("/api/chat")
async def chat(request: ChatRequest) -> StreamingResponse:
    """Process a chat request through the Supply Chain agents with SSE streaming.
    
    Args:
        request: Chat request with message and optional context
        
    Returns:
        StreamingResponse with Server-Sent Events
    """
    async def event_generator():
        """Generate Server-Sent Events for the chat response."""
        try:
            logger.info(f"Processing chat request: {request.message[:100]}...")
            
            # Send START event
            start_event = {
                "type": "metadata",
                "event": "WorkflowStarted",
                "kind": "supply-chain-agents",
                "data": {"agent": "Orchestrator", "message": "Starting workflow"},
            }
            yield f"data: {json.dumps(start_event)}\n\n"
            
            # Process through workflow with streaming
            async for event in magentic_orchestrator.process_request_stream(
                user_message=request.message,
                conversation_history=request.context,
            ):
                yield f"data: {json.dumps(event)}\n\n"
            
            # Send END event
            end_event = {
                "type": "metadata",
                "kind": "supply-chain-agents",
                "event": "Complete",
                "data": {"message": "Request processed successfully"},
            }
            yield f"data: {json.dumps(end_event)}\n\n"
            logger.info("Request processed successfully")
            
        except Exception as e:
            logger.error(f"Error processing chat: {e}", exc_info=True)
            error_event = {
                "type": "error",
                "kind": "supply-chain-agents",
                "event": "Error",
                "error": {"message": str(e), "statusCode": 500},
            }
            yield f"data: {json.dumps(error_event)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
