#!/usr/bin/env python3
"""
Validate data quality after population.
Checks foreign keys, distributions, and database size.
"""
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.database.config import SessionLocal, engine
from src.database.models import Product, Supplier, PurchaseOrder, PurchaseOrderItem
from src.database.connection import get_table_counts, validate_foreign_keys
from sqlalchemy import text


def get_database_size():
    """Get database size in MB"""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT
                SUM(CAST(FILEPROPERTY(name, 'SpaceUsed') AS bigint) * 8.0 / 1024) as size_mb
            FROM sys.database_files
            WHERE type = 0  -- Data files only
        """))
        row = result.fetchone()
        return round(row[0], 2) if row and row[0] else 0


def check_stock_distribution():
    """Verify stock level distribution matches expected pattern"""
    session = SessionLocal()
    try:
        total = session.query(Product).count()
        out_of_stock = session.query(Product).filter(Product.quantity_on_hand == 0).count()
        low_stock = session.query(Product).filter(
            Product.quantity_on_hand > 0,
            Product.quantity_on_hand <= 50
        ).count()
        normal = session.query(Product).filter(
            Product.quantity_on_hand > 50,
            Product.quantity_on_hand <= 200
        ).count()
        high = session.query(Product).filter(Product.quantity_on_hand > 200).count()

        return {
            'total': total,
            'out_of_stock': (out_of_stock, out_of_stock/total*100 if total > 0 else 0),
            'low_stock': (low_stock, low_stock/total*100 if total > 0 else 0),
            'normal': (normal, normal/total*100 if total > 0 else 0),
            'high': (high, high/total*100 if total > 0 else 0)
        }
    finally:
        session.close()


def check_order_status_distribution():
    """Verify order status distribution"""
    session = SessionLocal()
    try:
        total = session.query(PurchaseOrder).count()
        statuses = {}

        for status in ['pending', 'shipped', 'received', 'cancelled']:
            count = session.query(PurchaseOrder).filter(PurchaseOrder.status == status).count()
            statuses[status] = (count, count/total*100 if total > 0 else 0)

        return {'total': total, 'statuses': statuses}
    finally:
        session.close()


def check_date_ranges():
    """Verify order dates are within last 3 months"""
    session = SessionLocal()
    try:
        from datetime import datetime, timedelta

        three_months_ago = datetime.now() - timedelta(days=90)

        old_orders = session.query(PurchaseOrder).filter(
            PurchaseOrder.order_date < three_months_ago
        ).count()

        total_orders = session.query(PurchaseOrder).count()

        return {
            'total_orders': total_orders,
            'orders_older_than_3_months': old_orders,
            'all_within_range': old_orders == 0
        }
    finally:
        session.close()


def main():
    print("🔍 Verifying database data quality...")
    print()

    # 1. Table counts
    print("📊 Table Counts:")
    counts = get_table_counts()
    for table, count in counts.items():
        print(f"  {table}: {count}")
    print()

    # 2. Database size
    print("💾 Database Size:")
    size_mb = get_database_size()
    print(f"  {size_mb:.2f} MB")
    if size_mb >= 32:
        print("  ⚠️  WARNING: Database size exceeds Azure Free tier limit (32 MB)")
    else:
        print(f"  ✅ Within Azure Free tier limit ({32 - size_mb:.2f} MB remaining)")
    print()

    # 3. Foreign key integrity
    print("🔗 Foreign Key Validation:")
    fk_issues = validate_foreign_keys()
    if fk_issues:
        print("  ❌ Found issues:")
        for issue in fk_issues:
            print(f"    - {issue}")
    else:
        print("  ✅ All foreign keys valid")
    print()

    # 4. Stock distribution
    print("📦 Stock Level Distribution:")
    stock_dist = check_stock_distribution()
    print(f"  Total products: {stock_dist['total']}")
    print(f"  Out of stock: {stock_dist['out_of_stock'][0]} ({stock_dist['out_of_stock'][1]:.1f}%) - Target: ~5%")
    print(f"  Low (1-50): {stock_dist['low_stock'][0]} ({stock_dist['low_stock'][1]:.1f}%) - Target: ~15%")
    print(f"  Normal (51-200): {stock_dist['normal'][0]} ({stock_dist['normal'][1]:.1f}%) - Target: ~60%")
    print(f"  High (200+): {stock_dist['high'][0]} ({stock_dist['high'][1]:.1f}%) - Target: ~20%")
    print()

    # 5. Order status distribution
    print("📋 Order Status Distribution:")
    order_dist = check_order_status_distribution()
    print(f"  Total orders: {order_dist['total']}")
    for status, (count, pct) in order_dist['statuses'].items():
        target = {'received': '~70%', 'shipped': '~15%', 'pending': '~10%', 'cancelled': '~5%'}
        print(f"  {status.capitalize()}: {count} ({pct:.1f}%) - Target: {target.get(status, 'N/A')}")
    print()

    # 6. Date ranges
    print("📅 Order Date Ranges:")
    date_check = check_date_ranges()
    print(f"  Total orders: {date_check['total_orders']}")
    print(f"  Orders older than 3 months: {date_check['orders_older_than_3_months']}")
    if date_check['all_within_range']:
        print("  ✅ All orders within last 3 months")
    else:
        print("  ⚠️  Some orders are older than 3 months")
    print()

    # Final summary
    print("="*60)
    all_good = (
        not fk_issues and
        size_mb < 32 and
        date_check['all_within_range'] and
        counts['suppliers'] >= 10 and
        counts['products'] >= 500 and
        counts['purchase_orders'] >= 50
    )

    if all_good:
        print("✅ ALL CHECKS PASSED! Database is ready for use.")
    else:
        print("⚠️  Some checks failed. Review warnings above.")
    print("="*60)


if __name__ == '__main__':
    main()
