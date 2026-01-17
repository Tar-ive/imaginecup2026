"""
Pydantic models for supplier negotiation workflow.
Follows UCP (Universal Commerce Protocol) patterns.
"""

from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class NegotiationStatus(str, Enum):
    """Status of a negotiation session."""
    OPEN = "open"
    QUOTING = "quoting"
    NEGOTIATING = "negotiating"
    ACCEPTED = "accepted"
    CANCELLED = "cancelled"


class NegotiationItem(BaseModel):
    """Item to negotiate (like UCP line_item)."""
    model_config = ConfigDict(extra="allow")
    
    sku: str
    title: str
    quantity: int = Field(..., ge=1)
    target_price: Optional[float] = None


class SupplierQuote(BaseModel):
    """Quote from a supplier (like UCP fulfillment_option)."""
    model_config = ConfigDict(extra="allow")
    
    quote_id: str
    supplier_id: str
    supplier_name: str
    unit_price: float
    total_price: float
    lead_time_days: int
    valid_until: datetime
    round_number: int = 1
    is_counter: bool = False


class NegotiationSession(BaseModel):
    """Active negotiation session (like UCP checkout)."""
    model_config = ConfigDict(extra="allow")
    
    session_id: str
    status: NegotiationStatus
    items: List[NegotiationItem]
    quotes: List[SupplierQuote] = []
    current_round: int = 0
    max_rounds: int = 3
    best_offer: Optional[SupplierQuote] = None
    accepted_quote: Optional[SupplierQuote] = None
    created_at: datetime
    events: List[Dict[str, Any]] = []  # Append-only log


class CounterOfferRequest(BaseModel):
    """Counter-offer request (like UCP discount)."""
    session_id: str
    supplier_id: str
    counter_price: float
    justification: Optional[str] = None


class AcceptOfferRequest(BaseModel):
    """Accept offer request (like UCP complete_checkout)."""
    session_id: str
    supplier_id: str


class CreateSessionRequest(BaseModel):
    """Request to create a new negotiation session."""
    items: List[NegotiationItem]
    max_rounds: int = 3


class RequestQuotesRequest(BaseModel):
    """Request to get quotes from suppliers."""
    session_id: str
    supplier_ids: Optional[List[str]] = None  # None = all active suppliers
