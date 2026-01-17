#!/usr/bin/env python3
"""
Generate 500-1000 inventory records from Amazon CSV with realistic stock levels and costs.
"""
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.database.config import SessionLocal
from src.database.models import Product, Supplier
import pandas as pd
import requests
from io import StringIO
import random
from datetime import datetime

CSV_URL = "https://raw.githubusercontent.com/luminati-io/eCommerce-dataset-samples/refs/heads/main/amazon-products.csv"

# Category keywords for supplier mapping
SUPPLIER_KEYWORDS = {
    'TECH': ['electronic', 'computer', 'phone', 'tablet', 'camera', 'audio', 'headphone', 'speaker', 'charger', 'cable'],
    'HOME': ['home', 'kitchen', 'furniture', 'decor', 'bedding', 'bath', 'garden', 'tool'],
    'FASH': ['clothing', 'fashion', 'shoes', 'apparel', 'shirt', 'pants', 'dress', 'jacket'],
    'SPORT': ['sport', 'fitness', 'athletic', 'outdoor', 'running', 'exercise', 'gym', 'yoga'],
    'OFFICE': ['office', 'stationery', 'desk', 'pen', 'paper', 'notebook', 'organizer'],
    'BEAUTY': ['beauty', 'cosmetic', 'skincare', 'makeup', 'lotion', 'perfume', 'hair'],
    'GENERAL': []  # Catch-all
}


def match_supplier(title: str, brand: str, suppliers: list) -> str:
    """Match product to supplier based on title/brand keywords"""
    text = f"{title} {brand}".lower()

    # Check each supplier category
    for prefix, keywords in SUPPLIER_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            # Find supplier with matching prefix
            matching = [s for s in suppliers if s.supplier_id.startswith(prefix)]
            if matching:
                return random.choice(matching).supplier_id

    # Default to GENERAL supplier
    general = [s for s in suppliers if s.supplier_id.startswith('GENERAL')]
    return general[0].supplier_id if general else suppliers[0].supplier_id


def generate_stock_level() -> dict:
    """Generate realistic stock levels with distribution"""
    distribution = random.random()

    if distribution < 0.05:  # 5% out of stock
        on_hand = 0
    elif distribution < 0.20:  # 15% low stock
        on_hand = random.randint(1, 50)
    elif distribution < 0.80:  # 60% normal stock
        on_hand = random.randint(50, 200)
    else:  # 20% high stock
        on_hand = random.randint(200, 500)

    # Reserved is 0-20% of on-hand
    reserved = int(on_hand * random.uniform(0, 0.20)) if on_hand > 0 else 0

    # Reorder point is 10-30% of typical stock level
    reorder_point = max(10, int(on_hand * random.uniform(0.10, 0.30)))

    # Reorder quantity is 2-5x reorder point
    reorder_quantity = int(reorder_point * random.uniform(2, 5))

    return {
        'quantity_on_hand': on_hand,
        'quantity_reserved': reserved,
        'reorder_point': reorder_point,
        'reorder_quantity': reorder_quantity,
        'lead_time_days': random.randint(5, 14)
    }


def calculate_costs(market_price: float) -> dict:
    """Calculate unit cost and last purchase price based on market price"""
    if market_price <= 0:
        return {'unit_cost': 0.0, 'last_purchase_price': 0.0}

    # Unit cost is 40-70% of market price (realistic margin)
    unit_cost = round(market_price * random.uniform(0.40, 0.70), 2)

    # Last purchase price is unit_cost ± 10%
    last_purchase = round(unit_cost * random.uniform(0.90, 1.10), 2)

    return {
        'unit_cost': unit_cost,
        'last_purchase_price': last_purchase,
        'market_price': market_price,
        'price_last_updated': datetime.utcnow()
    }


def main():
    print("📦 Generating inventory data from Amazon CSV...")

    # Load CSV
    print(f"  Fetching CSV from {CSV_URL[:50]}...")
    response = requests.get(CSV_URL)
    df = pd.read_csv(StringIO(response.text))

    # Normalize columns
    df.columns = df.columns.str.strip().str.lower()
    print(f"  ✅ Loaded {len(df)} products from CSV")

    # Clean price column
    if 'final_price' in df.columns:
        df['price_cleaned'] = df['final_price'].astype(str).str.replace(r'[^\d.]', '', regex=True)
        df['price_cleaned'] = pd.to_numeric(df['price_cleaned'], errors='coerce').fillna(0.0)
    else:
        df['price_cleaned'] = 0.0

    # Fill missing values
    df['brand'] = df['brand'].fillna('Unknown')
    df['title'] = df['title'].fillna('Untitled Product')
    df['description'] = df.get('description', '').fillna('')

    # Filter out invalid products
    df = df[
        (df['asin'].notna()) &
        (df['asin'].str.len() > 0) &
        (df['title'].notna()) &
        (df['price_cleaned'] > 0)
    ].copy()

    # Limit to 500-1000 products
    target_count = random.randint(500, 1000)
    df = df.head(target_count)

    print(f"  📊 Generating inventory for {len(df)} products...")

    session = SessionLocal()
    try:
        # Get all suppliers for mapping
        suppliers = session.query(Supplier).all()
        if not suppliers:
            print("❌ No suppliers found! Run 01_generate_suppliers.py first.")
            return

        # Clear existing products
        session.query(Product).delete()
        session.commit()

        products_created = 0

        for idx, row in df.iterrows():
            # Match to supplier
            supplier_id = match_supplier(row['title'], row['brand'], suppliers)

            # Generate stock and pricing
            stock = generate_stock_level()
            costs = calculate_costs(row['price_cleaned'])

            # Create product
            product = Product(
                asin=str(row['asin']),
                title=str(row['title'])[:500],  # Limit length
                brand=str(row['brand'])[:100],
                description=str(row['description'])[:1000] if row['description'] else None,
                supplier_id=supplier_id,
                **stock,
                **costs
            )

            session.add(product)
            products_created += 1

            if products_created % 100 == 0:
                print(f"    ... {products_created} products created")

        session.commit()
        print(f"\n✅ Successfully created {products_created} products!")

        # Show distribution stats
        all_products = session.query(Product).all()
        out_of_stock = sum(1 for p in all_products if p.quantity_on_hand == 0)
        low_stock = sum(1 for p in all_products if 0 < p.quantity_on_hand <= 50)
        normal_stock = sum(1 for p in all_products if 50 < p.quantity_on_hand <= 200)
        high_stock = sum(1 for p in all_products if p.quantity_on_hand > 200)

        print(f"\n📊 Stock Distribution:")
        print(f"  Out of stock: {out_of_stock} ({out_of_stock/len(all_products)*100:.1f}%)")
        print(f"  Low stock (1-50): {low_stock} ({low_stock/len(all_products)*100:.1f}%)")
        print(f"  Normal (51-200): {normal_stock} ({normal_stock/len(all_products)*100:.1f}%)")
        print(f"  High (200+): {high_stock} ({high_stock/len(all_products)*100:.1f}%)")

    except Exception as e:
        session.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        session.close()


if __name__ == '__main__':
    main()
