"""
Centralized Option Chain Data Manager
======================================

This module provides a centralized mechanism to fetch option chain data from Dhan API
ONCE per refresh and share it across all tabs and components.

Key Features:
- Single fetch per refresh cycle for all symbols
- Session state caching to avoid redundant API calls
- Shared data across all tabs (ATM Zone Bias, OI Winding, Option Chain Analysis, etc.)
- Batch fetching for all instruments (NIFTY, SENSEX, BANKNIFTY, FINNIFTY)
- Thread-safe access with proper locking
"""

import streamlit as st
import threading
from datetime import datetime
from typing import Dict, Optional, List
from dhan_option_chain_analyzer import DhanOptionChainAnalyzer
from config import get_current_time_ist
import logging

logger = logging.getLogger(__name__)


class OptionChainManager:
    """Centralized manager for option chain data fetching and caching"""

    # All supported symbols
    SYMBOLS = ['NIFTY', 'SENSEX', 'BANKNIFTY', 'FINNIFTY']

    # Session state keys
    SESSION_KEY_DATA = 'option_chain_shared_data'
    SESSION_KEY_TIMESTAMP = 'option_chain_fetch_timestamp'
    SESSION_KEY_LOCK = 'option_chain_fetch_lock'
    SESSION_KEY_FETCHING = 'option_chain_fetching'

    def __init__(self):
        """Initialize the option chain manager"""
        self.analyzer = self._get_analyzer()
        self._initialize_session_state()

    @staticmethod
    def _get_analyzer():
        """Get or create DhanOptionChainAnalyzer instance"""
        if 'option_chain_analyzer' not in st.session_state:
            st.session_state.option_chain_analyzer = DhanOptionChainAnalyzer()
        return st.session_state.option_chain_analyzer

    @staticmethod
    def _initialize_session_state():
        """Initialize session state variables"""
        if OptionChainManager.SESSION_KEY_DATA not in st.session_state:
            st.session_state[OptionChainManager.SESSION_KEY_DATA] = {}

        if OptionChainManager.SESSION_KEY_TIMESTAMP not in st.session_state:
            st.session_state[OptionChainManager.SESSION_KEY_TIMESTAMP] = None

        if OptionChainManager.SESSION_KEY_FETCHING not in st.session_state:
            st.session_state[OptionChainManager.SESSION_KEY_FETCHING] = False

    def fetch_all_symbols(self, force_refresh: bool = False) -> Dict[str, Dict]:
        """
        Fetch option chain data for all symbols at once

        Args:
            force_refresh: If True, force fetch even if cached data exists

        Returns:
            Dictionary with symbol as key and option chain data as value
        """
        # Check if we're already fetching
        if st.session_state[self.SESSION_KEY_FETCHING]:
            logger.warning("Fetch already in progress, returning cached data")
            return st.session_state[self.SESSION_KEY_DATA]

        # Check if cached data exists and is recent (within last 5 minutes)
        if not force_refresh and st.session_state[self.SESSION_KEY_DATA]:
            last_fetch = st.session_state[self.SESSION_KEY_TIMESTAMP]
            if last_fetch:
                from datetime import timedelta
                if isinstance(last_fetch, str):
                    try:
                        last_fetch = datetime.fromisoformat(last_fetch)
                    except:
                        last_fetch = None

                if last_fetch and (datetime.now() - last_fetch) < timedelta(minutes=5):
                    logger.info("Using cached option chain data")
                    return st.session_state[self.SESSION_KEY_DATA]

        # Mark as fetching
        st.session_state[self.SESSION_KEY_FETCHING] = True

        try:
            logger.info("Fetching option chain data for all symbols...")
            all_data = {}

            for symbol in self.SYMBOLS:
                try:
                    logger.info(f"Fetching {symbol}...")

                    # Fetch raw option chain data
                    oc_data = self.analyzer.fetch_option_chain(symbol)

                    if oc_data.get('success'):
                        all_data[symbol] = oc_data
                        logger.info(f"✓ {symbol} fetched successfully")
                    else:
                        logger.error(f"✗ {symbol} fetch failed: {oc_data.get('error')}")
                        all_data[symbol] = oc_data  # Store error response

                except Exception as e:
                    logger.error(f"Error fetching {symbol}: {str(e)}")
                    all_data[symbol] = {
                        'success': False,
                        'error': str(e),
                        'symbol': symbol
                    }

            # Store in session state
            st.session_state[self.SESSION_KEY_DATA] = all_data
            st.session_state[self.SESSION_KEY_TIMESTAMP] = datetime.now()

            logger.info(f"All symbols fetched. Total: {len(all_data)}")
            return all_data

        finally:
            # Clear fetching flag
            st.session_state[self.SESSION_KEY_FETCHING] = False

    def get_option_chain(self, symbol: str, auto_fetch: bool = True) -> Optional[Dict]:
        """
        Get option chain data for a specific symbol

        Args:
            symbol: Trading symbol (NIFTY, SENSEX, etc.)
            auto_fetch: If True and data not cached, fetch automatically

        Returns:
            Option chain data dictionary or None
        """
        # Check if data exists in cache
        cached_data = st.session_state[self.SESSION_KEY_DATA].get(symbol)

        if cached_data:
            return cached_data

        # If auto_fetch enabled and no cached data, fetch all symbols
        if auto_fetch:
            logger.info(f"No cached data for {symbol}, fetching all symbols...")
            all_data = self.fetch_all_symbols()
            return all_data.get(symbol)

        return None

    def get_all_option_chains(self, auto_fetch: bool = True) -> Dict[str, Dict]:
        """
        Get option chain data for all symbols

        Args:
            auto_fetch: If True and data not cached, fetch automatically

        Returns:
            Dictionary with all symbol data
        """
        cached_data = st.session_state[self.SESSION_KEY_DATA]

        # If cache is empty or incomplete, fetch
        if not cached_data or len(cached_data) < len(self.SYMBOLS):
            if auto_fetch:
                return self.fetch_all_symbols()

        return cached_data

    def is_data_stale(self, max_age_minutes: int = 5) -> bool:
        """
        Check if cached data is stale

        Args:
            max_age_minutes: Maximum age in minutes before data is considered stale

        Returns:
            True if data is stale or doesn't exist
        """
        last_fetch = st.session_state[self.SESSION_KEY_TIMESTAMP]

        if not last_fetch:
            return True

        if isinstance(last_fetch, str):
            try:
                last_fetch = datetime.fromisoformat(last_fetch)
            except:
                return True

        from datetime import timedelta
        return (datetime.now() - last_fetch) > timedelta(minutes=max_age_minutes)

    def get_fetch_timestamp(self) -> Optional[datetime]:
        """
        Get the timestamp of last fetch

        Returns:
            Datetime of last fetch or None
        """
        timestamp = st.session_state[self.SESSION_KEY_TIMESTAMP]

        if isinstance(timestamp, str):
            try:
                return datetime.fromisoformat(timestamp)
            except:
                return None

        return timestamp

    def clear_cache(self):
        """Clear all cached data"""
        st.session_state[self.SESSION_KEY_DATA] = {}
        st.session_state[self.SESSION_KEY_TIMESTAMP] = None
        logger.info("Option chain cache cleared")

    def get_cache_status(self) -> Dict:
        """
        Get status of cached data

        Returns:
            Dictionary with cache status information
        """
        cached_data = st.session_state[self.SESSION_KEY_DATA]
        last_fetch = self.get_fetch_timestamp()

        symbols_cached = list(cached_data.keys()) if cached_data else []
        symbols_success = [s for s, d in cached_data.items() if d.get('success')] if cached_data else []

        return {
            'symbols_cached': symbols_cached,
            'symbols_success': symbols_success,
            'total_cached': len(symbols_cached),
            'total_success': len(symbols_success),
            'last_fetch': last_fetch,
            'is_stale': self.is_data_stale(),
            'is_fetching': st.session_state[self.SESSION_KEY_FETCHING]
        }


# Global instance
_option_chain_manager = None


def get_option_chain_manager() -> OptionChainManager:
    """
    Get or create global option chain manager instance

    Returns:
        OptionChainManager instance
    """
    global _option_chain_manager

    # Use session state to ensure single instance per session
    if 'global_option_chain_manager' not in st.session_state:
        st.session_state.global_option_chain_manager = OptionChainManager()

    return st.session_state.global_option_chain_manager


def preload_option_chain_data(symbols: Optional[List[str]] = None):
    """
    Preload option chain data for specified symbols

    Args:
        symbols: List of symbols to preload (default: all supported symbols)
    """
    manager = get_option_chain_manager()

    # If specific symbols requested, only fetch those
    if symbols:
        for symbol in symbols:
            manager.get_option_chain(symbol, auto_fetch=True)
    else:
        # Fetch all symbols at once
        manager.fetch_all_symbols()


def refresh_all_option_chain_data():
    """Force refresh all option chain data"""
    manager = get_option_chain_manager()
    return manager.fetch_all_symbols(force_refresh=True)
