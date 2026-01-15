"""
Database connection management and utilities.
Provides helper functions for database operations.
"""
from sqlalchemy import text
from .config import engine, SessionLocal, Base
from . import models  # Import models to register them with Base


def create_tables():
    """
    Create all tables defined in models.
    Note: This uses SQLAlchemy's create_all, which may not match
    the exact SQL in schema.sql. For production, deploy schema.sql directly.
    """
    print("Creating tables from SQLAlchemy models...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tables created successfully!")


def drop_tables():
    """Drop all tables. USE WITH CAUTION!"""
    print("⚠️  Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    print("✅ Tables dropped!")


def execute_sql_file(sql_file_path: str):
    """
    Execute SQL script from file (e.g., schema.sql).
    Handles GO statements by splitting script into batches.
    """
    print(f"Executing SQL script: {sql_file_path}")

    with open(sql_file_path, 'r') as f:
        sql_script = f.read()

    # Split by GO statements (SQL Server batch separator)
    batches = sql_script.split('GO')

    with engine.begin() as connection:
        for i, batch in enumerate(batches, 1):
            batch = batch.strip()
            if batch:  # Skip empty batches
                try:
                    connection.execute(text(batch))
                    print(f"  Batch {i}: ✅")
                except Exception as e:
                    print(f"  Batch {i}: ❌ {e}")
                    raise

    print("✅ SQL script executed successfully!")


def get_table_counts():
    """Get row counts for all tables"""
    counts = {}

    with SessionLocal() as session:
        counts['suppliers'] = session.query(models.Supplier).count()
        counts['products'] = session.query(models.Product).count()
        counts['purchase_orders'] = session.query(models.PurchaseOrder).count()
        counts['purchase_order_items'] = session.query(models.PurchaseOrderItem).count()

    return counts


def validate_foreign_keys():
    """Validate all foreign key relationships"""
    issues = []

    with SessionLocal() as session:
        # Check products -> suppliers
        products_without_supplier = session.query(models.Product).filter(
            models.Product.supplier_id.isnot(None)
        ).filter(
            ~models.Product.supplier_id.in_(
                session.query(models.Supplier.supplier_id)
            )
        ).count()

        if products_without_supplier > 0:
            issues.append(f"{products_without_supplier} products have invalid supplier_id")

        # Check purchase_orders -> suppliers
        pos_without_supplier = session.query(models.PurchaseOrder).filter(
            ~models.PurchaseOrder.supplier_id.in_(
                session.query(models.Supplier.supplier_id)
            )
        ).count()

        if pos_without_supplier > 0:
            issues.append(f"{pos_without_supplier} purchase orders have invalid supplier_id")

        # Check purchase_order_items -> purchase_orders
        items_without_po = session.query(models.PurchaseOrderItem).filter(
            ~models.PurchaseOrderItem.po_number.in_(
                session.query(models.PurchaseOrder.po_number)
            )
        ).count()

        if items_without_po > 0:
            issues.append(f"{items_without_po} order items have invalid po_number")

        # Check purchase_order_items -> products
        items_without_product = session.query(models.PurchaseOrderItem).filter(
            ~models.PurchaseOrderItem.asin.in_(
                session.query(models.Product.asin)
            )
        ).count()

        if items_without_product > 0:
            issues.append(f"{items_without_product} order items have invalid asin")

    return issues


if __name__ == '__main__':
    # Test connection
    from .config import test_connection
    test_connection()
