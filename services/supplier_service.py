"""
Supplier service for supplier management operations.
"""
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import func
from database.models import Supplier, Product, PurchaseOrder


class SupplierService:
    """Service for managing supplier operations"""

    def __init__(self, db: Session):
        self.db = db

    def get_all_suppliers(self, active_only: bool = True) -> List[Supplier]:
        """Get all suppliers"""
        q = self.db.query(Supplier)

        if active_only:
            q = q.filter(Supplier.is_active == True)

        return q.all()

    def get_supplier_by_id(self, supplier_id: str) -> Optional[Supplier]:
        """Get supplier by ID"""
        return self.db.query(Supplier).filter(Supplier.supplier_id == supplier_id).first()

    def get_supplier_performance(self, supplier_id: str) -> Optional[Dict]:
        """
        Get comprehensive supplier performance metrics.

        Returns:
            Dict with performance data or None if supplier not found
        """
        supplier = self.get_supplier_by_id(supplier_id)
        if not supplier:
            return None

        # Count products from this supplier
        product_count = self.db.query(Product).filter(
            Product.supplier_id == supplier_id,
            Product.is_active == True
        ).count()

        # Count total orders
        total_orders = self.db.query(PurchaseOrder).filter(
            PurchaseOrder.supplier_id == supplier_id
        ).count()

        # Count received orders
        received_orders = self.db.query(PurchaseOrder).filter(
            PurchaseOrder.supplier_id == supplier_id,
            PurchaseOrder.status == 'received'
        ).count()

        # Calculate average order value
        avg_order_value = self.db.query(func.avg(PurchaseOrder.total_cost)).filter(
            PurchaseOrder.supplier_id == supplier_id
        ).scalar() or 0

        return {
            'supplier_id': supplier.supplier_id,
            'supplier_name': supplier.supplier_name,
            'contact_person': supplier.contact_person,
            'email': supplier.email,
            'phone': supplier.phone,
            'on_time_delivery_rate': float(supplier.on_time_delivery_rate or 0),
            'quality_rating': float(supplier.quality_rating or 0),
            'default_lead_time_days': supplier.default_lead_time_days,
            'payment_terms': supplier.payment_terms,
            'product_count': product_count,
            'total_orders': total_orders,
            'received_orders': received_orders,
            'avg_order_value': round(float(avg_order_value), 2)
        }

    def get_products_by_supplier(self, supplier_id: str) -> List[Product]:
        """Get all active products from a specific supplier"""
        return self.db.query(Product).filter(
            Product.supplier_id == supplier_id,
            Product.is_active == True
        ).all()

    def get_supplier_summary(self) -> List[Dict]:
        """Get summary of all suppliers with key metrics"""
        suppliers = self.get_all_suppliers()

        summary = []
        for supplier in suppliers:
            perf = self.get_supplier_performance(supplier.supplier_id)
            if perf:
                summary.append({
                    'supplier_id': supplier.supplier_id,
                    'supplier_name': supplier.supplier_name,
                    'on_time_delivery_rate': perf['on_time_delivery_rate'],
                    'quality_rating': perf['quality_rating'],
                    'product_count': perf['product_count'],
                    'total_orders': perf['total_orders']
                })

        return summary
