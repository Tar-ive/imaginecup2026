"""
SQLAlchemy ORM models for negotiation sessions and supplier quotes.
Stores negotiation workflow state in Postgres.
"""

from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from .config import Base


class NegotiationSession(Base):
    """Negotiation session tracking (like UCP checkout)."""
    __tablename__ = "negotiation_sessions"
    
    session_id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    status = Column(String(20), default="open")  # open, quoting, negotiating, accepted, cancelled
    items_json = Column(Text)  # JSON array of items
    max_rounds = Column(Integer, default=3)
    current_round = Column(Integer, default=0)
    best_supplier_id = Column(String(50), nullable=True)
    best_price = Column(Float, nullable=True)
    accepted_supplier_id = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    quotes = relationship("NegotiationQuote", back_populates="session", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<NegotiationSession {self.session_id}: {self.status}>"


class NegotiationQuote(Base):
    """Supplier quote for a negotiation session."""
    __tablename__ = "negotiation_quotes"
    
    quote_id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(50), ForeignKey("negotiation_sessions.session_id"), nullable=False)
    supplier_id = Column(String(50), nullable=False)
    supplier_name = Column(String(100))
    unit_price = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)
    lead_time_days = Column(Integer)
    round_number = Column(Integer, default=1)
    is_counter = Column(Boolean, default=False)
    status = Column(String(20), default="pending")  # pending, accepted, rejected, countered
    created_at = Column(DateTime, default=datetime.utcnow)
    valid_until = Column(DateTime)
    
    # Relationships
    session = relationship("NegotiationSession", back_populates="quotes")
    
    def __repr__(self):
        return f"<NegotiationQuote {self.quote_id}: ${self.unit_price} from {self.supplier_name}>"
