"""
Order service for purchase order operations.
"""
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from datetime import datetime, timedelta
from database.models import PurchaseOrder, PurchaseOrderItem, Product


class OrderService:
    """Service for managing purchase order operations"""

    def __init__(self, db: Session):
        self.db = db

    def get_orders(
        self,
        status: Optional[str] = None,
        supplier_id: Optional[str] = None,
        days: int = 90,
        skip: int = 0,
        limit: int = 50
    ) -> List[PurchaseOrder]:
        """
        Get purchase orders with filtering.

        Args:
            status: Filter by status (pending, shipped, received, cancelled)
            supplier_id: Filter by supplier
            days: Only return orders from last N days
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of PurchaseOrder objects
        """
        cutoff_date = datetime.now() - timedelta(days=days)

        q = self.db.query(PurchaseOrder).filter(
            PurchaseOrder.order_date >= cutoff_date
        )

        if status:
            q = q.filter(PurchaseOrder.status == status)

        if supplier_id:
            q = q.filter(PurchaseOrder.supplier_id == supplier_id)

        return q.order_by(PurchaseOrder.order_date.desc()).offset(skip).limit(limit).all()

    def get_order_details(self, po_number: str) -> Optional[Dict]:
        """
        Get full order details with line items.

        Returns:
            Dict with order header and items, or None if not found
        """
        order = self.db.query(PurchaseOrder).filter(
            PurchaseOrder.po_number == po_number
        ).first()

        if not order:
            return None

        # Get line items with product details
        items = self.db.query(PurchaseOrderItem, Product).join(
            Product, PurchaseOrderItem.asin == Product.asin
        ).filter(
            PurchaseOrderItem.po_number == po_number
        ).all()

        line_items = []
        for item, product in items:
            line_items.append({
                'po_item_id': item.po_item_id,
                'asin': item.asin,
                'product_title': product.title,
                'quantity_ordered': item.quantity_ordered,
                'quantity_received': item.quantity_received,
                'unit_price': float(item.unit_price),
                'line_total': float(item.line_total)
            })

        return {
            'po_number': order.po_number,
            'supplier_id': order.supplier_id,
            'supplier_name': order.supplier.supplier_name if order.supplier else None,
            'order_date': order.order_date.isoformat(),
            'expected_delivery_date': order.expected_delivery_date.isoformat() if order.expected_delivery_date else None,
            'actual_delivery_date': order.actual_delivery_date.isoformat() if order.actual_delivery_date else None,
            'status': order.status,
            'total_cost': float(order.total_cost),
            'created_by': order.created_by,
            'items': line_items,
            'item_count': len(line_items)
        }

    def create_order(
        self,
        supplier_id: str,
        items: List[Dict],
        expected_delivery_date: Optional[datetime] = None
    ) -> PurchaseOrder:
        """
        Create a new purchase order.

        Args:
            supplier_id: Supplier ID
            items: List of dicts with 'asin', 'quantity', 'unit_price'
            expected_delivery_date: Optional expected delivery date

        Returns:
            Created PurchaseOrder object

        Raises:
            ValueError: If supplier or products not found
        """
        from database.models import Supplier

        # Validate supplier exists
        supplier = self.db.query(Supplier).filter(Supplier.supplier_id == supplier_id).first()
        if not supplier:
            raise ValueError(f"Supplier {supplier_id} not found")

        # Generate PO number
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        po_number = f"PO-{timestamp}"

        # Calculate expected delivery if not provided
        if not expected_delivery_date:
            expected_delivery_date = datetime.now() + timedelta(days=supplier.default_lead_time_days)

        # Create order
        order = PurchaseOrder(
            po_number=po_number,
            supplier_id=supplier_id,
            order_date=datetime.now(),
            expected_delivery_date=expected_delivery_date,
            total_cost=0.0,
            status='pending',
            created_by='api'
        )

        total_cost = 0.0

        # Create line items
        for item_data in items:
            # Validate product exists
            product = self.db.query(Product).filter(Product.asin == item_data['asin']).first()
            if not product:
                raise ValueError(f"Product {item_data['asin']} not found")

            item = PurchaseOrderItem(
                po_number=po_number,
                asin=item_data['asin'],
                quantity_ordered=item_data['quantity'],
                quantity_received=0,
                unit_price=item_data['unit_price']
            )

            total_cost += item_data['quantity'] * item_data['unit_price']
            self.db.add(item)

        order.total_cost = round(total_cost, 2)
        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)

        return order

    def update_order_status(self, po_number: str, status: str) -> Optional[PurchaseOrder]:
        """Update order status"""
        valid_statuses = ['pending', 'shipped', 'received', 'cancelled']
        if status not in valid_statuses:
            raise ValueError(f"Invalid status. Must be one of: {valid_statuses}")

        order = self.db.query(PurchaseOrder).filter(
            PurchaseOrder.po_number == po_number
        ).first()

        if not order:
            return None

        order.status = status

        # Set actual delivery date if status is received
        if status == 'received' and not order.actual_delivery_date:
            order.actual_delivery_date = datetime.now()

        self.db.commit()
        self.db.refresh(order)

        return order

    def receive_order(self, po_number: str, items_received: List[Dict]) -> Optional[PurchaseOrder]:
        """
        Mark order items as received and update inventory.

        Args:
            po_number: Purchase order number
            items_received: List of dicts with 'asin' and 'quantity_received'

        Returns:
            Updated PurchaseOrder or None if not found
        """
        order = self.db.query(PurchaseOrder).filter(
            PurchaseOrder.po_number == po_number
        ).first()

        if not order:
            return None

        for item_data in items_received:
            # Update line item
            item = self.db.query(PurchaseOrderItem).filter(
                and_(
                    PurchaseOrderItem.po_number == po_number,
                    PurchaseOrderItem.asin == item_data['asin']
                )
            ).first()

            if item:
                item.quantity_received = item_data['quantity_received']

                # Update product inventory
                product = self.db.query(Product).filter(
                    Product.asin == item_data['asin']
                ).first()

                if product:
                    product.quantity_on_hand += item_data['quantity_received']

        # Update order status to received
        order.status = 'received'
        order.actual_delivery_date = datetime.now()

        self.db.commit()
        self.db.refresh(order)

        return order

    def get_order_history_by_product(self, asin: str) -> List[Dict]:
        """Get all orders containing a specific product"""
        items = self.db.query(PurchaseOrderItem, PurchaseOrder).join(
            PurchaseOrder, PurchaseOrderItem.po_number == PurchaseOrder.po_number
        ).filter(
            PurchaseOrderItem.asin == asin
        ).order_by(PurchaseOrder.order_date.desc()).all()

        history = []
        for item, order in items:
            history.append({
                'po_number': order.po_number,
                'order_date': order.order_date.isoformat(),
                'supplier_id': order.supplier_id,
                'supplier_name': order.supplier.supplier_name if order.supplier else None,
                'quantity_ordered': item.quantity_ordered,
                'quantity_received': item.quantity_received,
                'unit_price': float(item.unit_price),
                'status': order.status
            })

        return history
