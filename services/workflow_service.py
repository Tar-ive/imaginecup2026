"""
Workflow Service for Supply Chain Optimization
==============================================
Combines demand forecasting, price monitoring, and order generation
into a complete supply chain optimization workflow.

Usage:
    from services.workflow_service import WorkflowService
    
    workflow = WorkflowService(db)
    result = await workflow.run_optimization_workflow()
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
import requests

from sqlalchemy.orm import Session

from database.models import Product, Supplier, PurchaseOrder
from services.inventory_service import InventoryService
from services.order_service import OrderService
from agents.demand_forecasting import DemandForecasterService, DemandForecast

logger = logging.getLogger(__name__)

# Amazon API endpoint
AMAZON_API_URL = "https://amazon-api-app.purplepebble-8d2a2163.eastus.azurecontainerapps.io/products"


@dataclass
class ProductAnalysis:
    """Analysis result for a single product."""
    asin: str
    title: str
    current_stock: int
    reorder_point: int
    predicted_demand: float
    confidence_lower: float
    confidence_upper: float
    confidence_level: str
    shortfall: float  # predicted_demand - current_stock
    needs_reorder: bool
    amazon_price: Optional[float] = None
    db_price: Optional[float] = None
    price_change_pct: Optional[float] = None
    recommended_order_qty: int = 0
    supplier_id: Optional[str] = None
    supplier_name: Optional[str] = None


@dataclass
class OrderRecommendation:
    """Recommended order for a supplier."""
    supplier_id: str
    supplier_name: str
    items: List[Dict]  # [{asin, title, quantity, unit_price, line_total}]
    total_value: float
    total_items: int
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class WorkflowResult:
    """Complete workflow result."""
    timestamp: str
    products_analyzed: int
    products_needing_reorder: int
    order_recommendations: List[Dict]
    total_recommended_value: float
    analysis_details: List[Dict]
    
    def to_dict(self) -> dict:
        return asdict(self)


class WorkflowService:
    """
    Supply Chain Optimization Workflow Service.
    
    Combines:
    1. Demand forecasting (from trained ML model)
    2. Price monitoring (from Amazon API)
    3. Order recommendations (grouped by supplier)
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.inventory_service = InventoryService(db)
        self.order_service = OrderService(db)
        self.forecaster = DemandForecasterService.get_instance()
    
    async def run_optimization_workflow(
        self,
        forecast_days: int = 7,
        include_all_products: bool = False,
        auto_create_orders: bool = False,
    ) -> WorkflowResult:
        """
        Run the complete supply chain optimization workflow.
        
        Args:
            forecast_days: Days ahead to forecast demand
            include_all_products: If True, analyze all products; else only low-stock
            auto_create_orders: If True, actually create POs; else just recommendations
        
        Returns:
            WorkflowResult with analysis and recommendations
        """
        logger.info(f"Starting optimization workflow (forecast_days={forecast_days})")
        
        # Step 1: Get products to analyze
        if include_all_products:
            products = self.inventory_service.get_products(limit=500)
        else:
            products = self.inventory_service.get_low_stock_products()
        
        logger.info(f"Analyzing {len(products)} products")
        
        # Step 2: Analyze each product
        analysis_results: List[ProductAnalysis] = []
        
        for product in products:
            analysis = await self._analyze_product(product, forecast_days)
            analysis_results.append(analysis)
        
        # Step 3: Filter products needing reorder
        reorder_products = [a for a in analysis_results if a.needs_reorder]
        
        # Step 4: Generate order recommendations (grouped by supplier)
        order_recommendations = self._generate_order_recommendations(reorder_products)
        
        # Step 5: Optionally create orders
        if auto_create_orders and order_recommendations:
            for rec in order_recommendations:
                try:
                    self._create_purchase_order(rec)
                except Exception as e:
                    logger.error(f"Failed to create order for {rec['supplier_id']}: {e}")
        
        # Build result
        result = WorkflowResult(
            timestamp=datetime.utcnow().isoformat(),
            products_analyzed=len(analysis_results),
            products_needing_reorder=len(reorder_products),
            order_recommendations=[r for r in order_recommendations],
            total_recommended_value=sum(r['total_value'] for r in order_recommendations),
            analysis_details=[asdict(a) for a in analysis_results],
        )
        
        logger.info(
            f"Workflow complete: {result.products_needing_reorder} products need reorder, "
            f"${result.total_recommended_value:.2f} total value"
        )
        
        return result
    
    async def _analyze_product(
        self, product: Product, forecast_days: int
    ) -> ProductAnalysis:
        """Analyze a single product with forecasting and pricing."""
        
        # Get demand forecast
        forecast = self.forecaster.forecast(product.asin, forecast_days)
        
        # Get Amazon price
        amazon_price = self._get_amazon_price(product.asin)
        
        # Calculate shortfall
        current_stock = product.quantity_available or 0
        predicted_demand = forecast.predicted_total_demand
        shortfall = predicted_demand - current_stock
        
        # Determine if reorder needed
        # Reorder if: predicted demand > current stock OR current stock < reorder point
        needs_reorder = (
            shortfall > 0 or 
            current_stock <= (product.reorder_point or 10)
        )
        
        # Calculate recommended order quantity
        recommended_qty = 0
        if needs_reorder:
            # Order enough to cover demand + safety buffer
            safety_buffer = forecast.confidence_upper - predicted_demand
            recommended_qty = max(
                int(shortfall + safety_buffer),
                product.reorder_quantity or 50
            )
        
        # Price comparison
        db_price = float(product.market_price) if product.market_price else None
        price_change_pct = None
        if db_price and amazon_price and db_price > 0:
            price_change_pct = round(((amazon_price - db_price) / db_price) * 100, 2)
        
        # Get supplier info
        supplier_name = None
        if product.supplier:
            supplier_name = product.supplier.supplier_name
        
        return ProductAnalysis(
            asin=product.asin,
            title=product.title[:100] if product.title else "",
            current_stock=current_stock,
            reorder_point=product.reorder_point or 10,
            predicted_demand=predicted_demand,
            confidence_lower=forecast.confidence_lower,
            confidence_upper=forecast.confidence_upper,
            confidence_level=forecast.confidence_level,
            shortfall=max(0, shortfall),
            needs_reorder=needs_reorder,
            amazon_price=amazon_price,
            db_price=db_price,
            price_change_pct=price_change_pct,
            recommended_order_qty=recommended_qty,
            supplier_id=product.supplier_id,
            supplier_name=supplier_name,
        )
    
    def _get_amazon_price(self, asin: str) -> Optional[float]:
        """Get current price from Amazon API."""
        try:
            response = requests.get(
                AMAZON_API_URL,
                params={"query": asin, "limit": 1},
                timeout=5
            )
            response.raise_for_status()
            products = response.json()
            
            if products and len(products) > 0:
                price = products[0].get("initial_price")
                if price and isinstance(price, (int, float)):
                    return float(price)
        except Exception as e:
            logger.debug(f"Failed to get Amazon price for {asin}: {e}")
        
        return None
    
    def _generate_order_recommendations(
        self, products: List[ProductAnalysis]
    ) -> List[Dict]:
        """Group products by supplier and generate order recommendations."""
        
        # Group by supplier
        by_supplier: Dict[str, List[ProductAnalysis]] = {}
        for p in products:
            supplier_id = p.supplier_id or "UNKNOWN"
            if supplier_id not in by_supplier:
                by_supplier[supplier_id] = []
            by_supplier[supplier_id].append(p)
        
        # Generate recommendations
        recommendations = []
        for supplier_id, items in by_supplier.items():
            # Get supplier name
            supplier_name = items[0].supplier_name or supplier_id
            
            # Build order items
            order_items = []
            total_value = 0
            
            for item in items:
                if item.recommended_order_qty <= 0:
                    continue
                
                # Use Amazon price if available, else DB price, else default
                unit_price = item.amazon_price or item.db_price or 10.0
                line_total = item.recommended_order_qty * unit_price
                
                order_items.append({
                    "asin": item.asin,
                    "title": item.title,
                    "quantity": item.recommended_order_qty,
                    "unit_price": round(unit_price, 2),
                    "line_total": round(line_total, 2),
                    "current_stock": item.current_stock,
                    "predicted_demand": item.predicted_demand,
                })
                total_value += line_total
            
            if order_items:
                recommendations.append({
                    "supplier_id": supplier_id,
                    "supplier_name": supplier_name,
                    "items": order_items,
                    "total_value": round(total_value, 2),
                    "total_items": len(order_items),
                })
        
        # Sort by total value descending
        recommendations.sort(key=lambda x: x["total_value"], reverse=True)
        
        return recommendations
    
    def _create_purchase_order(self, recommendation: Dict) -> Optional[PurchaseOrder]:
        """Actually create a purchase order from recommendation."""
        items = [
            {
                "asin": item["asin"],
                "quantity": item["quantity"],
                "unit_price": item["unit_price"],
            }
            for item in recommendation["items"]
        ]
        
        expected_delivery = datetime.utcnow() + timedelta(days=7)
        
        return self.order_service.create_order(
            supplier_id=recommendation["supplier_id"],
            items=items,
            expected_delivery_date=expected_delivery,
        )
    
    def analyze_single_product(self, asin: str, forecast_days: int = 7) -> Dict:
        """Analyze a single product synchronously."""
        import asyncio
        
        product = self.inventory_service.get_product_by_asin(asin)
        if not product:
            return {"error": f"Product {asin} not found"}
        
        # Run async analysis
        loop = asyncio.new_event_loop()
        try:
            analysis = loop.run_until_complete(
                self._analyze_product(product, forecast_days)
            )
            return asdict(analysis)
        finally:
            loop.close()
