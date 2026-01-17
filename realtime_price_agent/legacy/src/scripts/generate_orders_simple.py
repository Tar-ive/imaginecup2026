#!/usr/bin/env python3
"""
Simplified order generation using statistical parameters
"""

import sys
import os
import json
import numpy as np
from datetime import datetime, timedelta
import random

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.database.config import SessionLocal
from src.database.models import Product, Supplier, PurchaseOrder, PurchaseOrderItem


def load_order_parameters():
    """Load statistical parameters"""
    params_file = os.path.join(
        os.path.dirname(__file__), "order_generation_params.json"
    )
    try:
        with open(params_file, "r") as f:
            return json.load(f)
    except:
        return {}


def classify_price_tier(price: float, price_tiers: dict) -> str:
    """Classify a price into tier"""
    for tier, config in price_tiers.items():
        if config["min"] <= price <= config["max"]:
            return tier
    return "medium"


def generate_quantity_for_price_tier(price_tier: str, price_tiers: dict) -> int:
    """Generate quantity based on statistical distribution"""
    if price_tier not in price_tiers:
        return random.randint(1, 10)

    config = price_tiers[price_tier]
    quantity = np.random.normal(config["avg_quantity"], config["std_quantity"])
    return max(1, min(config["max_quantity"], int(quantity)))


def generate_orders():
    """Generate purchase orders using statistical parameters"""
    print("📋 Generating purchase orders with statistical parameters...")

    # Load parameters
    params = load_order_parameters()
    price_tiers = params.get("price_tiers", {})
    print(f"Loaded {len(price_tiers)} price tiers")

    session = SessionLocal()
    try:
        # Get data
        suppliers = session.query(Supplier).all()
        products = session.query(Product).all()
        print(f"Found {len(suppliers)} suppliers and {len(products)} products")

        # Clear existing orders
        session.query(PurchaseOrderItem).delete()
        session.query(PurchaseOrder).delete()
        session.commit()

        # Generate orders
        num_orders = 10  # Start with 10 for testing
        orders_created = 0

        for i in range(num_orders):
            # Select random supplier
            supplier = random.choice(suppliers)

            # Get supplier's products
            supplier_products = [
                p for p in products if p.supplier_id == supplier.supplier_id
            ]
            if not supplier_products:
                supplier_products = products[:20]  # Fallback

            # Select 2-8 products for this order
            num_items = random.randint(2, 8)
            order_products = random.sample(
                supplier_products, min(num_items, len(supplier_products))
            )

            # Generate order date (last 90 days)
            days_ago = random.randint(0, 90)
            order_date = datetime.now() - timedelta(days=days_ago)

            # Create order
            po_number = f"PO-{datetime.now().strftime('%Y%m%d')}-{i + 1:03d}"

            total_cost = 0.0
            order_items = []

            for product in order_products:
                # Get product price
                market_price = float(product.market_price or 0)
                unit_cost = float(product.unit_cost or 10.0)
                price = market_price or unit_cost

                # Classify price tier
                price_tier = classify_price_tier(price, price_tiers)

                # Generate quantity
                quantity = generate_quantity_for_price_tier(price_tier, price_tiers)

                # Calculate unit price with variance
                unit_price = (
                    round(unit_cost * random.uniform(0.95, 1.05), 2)
                    if unit_cost
                    else 10.0
                )

                # Create order item
                item = PurchaseOrderItem(
                    po_number=po_number,
                    asin=product.asin,
                    quantity_ordered=quantity,
                    quantity_received=quantity,  # Assume all received for simplicity
                    unit_price=unit_price,
                )

                order_items.append(item)
                total_cost += quantity * unit_price

            # Determine status (simple logic)
            if order_date < datetime.now() - timedelta(days=30):
                status = random.choice(
                    ["received", "received", "cancelled"]
                )  # Mostly received
            else:
                status = random.choice(["pending", "shipped"])

            # Calculate delivery dates
            lead_time = int(supplier.default_lead_time_days or 7)
            expected_delivery = order_date + timedelta(days=lead_time)

            if status == "received":
                actual_delivery = expected_delivery + timedelta(
                    days=random.randint(-2, 3)
                )
            else:
                actual_delivery = None

            # Create purchase order
            po = PurchaseOrder(
                po_number=po_number,
                supplier_id=supplier.supplier_id,
                order_date=order_date,
                expected_delivery_date=expected_delivery,
                actual_delivery_date=actual_delivery,
                total_cost=total_cost,
                status=status,
                created_by="system",
            )

            # Add to session
            session.add(po)
            for item in order_items:
                session.add(item)

            orders_created += 1
            print(f"  Created order {orders_created} with {len(order_items)} items")

            if orders_created >= 2:  # Stop after 2 orders for testing
                print("Stopping after 2 orders for testing")
                break

        print("Committing to database...")
        session.commit()
        print("Commit successful")
        print(f"✅ Successfully created {orders_created} purchase orders!")

        # Count items
        total_items = session.query(PurchaseOrderItem).count()
        print(f"  Total order items: {total_items}")

    except Exception as e:
        session.rollback()
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
    finally:
        session.close()


if __name__ == "__main__":
    generate_orders()
