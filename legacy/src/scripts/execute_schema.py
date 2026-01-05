#!/usr/bin/env python3
"""
Execute the Postgres schema SQL file.
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.database.config import engine
from sqlalchemy import text


def main():
    print("🛠️  Executing schema SQL...")

    # Read the schema file
    schema_path = os.path.join(os.path.dirname(__file__), "../../schema_postgres.sql")
    with open(schema_path, "r") as f:
        schema_sql = f.read()

    try:
        with engine.connect() as conn:
            # Execute the entire schema at once
            print("Executing schema...")
            conn.execute(text(schema_sql))
            conn.commit()
        print("✅ Schema executed successfully!")

    except Exception as e:
        print(f"❌ Error executing schema: {e}")
        raise


if __name__ == "__main__":
    main()
