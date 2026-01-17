-- ============================================================================
-- Migration: Add Negotiation and AP2 Payment Tables
-- Date: 2026-01-16  
-- Description: Adds tables for supplier negotiation workflow and AP2 payment mandates
-- Database: PostgreSQL (Neon)
-- ============================================================================

-- Step 1: Add negotiation columns to existing suppliers table
ALTER TABLE suppliers
ADD COLUMN IF NOT EXISTS negotiation_enabled BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS negotiation_email VARCHAR(255),
ADD COLUMN IF NOT EXISTS preferred_communication VARCHAR(20) DEFAULT 'email',
ADD COLUMN IF NOT EXISTS api_endpoint VARCHAR(500),
ADD COLUMN IF NOT EXISTS last_negotiation_date TIMESTAMP;

-- Step 2: Create negotiation_sessions table
CREATE TABLE IF NOT EXISTS negotiation_sessions (
    session_id VARCHAR(50) PRIMARY KEY,
    status VARCHAR(20) NOT NULL DEFAULT 'open',  -- 'open', 'completed', 'cancelled'
    items_json JSONB NOT NULL,                   -- JSON array of {sku, quantity, description}
    target_price DECIMAL(10,2),                  -- Optional target unit price
    max_rounds INTEGER NOT NULL DEFAULT 3,
    current_round INTEGER NOT NULL DEFAULT 0,
    winning_supplier_id VARCHAR(50),
    final_price DECIMAL(10,2),                   -- Final accepted unit price
    total_value DECIMAL(12,2),                   -- Final total order value
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    created_by VARCHAR(100),                     -- User or agent that initiated

    CONSTRAINT fk_negotiation_supplier
        FOREIGN KEY (winning_supplier_id) REFERENCES suppliers(supplier_id)
);

-- Create indexes for negotiation_sessions
CREATE INDEX IF NOT EXISTS idx_negotiation_status ON negotiation_sessions(status);
CREATE INDEX IF NOT EXISTS idx_negotiation_created ON negotiation_sessions(created_at DESC);

-- Step 3: Create negotiation_rounds table
CREATE TABLE IF NOT EXISTS negotiation_rounds (
    round_id VARCHAR(50) PRIMARY KEY,
    session_id VARCHAR(50) NOT NULL,
    supplier_id VARCHAR(50) NOT NULL,
    round_number INTEGER NOT NULL,               -- 1, 2, 3...
    offer_type VARCHAR(20) NOT NULL,             -- 'initial', 'counter', 'final'
    offered_price DECIMAL(10,2) NOT NULL,        -- Unit price offered by supplier
    total_value DECIMAL(12,2) NOT NULL,          -- Total order value
    counter_price DECIMAL(10,2),                 -- Our counter-offer (if any)
    justification TEXT,                          -- Reason for counter-offer
    status VARCHAR(20) NOT NULL DEFAULT 'pending', -- 'pending', 'accepted', 'rejected', 'countered'
    response_received_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_round_session
        FOREIGN KEY (session_id) REFERENCES negotiation_sessions(session_id),
    CONSTRAINT fk_round_supplier
        FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id)
);

-- Create indexes for negotiation_rounds
CREATE INDEX IF NOT EXISTS idx_round_session ON negotiation_rounds(session_id, round_number);
CREATE INDEX IF NOT EXISTS idx_round_supplier ON negotiation_rounds(supplier_id, created_at DESC);

-- Step 4: Create payment_mandates table
CREATE TABLE IF NOT EXISTS payment_mandates (
    mandate_id VARCHAR(50) PRIMARY KEY,
    session_id VARCHAR(50),                      -- Link to negotiation (optional)
    po_number VARCHAR(50),                       -- Link to purchase order (optional)
    supplier_id VARCHAR(50) NOT NULL,
    amount DECIMAL(12,2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    mandate_type VARCHAR(20) NOT NULL,           -- 'checkout', 'recurring', 'preauth'
    signed_mandate_json TEXT NOT NULL,           -- Full AP2 mandate (SD-JWT)
    merchant_authorization_json TEXT,            -- Supplier's signed response
    signature_algorithm VARCHAR(50) NOT NULL,    -- 'ES256', 'RS256'
    public_key_id VARCHAR(100),                  -- Key ID for verification
    status VARCHAR(20) NOT NULL DEFAULT 'created', -- 'created', 'sent', 'verified', 'executed', 'expired', 'failed'
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    executed_at TIMESTAMP,
    error_message TEXT,

    CONSTRAINT fk_mandate_session
        FOREIGN KEY (session_id) REFERENCES negotiation_sessions(session_id),
    CONSTRAINT fk_mandate_supplier
        FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id)
);

-- Create indexes for payment_mandates
CREATE INDEX IF NOT EXISTS idx_mandate_session ON payment_mandates(session_id);
CREATE INDEX IF NOT EXISTS idx_mandate_status ON payment_mandates(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_mandate_expiry ON payment_mandates(expires_at) 
    WHERE status IN ('created', 'sent');

-- Step 5: Add foreign keys to purchase_orders table (if columns don't exist)
ALTER TABLE purchase_orders
ADD COLUMN IF NOT EXISTS mandate_id VARCHAR(50),
ADD COLUMN IF NOT EXISTS negotiation_session_id VARCHAR(50);

-- Add foreign key constraints (use DO block to check if constraints exist)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'fk_po_mandate'
    ) THEN
        ALTER TABLE purchase_orders
        ADD CONSTRAINT fk_po_mandate
            FOREIGN KEY (mandate_id) REFERENCES payment_mandates(mandate_id);
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'fk_po_negotiation'
    ) THEN
        ALTER TABLE purchase_orders
        ADD CONSTRAINT fk_po_negotiation
            FOREIGN KEY (negotiation_session_id) REFERENCES negotiation_sessions(session_id);
    END IF;
END $$;

-- ============================================================================
-- Verification Queries
-- ============================================================================

-- Verify tables were created
SELECT table_name
FROM information_schema.tables
WHERE table_name IN ('negotiation_sessions', 'negotiation_rounds', 'payment_mandates')
  AND table_schema = 'public'
ORDER BY table_name;

-- ============================================================================
-- Rollback Script (if needed)
-- ============================================================================

/*
-- To rollback this migration, run the following in order:

-- Drop foreign keys from purchase_orders
ALTER TABLE purchase_orders DROP CONSTRAINT IF EXISTS fk_po_mandate;
ALTER TABLE purchase_orders DROP CONSTRAINT IF EXISTS fk_po_negotiation;

-- Drop columns from purchase_orders
ALTER TABLE purchase_orders DROP COLUMN IF EXISTS mandate_id;
ALTER TABLE purchase_orders DROP COLUMN IF EXISTS negotiation_session_id;

-- Drop payment_mandates table
DROP TABLE IF EXISTS payment_mandates;

-- Drop negotiation_rounds table
DROP TABLE IF EXISTS negotiation_rounds;

-- Drop negotiation_sessions table
DROP TABLE IF EXISTS negotiation_sessions;

-- Drop negotiation columns from suppliers
ALTER TABLE suppliers DROP COLUMN IF EXISTS negotiation_enabled;
ALTER TABLE suppliers DROP COLUMN IF EXISTS negotiation_email;
ALTER TABLE suppliers DROP COLUMN IF EXISTS preferred_communication;
ALTER TABLE suppliers DROP COLUMN IF EXISTS api_endpoint;
ALTER TABLE suppliers DROP COLUMN IF EXISTS last_negotiation_date;
*/
