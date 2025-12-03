-- ============================================================================
-- Supabase Database Schema for NIFTY/SENSEX Trader
-- ============================================================================
-- This file contains all table definitions for the trading application
-- Run this in your Supabase SQL Editor to create the required tables
-- ============================================================================

-- ============================================================================
-- 1. ATM ZONE BIAS TABLE
-- Stores detailed strike-wise data for ATM ±5 zones with PCR calculations
-- ============================================================================
CREATE TABLE IF NOT EXISTS atm_zone_bias (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(50) NOT NULL,                  -- Trading symbol (NIFTY, SENSEX, etc.)
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(), -- Record timestamp
    spot_price DECIMAL(10, 2) NOT NULL,           -- Current spot price
    strike_price DECIMAL(10, 2) NOT NULL,         -- Strike price
    strike_offset INTEGER NOT NULL,               -- Offset from ATM (-5 to +5)

    -- Call Option (CE) Data
    ce_oi BIGINT DEFAULT 0,                       -- Call Open Interest
    ce_oi_change BIGINT DEFAULT 0,                -- Call OI Change
    ce_volume BIGINT DEFAULT 0,                   -- Call Volume

    -- Put Option (PE) Data
    pe_oi BIGINT DEFAULT 0,                       -- Put Open Interest
    pe_oi_change BIGINT DEFAULT 0,                -- Put OI Change
    pe_volume BIGINT DEFAULT 0,                   -- Put Volume

    -- Put-Call Ratio (PCR) for this strike
    pcr_oi DECIMAL(10, 4) DEFAULT 0,              -- PCR based on OI
    pcr_oi_change DECIMAL(10, 4) DEFAULT 0,       -- PCR based on OI Change
    pcr_volume DECIMAL(10, 4) DEFAULT 0,          -- PCR based on Volume

    -- Bias for this strike
    strike_bias VARCHAR(20) DEFAULT 'NEUTRAL',    -- BULLISH, BEARISH, or NEUTRAL

    -- Indexes for faster queries
    CONSTRAINT atm_zone_bias_unique UNIQUE(symbol, timestamp, strike_price)
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_atm_zone_bias_symbol ON atm_zone_bias(symbol);
CREATE INDEX IF NOT EXISTS idx_atm_zone_bias_timestamp ON atm_zone_bias(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_atm_zone_bias_symbol_timestamp ON atm_zone_bias(symbol, timestamp DESC);

-- Enable Row Level Security (RLS)
ALTER TABLE atm_zone_bias ENABLE ROW LEVEL SECURITY;

-- Create policy to allow all operations (adjust based on your security requirements)
CREATE POLICY "Enable all access for atm_zone_bias" ON atm_zone_bias
    FOR ALL USING (true);

-- ============================================================================
-- 2. OPTION CHAIN SNAPSHOTS TABLE
-- Stores complete option chain snapshots with overall PCR and bias
-- ============================================================================
CREATE TABLE IF NOT EXISTS option_chain_snapshots (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(50) NOT NULL,                  -- Trading symbol
    expiry DATE NOT NULL,                         -- Option expiry date
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(), -- Snapshot timestamp

    -- Market Data
    spot_price DECIMAL(10, 2) NOT NULL,           -- Current spot price

    -- Overall PCR Metrics
    pcr_oi DECIMAL(10, 4) DEFAULT 0,              -- Overall PCR (OI)
    pcr_oi_change DECIMAL(10, 4) DEFAULT 0,       -- Overall PCR (OI Change)
    pcr_volume DECIMAL(10, 4) DEFAULT 0,          -- Overall PCR (Volume)

    -- Total OI
    total_ce_oi BIGINT DEFAULT 0,                 -- Total Call OI
    total_pe_oi BIGINT DEFAULT 0,                 -- Total Put OI

    -- Bias Analysis
    overall_bias VARCHAR(20) DEFAULT 'NEUTRAL',   -- Overall market bias
    bias_score INTEGER DEFAULT 0,                 -- Bias score (-10 to +10)

    -- Complete Data (JSONB for flexibility)
    data JSONB,                                   -- Full option chain data

    -- Constraint
    CONSTRAINT option_chain_unique UNIQUE(symbol, expiry, timestamp)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_option_chain_symbol ON option_chain_snapshots(symbol);
CREATE INDEX IF NOT EXISTS idx_option_chain_timestamp ON option_chain_snapshots(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_option_chain_expiry ON option_chain_snapshots(expiry);
CREATE INDEX IF NOT EXISTS idx_option_chain_symbol_expiry ON option_chain_snapshots(symbol, expiry, timestamp DESC);

-- Enable RLS
ALTER TABLE option_chain_snapshots ENABLE ROW LEVEL SECURITY;

-- Create policy
CREATE POLICY "Enable all access for option_chain_snapshots" ON option_chain_snapshots
    FOR ALL USING (true);

-- ============================================================================
-- 3. TRADING SIGNALS TABLE
-- Stores trading signals and setups
-- ============================================================================
CREATE TABLE IF NOT EXISTS trading_signals (
    id BIGSERIAL PRIMARY KEY,
    signal_id VARCHAR(100) UNIQUE NOT NULL,       -- Unique signal identifier
    symbol VARCHAR(50) NOT NULL,                  -- Trading symbol
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(), -- Signal generation time

    -- Signal Details
    signal_type VARCHAR(50) NOT NULL,             -- VOB, HTF, etc.
    direction VARCHAR(10) NOT NULL,               -- LONG or SHORT
    entry_price DECIMAL(10, 2),                   -- Entry price
    stop_loss DECIMAL(10, 2),                     -- Stop loss level
    target DECIMAL(10, 2),                        -- Target price

    -- Signal Status
    status VARCHAR(20) DEFAULT 'active',          -- active, triggered, closed, cancelled

    -- Additional Data
    metadata JSONB,                               -- Additional signal metadata

    -- Result Tracking
    exit_price DECIMAL(10, 2),                    -- Exit price (if closed)
    pnl DECIMAL(10, 2),                           -- Profit/Loss
    exit_timestamp TIMESTAMPTZ                    -- Exit time
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_trading_signals_symbol ON trading_signals(symbol);
CREATE INDEX IF NOT EXISTS idx_trading_signals_status ON trading_signals(status);
CREATE INDEX IF NOT EXISTS idx_trading_signals_timestamp ON trading_signals(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_trading_signals_symbol_status ON trading_signals(symbol, status);

-- Enable RLS
ALTER TABLE trading_signals ENABLE ROW LEVEL SECURITY;

-- Create policy
CREATE POLICY "Enable all access for trading_signals" ON trading_signals
    FOR ALL USING (true);

-- ============================================================================
-- 4. BIAS ANALYSIS HISTORY TABLE
-- Stores historical bias analysis data
-- ============================================================================
CREATE TABLE IF NOT EXISTS bias_analysis_history (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(50) NOT NULL,                  -- Trading symbol
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(), -- Analysis timestamp

    -- Bias Metrics
    overall_bias VARCHAR(20) DEFAULT 'NEUTRAL',   -- Overall bias
    bias_score DECIMAL(6, 2) DEFAULT 0,           -- Bias score

    -- Component Biases
    technical_bias VARCHAR(20),                   -- Technical indicators bias
    option_chain_bias VARCHAR(20),                -- Option chain bias
    volume_bias VARCHAR(20),                      -- Volume analysis bias
    sentiment_bias VARCHAR(20),                   -- Market sentiment bias

    -- Detailed Scores
    fast_indicators_score DECIMAL(6, 2),          -- Fast indicators score
    medium_indicators_score DECIMAL(6, 2),        -- Medium indicators score
    slow_indicators_score DECIMAL(6, 2),          -- Slow indicators score

    -- Complete Data
    data JSONB                                    -- Full bias analysis data
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_bias_history_symbol ON bias_analysis_history(symbol);
CREATE INDEX IF NOT EXISTS idx_bias_history_timestamp ON bias_analysis_history(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_bias_history_symbol_timestamp ON bias_analysis_history(symbol, timestamp DESC);

-- Enable RLS
ALTER TABLE bias_analysis_history ENABLE ROW LEVEL SECURITY;

-- Create policy
CREATE POLICY "Enable all access for bias_analysis_history" ON bias_analysis_history
    FOR ALL USING (true);

-- ============================================================================
-- 5. CREATE VIEWS FOR EASY DATA ACCESS
-- ============================================================================

-- Latest ATM Zone Bias View
CREATE OR REPLACE VIEW latest_atm_zone_bias AS
SELECT DISTINCT ON (symbol, strike_offset)
    symbol,
    timestamp,
    spot_price,
    strike_price,
    strike_offset,
    ce_oi,
    pe_oi,
    ce_oi_change,
    pe_oi_change,
    ce_volume,
    pe_volume,
    pcr_oi,
    pcr_oi_change,
    pcr_volume,
    strike_bias
FROM atm_zone_bias
ORDER BY symbol, strike_offset, timestamp DESC;

-- Latest Option Chain View
CREATE OR REPLACE VIEW latest_option_chain AS
SELECT DISTINCT ON (symbol, expiry)
    symbol,
    expiry,
    timestamp,
    spot_price,
    pcr_oi,
    pcr_oi_change,
    pcr_volume,
    total_ce_oi,
    total_pe_oi,
    overall_bias,
    bias_score
FROM option_chain_snapshots
ORDER BY symbol, expiry, timestamp DESC;

-- ============================================================================
-- 6. HELPFUL FUNCTIONS
-- ============================================================================

-- Function to clean old data (older than 30 days)
CREATE OR REPLACE FUNCTION clean_old_data(days_to_keep INTEGER DEFAULT 30)
RETURNS TABLE(
    table_name TEXT,
    rows_deleted BIGINT
) AS $$
DECLARE
    cutoff_date TIMESTAMPTZ;
    deleted_count BIGINT;
BEGIN
    cutoff_date := NOW() - (days_to_keep || ' days')::INTERVAL;

    -- Clean atm_zone_bias
    DELETE FROM atm_zone_bias WHERE timestamp < cutoff_date;
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    table_name := 'atm_zone_bias';
    rows_deleted := deleted_count;
    RETURN NEXT;

    -- Clean option_chain_snapshots
    DELETE FROM option_chain_snapshots WHERE timestamp < cutoff_date;
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    table_name := 'option_chain_snapshots';
    rows_deleted := deleted_count;
    RETURN NEXT;

    -- Clean bias_analysis_history
    DELETE FROM bias_analysis_history WHERE timestamp < cutoff_date;
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    table_name := 'bias_analysis_history';
    rows_deleted := deleted_count;
    RETURN NEXT;

    RETURN;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- SETUP COMPLETE
-- ============================================================================
-- All tables, indexes, views, and functions have been created
-- You can now use the Supabase integration in your application
-- ============================================================================
