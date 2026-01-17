#!/usr/bin/env python3
"""
Create database tables using pymssql (TDS protocol)
"""

from dotenv import load_dotenv
import os
import pymssql

# Load environment variables
load_dotenv()


def create_tables():
    """Create the 4 database tables using TDS connection"""

    server = os.getenv("AZURE_SQL_SERVER")
    database = os.getenv("AZURE_SQL_DATABASE")

    print("🔄 Connecting to Azure SQL Database...")
    print(f"Server: {server}")
    print(f"Database: {database}")

    try:
        # Connect using managed identity (no username/password needed)
        # pymssql will use the default credential chain
        conn = pymssql.connect(
            server=server,
            database=database,
            # For managed identity, we don't specify user/password
            # It uses the Azure CLI or managed identity automatically
        )

        cursor = conn.cursor()
        print("✅ Connected successfully!")

        # Create suppliers table
        print("🔄 Creating suppliers table...")
        cursor.execute("""
        IF OBJECT_ID('suppliers', 'U') IS NULL
        CREATE TABLE suppliers (
            supplier_id VARCHAR(50) PRIMARY KEY,
            supplier_name NVARCHAR(100) NOT NULL,
            contact_person NVARCHAR(100),
            email VARCHAR(255),
            phone VARCHAR(50),
            address NVARCHAR(500),
            city NVARCHAR(100),
            state_province NVARCHAR(100),
            country NVARCHAR(100),
            postal_code VARCHAR(20),
            payment_terms VARCHAR(100),
            default_lead_time_days INT DEFAULT 7,
            on_time_delivery_rate DECIMAL(5, 2),
            quality_rating DECIMAL(3, 2),
            created_at DATETIME2 DEFAULT GETDATE(),
            is_active BIT DEFAULT 1
        );
        """)
        print("✅ Suppliers table created")

        # Create products table
        print("🔄 Creating products table...")
        cursor.execute("""
        IF OBJECT_ID('products', 'U') IS NULL
        CREATE TABLE products (
            asin VARCHAR(20) PRIMARY KEY,
            title NVARCHAR(500) NOT NULL,
            brand NVARCHAR(100),
            description NVARCHAR(MAX),
            unit_cost DECIMAL(10, 2),
            last_purchase_price DECIMAL(10, 2),
            market_price DECIMAL(10, 2),
            price_last_updated DATETIME2,
            quantity_on_hand INT NOT NULL DEFAULT 0,
            quantity_reserved INT DEFAULT 0,
            quantity_available AS (quantity_on_hand - quantity_reserved),
            reorder_point INT DEFAULT 10,
            reorder_quantity INT DEFAULT 50,
            lead_time_days INT DEFAULT 7,
            supplier_id VARCHAR(50),
            is_active BIT DEFAULT 1,
            created_at DATETIME2 DEFAULT GETDATE(),
            updated_at DATETIME2 DEFAULT GETDATE(),
            FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id)
        );
        """)
        print("✅ Products table created")

        # Create purchase orders table
        print("🔄 Creating purchase_orders table...")
        cursor.execute("""
        IF OBJECT_ID('purchase_orders', 'U') IS NULL
        CREATE TABLE purchase_orders (
            po_number VARCHAR(50) PRIMARY KEY,
            supplier_id VARCHAR(50),
            order_date DATETIME2 DEFAULT GETDATE(),
            expected_delivery_date DATETIME2,
            actual_delivery_date DATETIME2,
            total_cost DECIMAL(10, 2) DEFAULT 0,
            status VARCHAR(20) DEFAULT 'pending',
            item_count INT DEFAULT 0,
            created_by VARCHAR(100) DEFAULT 'system',
            created_at DATETIME2 DEFAULT GETDATE(),
            is_delivered AS (CASE WHEN actual_delivery_date IS NOT NULL THEN 1 ELSE 0 END),
            FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id)
        );
        """)
        print("✅ Purchase orders table created")

        # Create purchase order items table
        print("🔄 Creating purchase_order_items table...")
        cursor.execute("""
        IF OBJECT_ID('purchase_order_items', 'U') IS NULL
        CREATE TABLE purchase_order_items (
            po_item_id INT IDENTITY(1,1) PRIMARY KEY,
            po_number VARCHAR(50),
            asin VARCHAR(20),
            quantity_ordered INT NOT NULL,
            quantity_received INT DEFAULT 0,
            unit_price DECIMAL(10, 2) NOT NULL,
            line_total AS (quantity_ordered * unit_price),
            is_fully_received AS (CASE WHEN quantity_received >= quantity_ordered THEN 1 ELSE 0 END),
            FOREIGN KEY (po_number) REFERENCES purchase_orders(po_number),
            FOREIGN KEY (asin) REFERENCES products(asin)
        );
        """)
        print("✅ Purchase order items table created")

        # Create indexes
        print("🔄 Creating indexes...")
        cursor.execute("CREATE INDEX idx_supplier_name ON suppliers(supplier_name);")
        cursor.execute("CREATE INDEX idx_product_brand ON products(brand);")
        cursor.execute("CREATE INDEX idx_product_supplier ON products(supplier_id);")
        cursor.execute("CREATE INDEX idx_po_supplier ON purchase_orders(supplier_id);")
        cursor.execute("CREATE INDEX idx_po_status ON purchase_orders(status);")
        cursor.execute(
            "CREATE INDEX idx_poi_po_number ON purchase_order_items(po_number);"
        )
        cursor.execute("CREATE INDEX idx_poi_asin ON purchase_order_items(asin);")
        print("✅ Indexes created")

        conn.commit()
        print("✅ All changes committed!")

        # Verify tables were created
        print("🔄 Verifying table creation...")
        cursor.execute("""
        SELECT name, type_desc
        FROM sys.objects
        WHERE type = 'U' AND name IN ('suppliers', 'products', 'purchase_orders', 'purchase_order_items')
        ORDER BY name
        """)

        tables = cursor.fetchall()
        table_names = [row[0] for row in tables]
        print(f"✅ Tables verified: {table_names}")

        if len(table_names) == 4:
            print("🎉 SUCCESS: All 4 tables created and verified!")
            return True
        else:
            print(f"❌ ERROR: Expected 4 tables, found {len(table_names)}")
            return False

    except Exception as e:
        print(f"❌ Failed: {str(e)}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        if "conn" in locals():
            conn.close()


if __name__ == "__main__":
    success = create_tables()
    if success:
        print("\n🚀 Next steps:")
        print("1. Run: python src/scripts/01_generate_suppliers.py")
        print("2. Run: python src/scripts/02_generate_inventory.py")
        print("3. Run: python src/scripts/03_generate_orders.py")
        print("4. Run: python src/scripts/verify_data.py")
    else:
        print(
            "\n❌ Please check the error messages above and resolve issues before proceeding."
        )
