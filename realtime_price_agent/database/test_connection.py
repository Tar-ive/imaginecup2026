#!/usr/bin/env python3
"""
Test script for Azure SQL managed identity authentication and table creation
"""

from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()
print("✅ Environment variables loaded")


def test_managed_identity_connection():
    """Test managed identity connection and create tables"""

    server = os.getenv("AZURE_SQL_SERVER")
    database = os.getenv("AZURE_SQL_DATABASE")
    driver = os.getenv("AZURE_SQL_DRIVER", "ODBC Driver 18 for SQL Server")

    print("🔄 Testing managed identity authentication...")
    print(f"Server: {server}")
    print(f"Database: {database}")
    print(f"Driver: {driver}")

    if not server or not database:
        print("❌ Missing environment variables")
        return False

    try:
        # Try different credential types for macOS development
        from azure.identity import (
            AzureCliCredential,
            ManagedIdentityCredential,
            DefaultAzureCredential,
        )

        credential = None
        cred_type = ""

        # Try Azure CLI first (most common for development)
        try:
            credential = AzureCliCredential()
            cred_type = "Azure CLI"
            print("✅ Using Azure CLI credential")
        except Exception as e:
            print(f"⚠️ Azure CLI credential failed: {e}")
            try:
                credential = ManagedIdentityCredential()
                cred_type = "Managed Identity"
                print("✅ Using managed identity credential")
            except Exception as e2:
                print(f"⚠️ Managed identity failed: {e2}")
                credential = DefaultAzureCredential()
                cred_type = "Default"
                print("✅ Using default credential")

        print(f"🔄 Getting access token using {cred_type}...")
        token = credential.get_token("https://database.windows.net/.default")
        print("✅ Access token obtained")

        # Create connection
        from sqlalchemy import create_engine, text
        import pyodbc

        conn_str = (
            f"DRIVER={{{driver}}};"
            f"SERVER={server};"
            f"DATABASE={database};"
            "Encrypt=yes;"
            "TrustServerCertificate=no;"
            "Connection Timeout=30;"
        )

        print("🔄 Creating SQLAlchemy engine...")
        engine = create_engine(
            f"mssql+pyodbc:///?odbc_connect={conn_str}",
            connect_args={
                "attrs_before": {
                    1256: token.token  # SQL_COPT_SS_ACCESS_TOKEN
                }
            },
        )

        # Test connection
        print("🔄 Testing database connection...")
        with engine.connect() as conn:
            result = conn.execute(text("SELECT @@VERSION as version"))
            row = result.fetchone()
            version = row[0]
            print(f"✅ Connected to SQL Database: {version[:80]}...")

            # Create database user for managed identity
            print("🔄 Creating database user for managed identity...")
            conn.execute(
                text("""
                IF NOT EXISTS (SELECT * FROM sys.database_principals WHERE name = 'id-api-2oy26vbxhdqti')
                BEGIN
                    CREATE USER [id-api-2oy26vbxhdqti] FROM EXTERNAL PROVIDER;
                    ALTER ROLE db_owner ADD MEMBER [id-api-2oy26vbxhdqti];
                END
            """)
            )
            conn.commit()
            print("✅ Database user created and permissions granted")

            # Create the 4 tables
            print("🔄 Creating database tables...")

            # Suppliers table
            conn.execute(
                text("""
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
            )

            # Products table
            conn.execute(
                text("""
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
            )

            # Purchase Orders table
            conn.execute(
                text("""
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
            )

            # Purchase Order Items table
            conn.execute(
                text("""
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
            )

            conn.commit()
            print("✅ All 4 tables created successfully!")

            # Verify tables were created
            print("🔄 Verifying table creation...")
            result = conn.execute(
                text("""
                SELECT name, type_desc
                FROM sys.objects
                WHERE type = 'U' AND name IN ('suppliers', 'products', 'purchase_orders', 'purchase_order_items')
                ORDER BY name
            """)
            )

            tables = result.fetchall()
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


if __name__ == "__main__":
    success = test_managed_identity_connection()
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
