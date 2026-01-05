"""
SQLAlchemy ORM models for inventory database.
Maps Python classes to Azure SQL tables.
"""

from sqlalchemy import (
    Column,
    String,
    Integer,
    DECIMAL,
    DateTime,
    Boolean,
    ForeignKey,
    Computed,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .config import Base


class Supplier(Base):
    """Supplier master with contact details and performance metrics"""

    __tablename__ = "suppliers"

    supplier_id = Column(String(50), primary_key=True)
    supplier_name = Column(String(100), nullable=False)

    # Contact Information
    contact_person = Column(String(100))
    email = Column(String(255))
    phone = Column(String(50))
    address = Column(String(500))
    city = Column(String(100))
    state_province = Column(String(100))
    country = Column(String(100))
    postal_code = Column(String(20))

    # Business Terms
    payment_terms = Column(String(100))
    default_lead_time_days = Column(Integer, default=7)

    # Performance Metrics
    on_time_delivery_rate = Column(DECIMAL(5, 2))  # e.g., 95.50
    quality_rating = Column(DECIMAL(3, 2))  # e.g., 4.75

    # Metadata
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, default=True)

    # Relationships
    products = relationship("Product", back_populates="supplier")
    purchase_orders = relationship("PurchaseOrder", back_populates="supplier")

    def __repr__(self):
        return f"<Supplier {self.supplier_id}: {self.supplier_name}>"


class Product(Base):
    """Product inventory with stock levels, pricing, and reordering rules"""

    __tablename__ = "products"

    # Identification
    asin = Column(String(20), primary_key=True)
    title = Column(String(500), nullable=False)
    brand = Column(String(100))
    description = Column(String)

    # Pricing
    unit_cost = Column(DECIMAL(10, 2))
    last_purchase_price = Column(DECIMAL(10, 2))
    market_price = Column(DECIMAL(10, 2))
    price_last_updated = Column(DateTime)

    # Stock Levels
    quantity_on_hand = Column(Integer, nullable=False, default=0)
    quantity_reserved = Column(Integer, nullable=False, default=0)
    # quantity_available is computed column in SQL

    # Reordering Rules
    reorder_point = Column(Integer, nullable=False, default=10)
    reorder_quantity = Column(Integer, nullable=False, default=50)
    lead_time_days = Column(Integer, nullable=False, default=7)

    # Supplier Link
    supplier_id = Column(String(50), ForeignKey("suppliers.supplier_id"))

    # Metadata
    created_at = Column(DateTime, server_default=func.getdate())
    updated_at = Column(
        DateTime, server_default=func.getdate(), onupdate=func.getdate()
    )
    is_active = Column(Boolean, default=True)

    # Relationships
    supplier = relationship("Supplier", back_populates="products")
    order_items = relationship("PurchaseOrderItem", back_populates="product")

    @property
    def quantity_available(self):
        """Computed property: available = on_hand - reserved"""
        return self.quantity_on_hand - self.quantity_reserved

    @property
    def needs_reorder(self):
        """Check if product is below reorder point"""
        return self.quantity_available <= self.reorder_point

    def __repr__(self):
        return f"<Product {self.asin}: {self.title[:50]}>"


class PurchaseOrder(Base):
    """Purchase order header with supplier and status tracking"""

    __tablename__ = "purchase_orders"

    po_number = Column(String(50), primary_key=True)
    supplier_id = Column(
        String(50), ForeignKey("suppliers.supplier_id"), nullable=False
    )

    # Dates
    order_date = Column(DateTime, nullable=False)
    expected_delivery_date = Column(DateTime)
    actual_delivery_date = Column(DateTime)

    # Financial
    total_cost = Column(DECIMAL(12, 2), nullable=False)

    # Status: pending, shipped, received, cancelled
    status = Column(String(50), nullable=False)

    # Metadata
    created_by = Column(String(100))
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    supplier = relationship("Supplier", back_populates="purchase_orders")
    items = relationship("PurchaseOrderItem", back_populates="purchase_order")

    @property
    def item_count(self):
        """Total number of line items"""
        return len(self.items)

    @property
    def is_delivered(self):
        """Check if order has been delivered"""
        return self.status == "received"

    def __repr__(self):
        return f"<PurchaseOrder {self.po_number}: {self.status}>"


class PurchaseOrderItem(Base):
    """Purchase order line items with product and quantity details"""

    __tablename__ = "purchase_order_items"

    po_item_id = Column(Integer, primary_key=True, autoincrement=True)
    po_number = Column(
        String(50), ForeignKey("purchase_orders.po_number"), nullable=False
    )
    asin = Column(String(20), ForeignKey("products.asin"), nullable=False)

    # Quantities
    quantity_ordered = Column(Integer, nullable=False)
    quantity_received = Column(Integer, default=0)

    # Pricing
    unit_price = Column(DECIMAL(10, 2), nullable=False)
    # line_total is computed column in SQL

    # Metadata
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    purchase_order = relationship("PurchaseOrder", back_populates="items")
    product = relationship("Product", back_populates="order_items")

    @property
    def line_total(self):
        """Computed property: total = quantity * price"""
        return self.quantity_ordered * self.unit_price

    @property
    def is_fully_received(self):
        """Check if all ordered items have been received"""
        return self.quantity_received >= self.quantity_ordered

    def __repr__(self):
        return f"<POItem {self.po_item_id}: {self.asin} x{self.quantity_ordered}>"
