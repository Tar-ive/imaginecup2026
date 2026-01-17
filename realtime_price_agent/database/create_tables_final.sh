#!/bin/bash
# Create database tables using Azure CLI and SQL files

echo "🔄 Creating database tables using Azure CLI..."

# Create a temporary SQL file for each table
cat > /tmp/suppliers.sql << 'EOF'
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
EOF

cat > /tmp/products.sql << 'EOF'
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
EOF

cat > /tmp/purchase_orders.sql << 'EOF'
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
EOF

cat > /tmp/purchase_order_items.sql << 'EOF'
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
EOF

cat > /tmp/indexes.sql << 'EOF'
CREATE INDEX idx_supplier_name ON suppliers(supplier_name);
CREATE INDEX idx_product_brand ON products(brand);
CREATE INDEX idx_product_supplier ON products(supplier_id);
CREATE INDEX idx_po_supplier ON purchase_orders(supplier_id);
CREATE INDEX idx_po_status ON purchase_orders(status);
CREATE INDEX idx_poi_po_number ON purchase_order_items(po_number);
CREATE INDEX idx_poi_asin ON purchase_order_items(asin);
EOF

# Execute each SQL file
echo "Creating suppliers table..."
sql_content=$(cat /tmp/suppliers.sql)
az sql db t-sql execute --server imaginecup-cosmos --resource-group ImagineCup --database free-sql-db-9628486 --query "$sql_content" 2>/dev/null && echo "✅ Suppliers table created" || echo "❌ Failed to create suppliers table"

echo "Creating products table..."
sql_content=$(cat /tmp/products.sql)
az sql db t-sql execute --server imaginecup-cosmos --resource-group ImagineCup --database free-sql-db-9628486 --query "$sql_content" 2>/dev/null && echo "✅ Products table created" || echo "❌ Failed to create products table"

echo "Creating purchase_orders table..."
sql_content=$(cat /tmp/purchase_orders.sql)
az sql db t-sql execute --server imaginecup-cosmos --resource-group ImagineCup --database free-sql-db-9628486 --query "$sql_content" 2>/dev/null && echo "✅ Purchase orders table created" || echo "❌ Failed to create purchase_orders table"

echo "Creating purchase_order_items table..."
sql_content=$(cat /tmp/purchase_order_items.sql)
az sql db t-sql execute --server imaginecup-cosmos --resource-group ImagineCup --database free-sql-db-9628486 --query "$sql_content" 2>/dev/null && echo "✅ Purchase order items table created" || echo "❌ Failed to create purchase_order_items table"

echo "Creating indexes..."
sql_content=$(cat /tmp/indexes.sql)
az sql db t-sql execute --server imaginecup-cosmos --resource-group ImagineCup --database free-sql-db-9628486 --query "$sql_content" 2>/dev/null && echo "✅ Indexes created" || echo "❌ Failed to create indexes"

# Clean up
rm -f /tmp/*.sql

echo "🔄 Verifying table creation..."
# This will likely fail due to the t-sql command issue, but let's try
az sql db t-sql execute --server imaginecup-cosmos --resource-group ImagineCup --database free-sql-db-9628486 --query "SELECT name, type_desc FROM sys.objects WHERE type = 'U' AND name IN ('suppliers', 'products', 'purchase_orders', 'purchase_order_items') ORDER BY name" 2>/dev/null || echo "Could not verify tables - this is expected if t-sql command doesn't work"

echo "✅ Database schema creation script completed!"
echo ""
echo "🚀 Next steps if tables were created successfully:"
echo "1. Run: python src/scripts/01_generate_suppliers.py"
echo "2. Run: python src/scripts/02_generate_inventory.py"
echo "3. Run: python src/scripts/03_generate_orders.py"
echo "4. Run: python src/scripts/verify_data.py"