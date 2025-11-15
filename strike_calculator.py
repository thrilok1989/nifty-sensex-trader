from config import STRIKE_INTERVALS, SENSEX_NIFTY_RATIO

def calculate_strike(index: str, nifty_price: float, direction: str, expiry_date: str):
    """Calculate option strike - Always uses ATM"""

    interval = STRIKE_INTERVALS[index]

    # Calculate spot price for selected index
    if index == "SENSEX":
        spot_price = nifty_price * SENSEX_NIFTY_RATIO
    else:
        spot_price = nifty_price

    # Calculate ATM
    atm_strike = round(spot_price / interval) * interval

    # Always use ATM strike
    strike = atm_strike
    strike_type = "ATM"

    return {
        'strike': strike,
        'strike_type': strike_type,
        'atm_strike': atm_strike,
        'spot_price': spot_price,
        'option_type': 'CE' if direction == 'CALL' else 'PE'
    }

def calculate_levels(index: str, direction: str, vob_support: float, 
                     vob_resistance: float, sl_offset: int = 10):
    """Calculate entry, SL, target levels"""
    
    # Scale for SENSEX
    if index == "SENSEX":
        vob_support *= SENSEX_NIFTY_RATIO
        vob_resistance *= SENSEX_NIFTY_RATIO
        sl_offset *= SENSEX_NIFTY_RATIO
    
    if direction == "CALL":
        entry = vob_support
        target = vob_resistance
        sl = vob_support - sl_offset
    else:
        entry = vob_resistance
        target = vob_support
        sl = vob_resistance + sl_offset
    
    return {
        'entry_level': round(entry, 2),
        'target_level': round(target, 2),
        'sl_level': round(sl, 2),
        'risk_points': abs(entry - sl),
        'reward_points': abs(target - entry),
        'rr_ratio': round(abs(target - entry) / abs(entry - sl), 2)
    }
