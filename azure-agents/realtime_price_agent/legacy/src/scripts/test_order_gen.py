#!/usr/bin/env python3
"""
Simplified test of order generation to debug issues
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


def test_order_generation():
    """Test basic order generation logic"""
    print("🧪 Testing order generation...")

    # Load parameters
    params = load_order_parameters()
    price_tiers = params.get("price_tiers", {})
    print(f"Loaded {len(price_tiers)} price tiers")

    session = SessionLocal()
    try:
        # Get sample data
        suppliers = session.query(Supplier).all()
        products = session.query(Product).all()

        print(f"Found {len(suppliers)} suppliers and {len(products)} products")

        # Test generating one order
        supplier = suppliers[0]
        supplier_products = [
            p for p in products if p.supplier_id == supplier.supplier_id
        ][:3]

        print(
            f"Testing with supplier {supplier.supplier_id} and {len(supplier_products)} products"
        )

        # Test the full order generation logic
        for i in range(2):  # Test 2 orders
            print(f"\n--- Testing Order {i + 1} ---")

            # Select supplier
            supplier = suppliers[i % len(suppliers)]
            print(f"Supplier: {supplier.supplier_id}")

            # Get products
            supplier_products = [
                p for p in products if p.supplier_id == supplier.supplier_id
            ]
            if not supplier_products:
                supplier_products = products[:10]  # Fallback
            print(f"Available products: {len(supplier_products)}")

            # Select random products for order
            num_items = min(3, len(supplier_products))
            order_products = random.sample(supplier_products, num_items)
            print(f"Order items: {num_items}")

            total_cost = 0.0
            for product in order_products:
                market_price = (
                    float(product.market_price) if product.market_price else 0.0
                )
                unit_cost = float(product.unit_cost) if product.unit_cost else 10.0
                price = market_price or unit_cost

                # Find price tier
                price_tier = None
                for tier, config in price_tiers.items():
                    if config["min"] <= price <= config["max"]:
                        price_tier = tier
                        break

                if price_tier and price_tier in price_tiers:
                    config = price_tiers[price_tier]
                    quantity = np.random.normal(
                        config["avg_quantity"], config["std_quantity"]
                    )
                    quantity = max(1, min(config["max_quantity"], int(quantity)))

                    unit_price = float(product.unit_cost or 10.0)
                    line_cost = quantity * unit_price
                    total_cost += line_cost

                    print(
                        f"  {product.asin}: tier={price_tier}, qty={quantity}, unit=${unit_price:.2f}, line=${line_cost:.2f}"
                    )

            print(f"  Total cost: ${total_cost:.2f}")

        session.close()
        print("✅ Test completed successfully")

    except Exception as e:
        session.close()
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_order_generation()
