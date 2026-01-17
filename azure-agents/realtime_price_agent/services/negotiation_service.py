"""
Negotiation Service
Provides business logic for supplier negotiation workflow with simulated email responses.
"""

import json
import uuid
import random
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from database.models import Supplier, Product, NegotiationSession, NegotiationRound


class NegotiationService:
    """Handles negotiation business logic and database operations."""

    def __init__(self, db: Session):
        self.db = db

    def create_session(
        self,
        items: List[Dict[str, Any]],
        target_price: Optional[float] = None,
        target_discount_percent: Optional[float] = None,
        max_rounds: int = 3,
        supplier_ids: Optional[List[str]] = None,
        created_by: str = "NegotiationAgent"
    ) -> Dict[str, Any]:
        """Create a new negotiation session."""

        session_id = f"neg-{uuid.uuid4().hex[:8]}"

        # Calculate target price if discount percentage provided
        if target_discount_percent and not target_price:
            # Get current average price for items
            sku = items[0]["sku"]
            product = self.db.query(Product).filter(Product.asin == sku).first()
            if product and product.unit_cost:
                target_price = float(product.unit_cost * (1 - target_discount_percent / 100))

        session = NegotiationSession(
            session_id=session_id,
            status="open",
            items_json=json.dumps(items),
            target_price=target_price,
            max_rounds=max_rounds,
            current_round=0,
            created_by=created_by
        )

        self.db.add(session)
        self.db.commit()

        return {
            "session_id": session_id,
            "status": "open",
            "items": items,
            "target_price": target_price,
            "max_rounds": max_rounds,
            "created_at": session.created_at.isoformat()
        }

    def request_quote(
        self,
        session_id: str,
        supplier_id: str,
        urgency: str = "medium"
    ) -> Dict[str, Any]:
        """
        Request quote from supplier with SIMULATED IMMEDIATE RESPONSE.

        In production, this would send an email and wait for response.
        For today, we simulate supplier behavior:
        - Random price variation from base cost (5-15% markup)
        - Instant response
        """

        session = self.db.query(NegotiationSession).filter_by(session_id=session_id).first()
        if not session:
            raise ValueError(f"Session {session_id} not found")

        supplier = self.db.query(Supplier).filter_by(supplier_id=supplier_id).first()
        if not supplier:
            raise ValueError(f"Supplier {supplier_id} not found")

        # Get session items
        items = json.loads(session.items_json)
        sku = items[0]["sku"]
        quantity = items[0]["quantity"]

        # Get product base price
        product = self.db.query(Product).filter_by(asin=sku).first()
        if not product or not product.unit_cost:
            # Fallback to default price
            base_price = 5.0
        else:
            base_price = float(product.unit_cost)

        # SIMULATE: Random price variation (5-15% markup)
        markup_percent = random.uniform(1.05, 1.15)
        offered_price = round(base_price * markup_percent, 2)
        total_value = round(offered_price * quantity, 2)

        # Create negotiation round with IMMEDIATE simulated response
        round_id = f"rnd-{uuid.uuid4().hex[:8]}"
        round_number = session.current_round + 1

        round_entry = NegotiationRound(
            round_id=round_id,
            session_id=session_id,
            supplier_id=supplier_id,
            round_number=round_number,
            offer_type="initial",
            offered_price=offered_price,
            total_value=total_value,
            status="received",  # Already received (simulated)
            response_received_at=datetime.now()
        )

        session.current_round = round_number
        self.db.add(round_entry)
        self.db.commit()

        return {
            "round_id": round_id,
            "session_id": session_id,
            "supplier_id": supplier_id,
            "supplier_name": supplier.supplier_name,
            "offered_price": offered_price,
            "total_value": total_value,
            "status": "received",
            "simulated": True,  # Flag to indicate this was simulated
            "items": items
        }

    def submit_counter(
        self,
        session_id: str,
        supplier_id: str,
        counter_price: float,
        justification: str
    ) -> Dict[str, Any]:
        """
        Submit counter-offer to supplier with SIMULATED RESPONSE.

        Simulates supplier decision logic:
        - If counter is within 10% of their last offer -> Accept or meet halfway
        - If counter is aggressive (>15% discount) -> Reject or smaller concession
        """

        session = self.db.query(NegotiationSession).filter_by(session_id=session_id).first()
        if not session:
            raise ValueError(f"Session {session_id} not found")

        # Get latest round for this supplier
        latest_round = (
            self.db.query(NegotiationRound)
            .filter_by(session_id=session_id, supplier_id=supplier_id)
            .order_by(NegotiationRound.round_number.desc())
            .first()
        )

        if not latest_round:
            raise ValueError(f"No previous round found for supplier {supplier_id}")

        # Update latest round with our counter
        latest_round.counter_price = counter_price
        latest_round.justification = justification
        latest_round.status = "countered"

        # SIMULATE: Supplier response logic
        their_price = float(latest_round.offered_price)
        discount_requested = (their_price - counter_price) / their_price * 100

        # Decision logic
        if discount_requested <= 5:
            # Small discount requested - likely to accept
            new_offered_price = counter_price
            response_status = "accepted"
        elif discount_requested <= 10:
            # Moderate discount - meet halfway
            new_offered_price = round((their_price + counter_price) / 2, 2)
            response_status = "countered"
        elif discount_requested <= 15:
            # Larger discount - smaller concession
            new_offered_price = round(their_price * 0.95, 2)  # 5% off
            response_status = "countered"
        else:
            # Aggressive discount - minimal movement
            new_offered_price = round(their_price * 0.97, 2)  # 3% off
            response_status = "countered"

        # Get session items for total value
        items = json.loads(session.items_json)
        quantity = items[0]["quantity"]
        new_total_value = round(new_offered_price * quantity, 2)

        # Create new round for supplier's response
        new_round_id = f"rnd-{uuid.uuid4().hex[:8]}"
        new_round_number = latest_round.round_number + 1

        new_round = NegotiationRound(
            round_id=new_round_id,
            session_id=session_id,
            supplier_id=supplier_id,
            round_number=new_round_number,
            offer_type="counter",
            offered_price=new_offered_price,
            total_value=new_total_value,
            status="received",
            response_received_at=datetime.now()
        )

        session.current_round = new_round_number
        self.db.add(new_round)
        self.db.commit()

        return {
            "round_id": new_round_id,
            "session_id": session_id,
            "supplier_id": supplier_id,
            "our_counter_price": counter_price,
            "their_response_price": new_offered_price,
            "total_value": new_total_value,
            "round_number": new_round_number,
            "status": response_status,
            "simulated": True,
            "discount_requested_percent": round(discount_requested, 2)
        }

    def accept_offer(
        self,
        session_id: str,
        supplier_id: str,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Accept supplier's offer and close negotiation."""

        session = self.db.query(NegotiationSession).filter_by(session_id=session_id).first()
        if not session:
            raise ValueError(f"Session {session_id} not found")

        # Get latest round for this supplier
        latest_round = (
            self.db.query(NegotiationRound)
            .filter_by(session_id=session_id, supplier_id=supplier_id)
            .order_by(NegotiationRound.round_number.desc())
            .first()
        )

        if not latest_round or latest_round.offered_price == 0:
            raise ValueError(f"No valid offer found from supplier {supplier_id}")

        # Update session
        session.status = "completed"
        session.winning_supplier_id = supplier_id
        session.final_price = latest_round.offered_price
        session.total_value = latest_round.total_value
        session.completed_at = datetime.now()

        # Update round
        latest_round.status = "accepted"

        self.db.commit()

        return {
            "session_id": session_id,
            "status": "completed",
            "winning_supplier_id": supplier_id,
            "final_price": float(session.final_price),
            "total_value": float(session.total_value),
            "items": json.loads(session.items_json),
            "target_price": float(session.target_price) if session.target_price else None,
            "rounds_completed": session.current_round,
            "notes": notes,
            "completed_at": session.completed_at.isoformat()
        }

    def get_status(self, session_id: str) -> Dict[str, Any]:
        """Get complete status of negotiation session."""

        session = self.db.query(NegotiationSession).filter_by(session_id=session_id).first()
        if not session:
            raise ValueError(f"Session {session_id} not found")

        rounds = (
            self.db.query(NegotiationRound)
            .filter_by(session_id=session_id)
            .order_by(NegotiationRound.round_number, NegotiationRound.created_at)
            .all()
        )

        rounds_data = []
        for r in rounds:
            rounds_data.append({
                "round_id": r.round_id,
                "supplier_id": r.supplier_id,
                "round_number": r.round_number,
                "offer_type": r.offer_type,
                "offered_price": float(r.offered_price) if r.offered_price else None,
                "total_value": float(r.total_value) if r.total_value else None,
                "counter_price": float(r.counter_price) if r.counter_price else None,
                "justification": r.justification,
                "status": r.status,
                "created_at": r.created_at.isoformat(),
                "response_received_at": r.response_received_at.isoformat() if r.response_received_at else None
            })

        return {
            "session_id": session_id,
            "status": session.status,
            "items": json.loads(session.items_json),
            "target_price": float(session.target_price) if session.target_price else None,
            "max_rounds": session.max_rounds,
            "current_round": session.current_round,
            "winning_supplier_id": session.winning_supplier_id,
            "final_price": float(session.final_price) if session.final_price else None,
            "total_value": float(session.total_value) if session.total_value else None,
            "created_at": session.created_at.isoformat(),
            "completed_at": session.completed_at.isoformat() if session.completed_at else None,
            "rounds": rounds_data
        }

    def compare_offers(self, session_id: str, criteria: str = "total_cost") -> Dict[str, Any]:
        """Compare all current offers and rank suppliers."""

        session = self.db.query(NegotiationSession).filter_by(session_id=session_id).first()
        if not session:
            raise ValueError(f"Session {session_id} not found")

        # Get latest offer from each supplier
        latest_offers = {}
        rounds = self.db.query(NegotiationRound).filter_by(session_id=session_id).all()

        for round_entry in rounds:
            if round_entry.status == "received" and round_entry.offered_price > 0:
                supplier_id = round_entry.supplier_id
                if supplier_id not in latest_offers or round_entry.round_number > latest_offers[supplier_id]["round_number"]:
                    supplier = self.db.query(Supplier).filter_by(supplier_id=supplier_id).first()
                    latest_offers[supplier_id] = {
                        "supplier_id": supplier_id,
                        "supplier_name": supplier.supplier_name if supplier else supplier_id,
                        "offered_price": float(round_entry.offered_price),
                        "total_value": float(round_entry.total_value),
                        "round_number": round_entry.round_number,
                        "on_time_rate": float(supplier.on_time_delivery_rate) if supplier and supplier.on_time_delivery_rate else None,
                        "quality_rating": float(supplier.quality_rating) if supplier and supplier.quality_rating else None
                    }

        # Rank by criteria
        ranked = list(latest_offers.values())
        if criteria == "price":
            ranked.sort(key=lambda x: x["offered_price"])
        elif criteria == "quality_adjusted":
            # Simple quality adjustment: price / (quality_rating * on_time_rate)
            for offer in ranked:
                quality_factor = (offer.get("quality_rating") or 3.0) / 5.0
                delivery_factor = (offer.get("on_time_rate") or 80.0) / 100.0
                offer["adjusted_score"] = offer["offered_price"] / (quality_factor * delivery_factor)
            ranked.sort(key=lambda x: x.get("adjusted_score", x["offered_price"]))
        else:  # total_cost
            ranked.sort(key=lambda x: x["total_value"])

        return {
            "session_id": session_id,
            "criteria": criteria,
            "target_price": float(session.target_price) if session.target_price else None,
            "offers_count": len(ranked),
            "ranked_suppliers": ranked,
            "best_offer": ranked[0] if ranked else None
        }
