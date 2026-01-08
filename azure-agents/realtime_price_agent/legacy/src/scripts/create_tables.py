#!/usr/bin/env python3
"""
Create database tables in Neon Postgres using SQLAlchemy.
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.database.config import engine, Base, test_connection


def main():
    print("🛠️  Creating database tables...")

    # Test connection first
    if not test_connection():
        print("❌ Cannot connect to database. Check your DATABASE_URL in .env")
        sys.exit(1)

    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created successfully!")
        print(
            "Created tables: suppliers, products, purchase_orders, purchase_order_items"
        )

    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        raise


if __name__ == "__main__":
    main()
