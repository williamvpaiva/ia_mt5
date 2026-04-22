"""
Migration Script: Add missing columns to bots table
Run this to update the database schema with new Bot model fields.
"""
import sys
from pathlib import Path

# Adiciona o backend ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import engine
from sqlalchemy import text

def run_migration():
    """Adiciona colunas faltantes na tabela bots"""
    
    print("Starting migration: Adding missing columns to bots table...")
    
    with engine.connect() as conn:
        # Adiciona colunas de trading limits
        try:
            conn.execute(text("ALTER TABLE bots ADD COLUMN IF NOT EXISTS max_spread FLOAT DEFAULT 5.0"))
            print("  max_spread column added/exists")
        except Exception as e:
            print(f"  max_spread: {e}")
        
        try:
            conn.execute(text("ALTER TABLE bots ADD COLUMN IF NOT EXISTS max_slippage FLOAT DEFAULT 3.0"))
            print("  max_slippage column added/exists")
        except Exception as e:
            print(f"  max_slippage: {e}")
        
        try:
            conn.execute(text("ALTER TABLE bots ADD COLUMN IF NOT EXISTS allowed_symbols JSONB DEFAULT '[]'"))
            print("  allowed_symbols column added/exists")
        except Exception as e:
            print(f"  allowed_symbols: {e}")
        
        # Adiciona coluna de trading schedule
        try:
            conn.execute(text("ALTER TABLE bots ADD COLUMN IF NOT EXISTS trading_schedule JSONB"))
            print("  trading_schedule column added/exists")
        except Exception as e:
            print(f"  trading_schedule: {e}")
        
        # Adiciona colunas de status
        try:
            conn.execute(text("ALTER TABLE bots ADD COLUMN IF NOT EXISTS last_run TIMESTAMP"))
            print("  last_run column added/exists")
        except Exception as e:
            print(f"  last_run: {e}")
        
        try:
            conn.execute(text("ALTER TABLE bots ADD COLUMN IF NOT EXISTS last_error VARCHAR(500)"))
            print("  last_error column added/exists")
        except Exception as e:
            print(f"  last_error: {e}")
        
        try:
            conn.execute(text("ALTER TABLE bots ADD COLUMN IF NOT EXISTS total_trades INTEGER DEFAULT 0"))
            print("  total_trades column added/exists")
        except Exception as e:
            print(f"  total_trades: {e}")
        
        try:
            conn.execute(text("ALTER TABLE bots ADD COLUMN IF NOT EXISTS winning_trades INTEGER DEFAULT 0"))
            print("  winning_trades column added/exists")
        except Exception as e:
            print(f"  winning_trades: {e}")
        
        try:
            conn.execute(text("ALTER TABLE bots ADD COLUMN IF NOT EXISTS losing_trades INTEGER DEFAULT 0"))
            print("  losing_trades column added/exists")
        except Exception as e:
            print(f"  losing_trades: {e}")
        
        try:
            conn.execute(text("ALTER TABLE bots ADD COLUMN IF NOT EXISTS total_pnl FLOAT DEFAULT 0.0"))
            print("  total_pnl column added/exists")
        except Exception as e:
            print(f"  total_pnl: {e}")
        
        # Cria indices
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_bots_max_spread ON bots(max_spread)"))
            print("  idx_bots_max_spread index created/exists")
        except Exception as e:
            print(f"  idx_bots_max_spread: {e}")
        
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_bots_last_run ON bots(last_run)"))
            print("  idx_bots_last_run index created/exists")
        except Exception as e:
            print(f"  idx_bots_last_run: {e}")
        
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_bots_active ON bots(active)"))
            print("  idx_bots_active index created/exists")
        except Exception as e:
            print(f"  idx_bots_active: {e}")
        
        conn.commit()
    
    print("\nMigration completed successfully!")
    print("You can now restart the backend container")


if __name__ == "__main__":
    run_migration()
