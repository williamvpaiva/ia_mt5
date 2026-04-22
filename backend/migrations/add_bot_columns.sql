-- Migration: Add missing columns to bots table
-- Created: 2026-04-19
-- Issue: Column bots.max_spread does not exist

-- Adiciona colunas de trading limits
ALTER TABLE bots ADD COLUMN IF NOT EXISTS max_spread FLOAT DEFAULT 5.0;
ALTER TABLE bots ADD COLUMN IF NOT EXISTS max_slippage FLOAT DEFAULT 3.0;
ALTER TABLE bots ADD COLUMN IF NOT EXISTS allowed_symbols JSONB DEFAULT '[]';

-- Adiciona coluna de trading schedule
ALTER TABLE bots ADD COLUMN IF NOT EXISTS trading_schedule JSONB;

-- Adiciona colunas de status
ALTER TABLE bots ADD COLUMN IF NOT EXISTS last_run TIMESTAMP;
ALTER TABLE bots ADD COLUMN IF NOT EXISTS last_error VARCHAR(500);
ALTER TABLE bots ADD COLUMN IF NOT EXISTS total_trades INTEGER DEFAULT 0;
ALTER TABLE bots ADD COLUMN IF NOT EXISTS winning_trades INTEGER DEFAULT 0;
ALTER TABLE bots ADD COLUMN IF NOT EXISTS losing_trades INTEGER DEFAULT 0;
ALTER TABLE bots ADD COLUMN IF NOT EXISTS total_pnl FLOAT DEFAULT 0.0;

-- Adiciona índices para performance
CREATE INDEX IF NOT EXISTS idx_bots_max_spread ON bots(max_spread);
CREATE INDEX IF NOT EXISTS idx_bots_last_run ON bots(last_run);
CREATE INDEX IF NOT EXISTS idx_bots_active ON bots(active);
