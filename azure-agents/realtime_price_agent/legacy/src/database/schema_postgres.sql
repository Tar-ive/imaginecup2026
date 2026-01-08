-- Postgres Database Schema for Realtime Price Agent
-- Creates the 4 core tables: suppliers, products, purchase_orders, purchase_order_items

-- ============================================================
-- Table 1: suppliers
-- ============================================================
CREATE TABLE IF NOT EXISTS suppliers (
    supplier_id VARCHAR(50) PRIMARY KEY,
    supplier_name VARCHAR(100) NOT NULL,
    contact_person VARCHAR(100),
    email VARCHAR(255),
    phone VARCHAR(50),
    address VARCHAR(500),
    city VARCHAR(100),
    state_province VARCHAR(100),
    country VARCHAR(100),
    postal_code VARCHAR(20),
    payment_terms VARCHAR(100),
    default_lead_time_days INTEGER DEFAULT 7,
    on_time_delivery_rate DECIMAL(5, 2),
    quality_rating DECIMAL(3, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT true
);

-- ============================================================
-- Table 2: products (Inventory Master)
-- ============================================================
CREATE TABLE IF NOT EXISTS products (
    asin VARCHAR(20) PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    brand VARCHAR(100),
    description TEXT,
    unit_cost DECIMAL(10, 2),
    last_purchase_price DECIMAL(10, 2),
    market_price DECIMAL(10, 2),
    price_last_updated TIMESTAMP,
    quantity_on_hand INTEGER NOT NULL DEFAULT 0,
    quantity_reserved INTEGER DEFAULT 0,
    quantity_available INTEGER GENERATED ALWAYS AS (quantity_on_hand - quantity_reserved) STORED,
    reorder_point INTEGER DEFAULT 10,
    reorder_quantity INTEGER DEFAULT 50,
    lead_time_days INTEGER DEFAULT 7,
    supplier_id VARCHAR(50),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id)
);

-- ============================================================
-- Table 3: purchase_orders
-- ============================================================
CREATE TABLE IF NOT EXISTS purchase_orders (
    po_number VARCHAR(50) PRIMARY KEY,
    supplier_id VARCHAR(50),
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expected_delivery_date TIMESTAMP,
    actual_delivery_date TIMESTAMP,
    total_cost DECIMAL(10, 2) DEFAULT 0,
    status VARCHAR(20) DEFAULT 'pending',
    item_count INTEGER DEFAULT 0,
    created_by VARCHAR(100) DEFAULT 'system',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_delivered BOOLEAN GENERATED ALWAYS AS (actual_delivery_date IS NOT NULL) STORED,
    FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id)
);

-- ============================================================
-- Table 4: purchase_order_items
-- ============================================================
CREATE TABLE IF NOT EXISTS purchase_order_items (
    po_item_id SERIAL PRIMARY KEY,
    po_number VARCHAR(50),
    asin VARCHAR(20),
    quantity_ordered INTEGER NOT NULL,
    quantity_received INTEGER DEFAULT 0,
    unit_price DECIMAL(10, 2) NOT NULL,
    line_total DECIMAL(12, 2) GENERATED ALWAYS AS (quantity_ordered * unit_price) STORED,
    is_fully_received BOOLEAN GENERATED ALWAYS AS (quantity_received >= quantity_ordered) STORED,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (po_number) REFERENCES purchase_orders(po_number),
    FOREIGN KEY (asin) REFERENCES products(asin)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_supplier_name ON suppliers(supplier_name);
CREATE INDEX IF NOT EXISTS idx_product_brand ON products(brand);
CREATE INDEX IF NOT EXISTS idx_product_supplier ON products(supplier_id);
CREATE INDEX IF NOT EXISTS idx_po_supplier ON purchase_orders(supplier_id);
CREATE INDEX IF NOT EXISTS idx_po_status ON purchase_orders(status);
CREATE INDEX IF NOT EXISTS idx_poi_po_number ON purchase_order_items(po_number);
CREATE INDEX IF NOT EXISTS idx_poi_asin ON purchase_order_items(asin);

-- Note: Trigger for updated_at can be added later if needed