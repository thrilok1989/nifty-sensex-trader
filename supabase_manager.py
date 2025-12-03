"""
Supabase Manager for NIFTY/SENSEX Trader
Handles all Supabase database operations including:
- Connection management
- Data storage and retrieval
- Schema management
"""

import streamlit as st
from supabase import create_client, Client
from typing import Optional, Dict, Any, List
from datetime import datetime
import pandas as pd
from config import get_supabase_credentials, IST

class SupabaseManager:
    """Manages Supabase database operations"""

    def __init__(self):
        """Initialize Supabase client"""
        self.client: Optional[Client] = None
        self.enabled = False
        self._initialize_client()

    def _initialize_client(self):
        """Initialize the Supabase client with credentials"""
        try:
            credentials = get_supabase_credentials()

            if credentials['enabled'] and credentials['url'] and credentials['key']:
                self.client = create_client(credentials['url'], credentials['key'])
                self.enabled = True
                print("✅ Supabase client initialized successfully")
            else:
                print("⚠️ Supabase is disabled - credentials not configured")
                self.enabled = False
        except Exception as e:
            print(f"❌ Failed to initialize Supabase client: {e}")
            self.enabled = False

    def is_enabled(self) -> bool:
        """Check if Supabase is enabled and connected"""
        return self.enabled and self.client is not None

    # ═══════════════════════════════════════════════════════════════════════
    # ATM ZONE BIAS OPERATIONS
    # ═══════════════════════════════════════════════════════════════════════

    def save_atm_zone_bias(self, symbol: str, spot_price: float, atm_zone_data: List[Dict[str, Any]]) -> bool:
        """
        Save ATM zone bias data for a symbol

        Args:
            symbol: Trading symbol (NIFTY, SENSEX, etc.)
            spot_price: Current spot price
            atm_zone_data: List of strike-wise data dictionaries

        Returns:
            bool: True if successful, False otherwise
        """
        if not self.is_enabled():
            return False

        try:
            timestamp = datetime.now(IST).isoformat()

            # Prepare records for batch insert
            records = []
            for strike_data in atm_zone_data:
                record = {
                    'symbol': symbol,
                    'timestamp': timestamp,
                    'spot_price': spot_price,
                    'strike_price': strike_data['strike_price'],
                    'strike_offset': strike_data['strike_offset'],
                    'ce_oi': strike_data.get('ce_oi', 0),
                    'pe_oi': strike_data.get('pe_oi', 0),
                    'ce_oi_change': strike_data.get('ce_oi_change', 0),
                    'pe_oi_change': strike_data.get('pe_oi_change', 0),
                    'ce_volume': strike_data.get('ce_volume', 0),
                    'pe_volume': strike_data.get('pe_volume', 0),
                    'pcr_oi': strike_data.get('pcr_oi', 0),
                    'pcr_oi_change': strike_data.get('pcr_oi_change', 0),
                    'pcr_volume': strike_data.get('pcr_volume', 0),
                    'strike_bias': strike_data.get('strike_bias', 'NEUTRAL')
                }
                records.append(record)

            # Insert all records
            response = self.client.table('atm_zone_bias').insert(records).execute()

            if response.data:
                print(f"✅ Saved {len(records)} ATM zone bias records for {symbol}")
                return True
            else:
                print(f"⚠️ No data returned after saving ATM zone bias for {symbol}")
                return False

        except Exception as e:
            print(f"❌ Error saving ATM zone bias data: {e}")
            return False

    def get_latest_atm_zone_bias(self, symbol: str, limit: int = 11) -> Optional[pd.DataFrame]:
        """
        Get the latest ATM zone bias data for a symbol

        Args:
            symbol: Trading symbol (NIFTY, SENSEX, etc.)
            limit: Number of strikes to retrieve (default 11 for ATM ±5)

        Returns:
            DataFrame with latest ATM zone bias data or None
        """
        if not self.is_enabled():
            return None

        try:
            response = (
                self.client.table('atm_zone_bias')
                .select('*')
                .eq('symbol', symbol)
                .order('timestamp', desc=True)
                .limit(limit)
                .execute()
            )

            if response.data:
                df = pd.DataFrame(response.data)
                # Sort by strike_offset for proper display
                df = df.sort_values('strike_offset', ascending=True).reset_index(drop=True)
                return df
            else:
                return None

        except Exception as e:
            print(f"❌ Error retrieving ATM zone bias data: {e}")
            return None

    def get_atm_zone_bias_history(self, symbol: str, hours: int = 24) -> Optional[pd.DataFrame]:
        """
        Get historical ATM zone bias data for a symbol

        Args:
            symbol: Trading symbol
            hours: Number of hours of history to retrieve

        Returns:
            DataFrame with historical ATM zone bias data or None
        """
        if not self.is_enabled():
            return None

        try:
            from datetime import timedelta

            cutoff_time = (datetime.now(IST) - timedelta(hours=hours)).isoformat()

            response = (
                self.client.table('atm_zone_bias')
                .select('*')
                .eq('symbol', symbol)
                .gte('timestamp', cutoff_time)
                .order('timestamp', desc=True)
                .execute()
            )

            if response.data:
                return pd.DataFrame(response.data)
            else:
                return None

        except Exception as e:
            print(f"❌ Error retrieving ATM zone bias history: {e}")
            return None

    # ═══════════════════════════════════════════════════════════════════════
    # OPTION CHAIN DATA OPERATIONS
    # ═══════════════════════════════════════════════════════════════════════

    def save_option_chain_snapshot(self, symbol: str, expiry: str, option_chain_data: Dict[str, Any]) -> bool:
        """
        Save a snapshot of option chain data

        Args:
            symbol: Trading symbol
            expiry: Expiry date
            option_chain_data: Complete option chain data dictionary

        Returns:
            bool: True if successful, False otherwise
        """
        if not self.is_enabled():
            return False

        try:
            timestamp = datetime.now(IST).isoformat()

            record = {
                'symbol': symbol,
                'expiry': expiry,
                'timestamp': timestamp,
                'spot_price': option_chain_data.get('spot_price', 0),
                'pcr_oi': option_chain_data.get('pcr_oi', 0),
                'pcr_oi_change': option_chain_data.get('pcr_change_oi', 0),
                'pcr_volume': option_chain_data.get('pcr_volume', 0),
                'total_ce_oi': option_chain_data.get('total_ce_oi', 0),
                'total_pe_oi': option_chain_data.get('total_pe_oi', 0),
                'overall_bias': option_chain_data.get('overall_bias', 'NEUTRAL'),
                'bias_score': option_chain_data.get('bias_score', 0),
                'data': option_chain_data  # Store complete data as JSONB
            }

            response = self.client.table('option_chain_snapshots').insert(record).execute()

            if response.data:
                print(f"✅ Saved option chain snapshot for {symbol} {expiry}")
                return True
            else:
                return False

        except Exception as e:
            print(f"❌ Error saving option chain snapshot: {e}")
            return False

    # ═══════════════════════════════════════════════════════════════════════
    # TRADING SIGNALS OPERATIONS
    # ═══════════════════════════════════════════════════════════════════════

    def save_trading_signal(self, signal_data: Dict[str, Any]) -> bool:
        """
        Save a trading signal to the database

        Args:
            signal_data: Dictionary containing signal information

        Returns:
            bool: True if successful, False otherwise
        """
        if not self.is_enabled():
            return False

        try:
            timestamp = datetime.now(IST).isoformat()
            signal_data['timestamp'] = timestamp

            response = self.client.table('trading_signals').insert(signal_data).execute()

            if response.data:
                print(f"✅ Saved trading signal: {signal_data.get('signal_id', 'unknown')}")
                return True
            else:
                return False

        except Exception as e:
            print(f"❌ Error saving trading signal: {e}")
            return False

    def get_active_signals(self) -> Optional[pd.DataFrame]:
        """
        Get all active trading signals

        Returns:
            DataFrame with active signals or None
        """
        if not self.is_enabled():
            return None

        try:
            response = (
                self.client.table('trading_signals')
                .select('*')
                .eq('status', 'active')
                .order('timestamp', desc=True)
                .execute()
            )

            if response.data:
                return pd.DataFrame(response.data)
            else:
                return None

        except Exception as e:
            print(f"❌ Error retrieving active signals: {e}")
            return None

    # ═══════════════════════════════════════════════════════════════════════
    # DATABASE HEALTH & UTILITY
    # ═══════════════════════════════════════════════════════════════════════

    def test_connection(self) -> bool:
        """
        Test the Supabase connection

        Returns:
            bool: True if connection is working, False otherwise
        """
        if not self.is_enabled():
            return False

        try:
            # Try a simple query to test connection
            response = self.client.table('atm_zone_bias').select('count', count='exact').limit(1).execute()
            return True
        except Exception as e:
            print(f"❌ Supabase connection test failed: {e}")
            return False

    def get_table_stats(self) -> Dict[str, int]:
        """
        Get statistics about stored data

        Returns:
            Dictionary with row counts for each table
        """
        if not self.is_enabled():
            return {}

        stats = {}
        tables = ['atm_zone_bias', 'option_chain_snapshots', 'trading_signals']

        for table in tables:
            try:
                response = self.client.table(table).select('count', count='exact').limit(1).execute()
                stats[table] = response.count if hasattr(response, 'count') else 0
            except Exception as e:
                print(f"⚠️ Error getting stats for {table}: {e}")
                stats[table] = 0

        return stats


# Global instance
_supabase_manager = None

def get_supabase_manager() -> SupabaseManager:
    """Get or create the global Supabase manager instance"""
    global _supabase_manager

    if _supabase_manager is None:
        _supabase_manager = SupabaseManager()

    return _supabase_manager
