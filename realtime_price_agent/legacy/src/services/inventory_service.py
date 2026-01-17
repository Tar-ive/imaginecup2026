"""
Inventory service for product CRUD and stock operations.
"""
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from src.database.models import Product


class InventoryService:
    """Service for managing inventory operations"""

    def __init__(self, db: Session):
        self.db = db

    def get_products(
        self,
        brand: Optional[str] = None,
        query: Optional[str] = None,
        min_qty: Optional[int] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Product]:
        """
        Get products with optional filtering.

        Args:
            brand: Filter by brand (case-insensitive substring match)
            query: Search in title and description
            min_qty: Minimum quantity_available
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of Product objects
        """
        q = self.db.query(Product).filter(Product.is_active == True)

        if brand:
            q = q.filter(Product.brand.ilike(f'%{brand}%'))

        if query:
            q = q.filter(
                or_(
                    Product.title.ilike(f'%{query}%'),
                    Product.description.ilike(f'%{query}%')
                )
            )

        # Note: quantity_available is computed, so we calculate it in query
        if min_qty is not None:
            q = q.filter((Product.quantity_on_hand - Product.quantity_reserved) >= min_qty)

        return q.offset(skip).limit(limit).all()

    def get_product_by_asin(self, asin: str) -> Optional[Product]:
        """Get single product by ASIN"""
        return self.db.query(Product).filter(Product.asin == asin).first()

    def get_low_stock_products(self, threshold: Optional[int] = None) -> List[Product]:
        """
        Get products below reorder point.

        Args:
            threshold: Optional custom threshold (overrides individual reorder_point)

        Returns:
            List of products that need reordering
        """
        q = self.db.query(Product).filter(Product.is_active == True)

        if threshold is not None:
            # Use custom threshold for all products
            q = q.filter((Product.quantity_on_hand - Product.quantity_reserved) <= threshold)
        else:
            # Use each product's reorder_point
            q = q.filter((Product.quantity_on_hand - Product.quantity_reserved) <= Product.reorder_point)

        return q.all()

    def adjust_stock(
        self,
        asin: str,
        quantity_change: int,
        reason: str = "Manual adjustment"
    ) -> Optional[Product]:
        """
        Adjust stock levels for a product.

        Args:
            asin: Product ASIN
            quantity_change: Change in quantity (positive or negative)
            reason: Reason for adjustment

        Returns:
            Updated Product object or None if not found
        """
        product = self.get_product_by_asin(asin)
        if not product:
            return None

        product.quantity_on_hand += quantity_change

        # Ensure quantity doesn't go negative
        if product.quantity_on_hand < 0:
            product.quantity_on_hand = 0

        self.db.commit()
        self.db.refresh(product)

        return product

    def reserve_stock(self, asin: str, quantity: int) -> bool:
        """
        Reserve stock for an order.

        Args:
            asin: Product ASIN
            quantity: Quantity to reserve

        Returns:
            True if successful, False if insufficient stock
        """
        product = self.get_product_by_asin(asin)
        if not product:
            return False

        available = product.quantity_on_hand - product.quantity_reserved

        if available < quantity:
            return False

        product.quantity_reserved += quantity
        self.db.commit()

        return True

    def release_stock(self, asin: str, quantity: int) -> bool:
        """
        Release reserved stock.

        Args:
            asin: Product ASIN
            quantity: Quantity to release

        Returns:
            True if successful, False if not found
        """
        product = self.get_product_by_asin(asin)
        if not product:
            return False

        product.quantity_reserved -= quantity

        # Ensure reserved doesn't go negative
        if product.quantity_reserved < 0:
            product.quantity_reserved = 0

        self.db.commit()

        return True

    def get_stock_summary(self) -> Dict:
        """Get summary statistics for inventory"""
        all_products = self.db.query(Product).filter(Product.is_active == True).all()

        total = len(all_products)
        out_of_stock = sum(1 for p in all_products if p.quantity_on_hand == 0)
        low_stock = sum(1 for p in all_products if p.needs_reorder and p.quantity_on_hand > 0)
        adequate = total - out_of_stock - low_stock

        total_value = sum(p.quantity_on_hand * (p.unit_cost or 0) for p in all_products)

        return {
            'total_products': total,
            'out_of_stock': out_of_stock,
            'low_stock': low_stock,
            'adequate_stock': adequate,
            'total_inventory_value': round(total_value, 2)
        }
