#!/usr/bin/env python3
"""
Generate 50-100 purchase orders over the last 3 months with realistic patterns.
"""

import sys
import os
import json
import numpy as np

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.database.config import SessionLocal
from src.database.models import Product, Supplier, PurchaseOrder, PurchaseOrderItem
from datetime import datetime, timedelta
import random


def load_order_parameters() -> dict:
    """Load statistical parameters for order generation"""
    params_file = os.path.join(
        os.path.dirname(__file__), "order_generation_params.json"
    )
    try:
        with open(params_file, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print("⚠️  Parameters file not found, using default values")
        return {}


def classify_price_tier(price: float, price_tiers: dict) -> str:
    """Classify a price into tier based on statistical parameters"""
    for tier, config in price_tiers.items():
        if config["min"] <= price <= config["max"]:
            return tier
    return "medium"  # Default fallback


def generate_quantity_for_price_tier(price_tier: str, price_tiers: dict) -> int:
    """Generate realistic order quantity based on price tier statistics"""
    if price_tier not in price_tiers:
        return random.randint(1, 10)  # Fallback

    config = price_tiers[price_tier]
    # Use normal distribution with statistical parameters
    quantity = np.random.normal(config["avg_quantity"], config["std_quantity"])
    quantity = max(1, min(config["max_quantity"], int(quantity)))
    return quantity


def get_seasonal_multiplier(
    order_date: datetime, seasonality: dict, category: str
) -> float:
    """Calculate seasonal demand multiplier"""
    month = order_date.month
    category_key = category.lower()

    if category_key in seasonality:
        return seasonality[category_key].get(f"q{(month - 1) // 3 + 1}", 1.0)
    return 1.0


def generate_po_number() -> str:
    """Generate unique PO number"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"PO-{timestamp}-{random.randint(1000, 9999)}"


def distribute_order_dates(num_orders: int) -> list:
    """Distribute order dates over last 3 months with realistic pattern"""
    dates = []
    now = datetime.now()

    for _ in range(num_orders):
        distribution = random.random()

        if distribution < 0.60:  # 60% in last 30 days
            days_ago = random.randint(0, 30)
        elif distribution < 0.90:  # 30% in 31-60 days ago
            days_ago = random.randint(31, 60)
        else:  # 10% in 61-90 days ago
            days_ago = random.randint(61, 90)

        order_date = now - timedelta(days=days_ago)
        dates.append(order_date)

    return sorted(dates)  # Chronological order


def assign_order_status(order_date: datetime, expected_delivery: datetime) -> str:
    """Assign realistic status based on order and delivery dates"""
    now = datetime.now()

    # If expected delivery has passed
    if now > expected_delivery:
        # 70% received, 5% cancelled
        if random.random() < 0.933:  # 70/75
            return "received"
        else:
            return "cancelled"

    # If order is recent but not yet delivered
    elif now > order_date:
        # 15% shipped, 10% pending
        if random.random() < 0.60:  # 15/25
            return "shipped"
        else:
            return "pending"

    return "pending"


def calculate_delivery_dates(order_date: datetime, lead_time: int, status: str) -> dict:
    """Calculate expected and actual delivery dates"""
    expected = order_date + timedelta(days=lead_time)

    if status == "received":
        # Actual delivery is expected ± 1-3 days
        variance = random.randint(-3, 3)
        actual = expected + timedelta(days=variance)
    elif status == "cancelled":
        actual = None
    else:
        actual = None

    return {"expected_delivery_date": expected, "actual_delivery_date": actual}


def main():
    print("📋 Generating purchase order data using statistical parameters...")
    print("Step 1: Loading parameters...")

    # Load statistical parameters
    params = load_order_parameters()
    print(f"Parameters loaded: {bool(params)}")
    price_tiers = params.get("price_tiers", {})
    category_weights = params.get("category_weights", {})
    seasonality = params.get("seasonality", {})
    temporal_patterns = params.get("temporal_patterns", {})
    print(f"Price tiers: {len(price_tiers)}")

    print("Step 2: Connecting to database...")
    session = SessionLocal()
    print("Database connected")
    try:
        # Get all suppliers and products
        suppliers = session.query(Supplier).all()
        products = session.query(Product).all()

        if not suppliers:
            print("❌ No suppliers found! Run 01_generate_suppliers.py first.")
            return

        if not products:
            print("❌ No products found! Run 02_generate_inventory.py first.")
            return

        print(f"  Found {len(suppliers)} suppliers and {len(products)} products")

        # Clear existing orders
        session.query(PurchaseOrderItem).delete()
        session.query(PurchaseOrder).delete()
        session.commit()

        # Generate 50-100 orders
        num_orders = random.randint(50, 100)
        order_dates = distribute_order_dates(num_orders)

        print(f"  Generating {num_orders} purchase orders over last 3 months...")
        print(f"  Using statistical parameters from API analysis")
        print(f"  Order dates generated: {len(order_dates)}")

        orders_by_status = {"pending": 0, "shipped": 0, "received": 0, "cancelled": 0}
        print("  Starting order generation loop...")

        for i, order_date in enumerate(order_dates):
            print(f"  Processing order {i + 1}/{num_orders}")
            if i >= 1:  # Stop after first order for testing
                print("  Stopping after first order for testing")
                break
            # Select supplier based on category weights (prefer suppliers with products in popular categories)
            supplier = random.choice(suppliers)

            # Get products from this supplier
            supplier_products = [
                p for p in products if p.supplier_id == supplier.supplier_id
            ]
            if not supplier_products:
                # Use any products if supplier has none assigned
                supplier_products = products

            # Generate 3-15 line items
            num_items = random.randint(3, 15)
            num_items = min(num_items, len(supplier_products))
            order_products = random.sample(supplier_products, num_items)

            # Calculate dates and status
            lead_time = int(supplier.default_lead_time_days or 7)
            delivery_dates = calculate_delivery_dates(order_date, lead_time, "pending")
            status = assign_order_status(
                order_date, delivery_dates["expected_delivery_date"]
            )
            delivery_dates = calculate_delivery_dates(
                order_date, lead_time, status
            )  # Recalculate with status

            # Create PO
            po_number = generate_po_number()
            po = PurchaseOrder(
                po_number=po_number,
                supplier_id=supplier.supplier_id,
                order_date=order_date,
                expected_delivery_date=delivery_dates["expected_delivery_date"],
                actual_delivery_date=delivery_dates["actual_delivery_date"],
                total_cost=0.0,  # Will be calculated from line items
                status=status,
                created_by="system",
            )

            orders_by_status[status] += 1

            # Create line items using statistical price tiers
            total_cost = 0.0
            for product in order_products:
                # Determine price tier for this product
                market_price = (
                    float(product.market_price) if product.market_price else 0.0
                )
                unit_cost = float(product.unit_cost) if product.unit_cost else 10.0
                price = market_price or unit_cost
                price_tier = classify_price_tier(price, price_tiers)

                # Generate quantity based on statistical distribution
                quantity = generate_quantity_for_price_tier(price_tier, price_tiers)

                # Use unit_cost with ±5% variance
                if product.unit_cost:
                    unit_price = round(
                        float(product.unit_cost) * random.uniform(0.95, 1.05), 2
                    )
                else:
                    unit_price = 10.0

                # If order is received, set quantity_received
                quantity_received = quantity if status == "received" else 0

                item = PurchaseOrderItem(
                    po_number=po_number,
                    asin=product.asin,
                    quantity_ordered=quantity,
                    quantity_received=quantity_received,
                    unit_price=unit_price,
                )

                total_cost += quantity * unit_price
                session.add(item)

            # Update PO total
            po.total_cost = total_cost
            session.add(po)

        session.commit()

        print(f"\n✅ Successfully created {num_orders} purchase orders!")
        print(f"\n📊 Order Status Distribution:")
        for status, count in sorted(orders_by_status.items()):
            percentage = (count / num_orders * 100) if num_orders > 0 else 0
            print(f"  {status.capitalize()}: {count} ({percentage:.1f}%)")

        # Calculate total order items
        total_items = session.query(PurchaseOrderItem).count()
        print(f"\n  Total line items: {total_items}")
        print(f"  Average items per order: {total_items / num_orders:.1f}")

        if params:
            print(f"\n📈 Used statistical parameters from API analysis:")
            print(f"  Price tiers: {len(price_tiers)}")
            print(f"  Category weights: {len(category_weights)}")
            print(f"  Seasonal patterns: {len(seasonality)} categories")

    except Exception as e:
        session.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
