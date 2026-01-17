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
    Text,
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

    # Negotiation Fields
    negotiation_enabled = Column(Boolean, default=False)
    negotiation_email = Column(String(255))
    preferred_communication = Column(String(20), default="email")  # 'email', 'api', 'edi'
    api_endpoint = Column(String(500))
    last_negotiation_date = Column(DateTime)

    # Metadata
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, default=True)

    # Relationships
    products = relationship("Product", back_populates="supplier")
    purchase_orders = relationship("PurchaseOrder", back_populates="supplier")
    negotiation_sessions = relationship("NegotiationSession", back_populates="supplier", foreign_keys="NegotiationSession.winning_supplier_id")
    negotiation_rounds = relationship("NegotiationRound", back_populates="supplier")
    payment_mandates = relationship("PaymentMandate", back_populates="supplier")

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

    # Negotiation & Payment Links
    mandate_id = Column(String(50), ForeignKey("payment_mandates.mandate_id"))
    negotiation_session_id = Column(String(50), ForeignKey("negotiation_sessions.session_id"))

    # Metadata
    created_by = Column(String(100))
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    supplier = relationship("Supplier", back_populates="purchase_orders")
    items = relationship("PurchaseOrderItem", back_populates="purchase_order")
    payment_mandate = relationship("PaymentMandate", back_populates="purchase_order", foreign_keys="[PurchaseOrder.mandate_id]")
    negotiation_session = relationship("NegotiationSession", back_populates="purchase_order", foreign_keys="[PurchaseOrder.negotiation_session_id]")

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


class NegotiationSession(Base):
    """Negotiation session for supplier price negotiation"""

    __tablename__ = "negotiation_sessions"

    session_id = Column(String(50), primary_key=True)
    status = Column(String(20), nullable=False, default="open")  # 'open', 'completed', 'cancelled'
    items_json = Column(Text, nullable=False)  # JSON array of {sku, quantity, description}
    target_price = Column(DECIMAL(10, 2))  # Optional target unit price
    max_rounds = Column(Integer, nullable=False, default=3)
    current_round = Column(Integer, nullable=False, default=0)
    winning_supplier_id = Column(String(50), ForeignKey("suppliers.supplier_id"))
    final_price = Column(DECIMAL(10, 2))  # Final accepted unit price
    total_value = Column(DECIMAL(12, 2))  # Final total order value
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    completed_at = Column(DateTime)
    created_by = Column(String(100))  # User or agent that initiated

    # Relationships
    supplier = relationship("Supplier", back_populates="negotiation_sessions", foreign_keys=[winning_supplier_id])
    rounds = relationship("NegotiationRound", back_populates="session")
    payment_mandate = relationship("PaymentMandate", back_populates="negotiation_session", uselist=False)
    purchase_order = relationship("PurchaseOrder", back_populates="negotiation_session", uselist=False)

    def __repr__(self):
        return f"<NegotiationSession {self.session_id}: {self.status}>"


class NegotiationRound(Base):
    """Individual negotiation round with a supplier"""

    __tablename__ = "negotiation_rounds"

    round_id = Column(String(50), primary_key=True)
    session_id = Column(String(50), ForeignKey("negotiation_sessions.session_id"), nullable=False)
    supplier_id = Column(String(50), ForeignKey("suppliers.supplier_id"), nullable=False)
    round_number = Column(Integer, nullable=False)  # 1, 2, 3...
    offer_type = Column(String(20), nullable=False)  # 'initial', 'counter', 'final'
    offered_price = Column(DECIMAL(10, 2), nullable=False)  # Unit price offered by supplier
    total_value = Column(DECIMAL(12, 2), nullable=False)  # Total order value
    counter_price = Column(DECIMAL(10, 2))  # Our counter-offer (if any)
    justification = Column(Text)  # Reason for counter-offer
    status = Column(String(20), nullable=False, default="pending")  # 'pending', 'accepted', 'rejected', 'countered'
    response_received_at = Column(DateTime)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    # Relationships
    session = relationship("NegotiationSession", back_populates="rounds")
    supplier = relationship("Supplier", back_populates="negotiation_rounds")

    def __repr__(self):
        return f"<NegotiationRound {self.round_id}: {self.supplier_id} R{self.round_number}>"


class PaymentMandate(Base):
    """AP2 payment mandate with cryptographic signature"""

    __tablename__ = "payment_mandates"

    mandate_id = Column(String(50), primary_key=True)
    session_id = Column(String(50), ForeignKey("negotiation_sessions.session_id"))  # Link to negotiation (optional)
    po_number = Column(String(50))  # Link to purchase order (optional) - NOTE: No FK, PO has the FK to mandate
    supplier_id = Column(String(50), ForeignKey("suppliers.supplier_id"), nullable=False)
    amount = Column(DECIMAL(12, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="USD")
    mandate_type = Column(String(20), nullable=False)  # 'checkout', 'recurring', 'preauth'
    signed_mandate_json = Column(Text, nullable=False)  # Full AP2 mandate (SD-JWT)
    merchant_authorization_json = Column(Text)  # Supplier's signed response
    signature_algorithm = Column(String(50), nullable=False)  # 'ES256', 'RS256'
    public_key_id = Column(String(100))  # Key ID for verification
    status = Column(String(20), nullable=False, default="created")  # 'created', 'sent', 'verified', 'executed', 'expired', 'failed'
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    expires_at = Column(DateTime, nullable=False)
    executed_at = Column(DateTime)
    error_message = Column(Text)

    # Relationships
    negotiation_session = relationship("NegotiationSession", back_populates="payment_mandate")
    purchase_order = relationship("PurchaseOrder", back_populates="payment_mandate", uselist=False)
    supplier = relationship("Supplier", back_populates="payment_mandates")

    def __repr__(self):
        return f"<PaymentMandate {self.mandate_id}: {self.status}>"
