"""
Configuration settings for Aster Operator

This module centralizes all bot configuration using Pydantic for type-safe settings
management. Values can be overridden via environment variables or .env file.

Educational Note:
- Using pydantic_settings ensures type safety and validation
- Settings are loaded from .env file automatically
- This pattern makes it easy to deploy across different environments
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    """
    Bot configuration with sensible defaults for educational purposes.

    All settings can be overridden via environment variables or .env file.
    For production use, always use environment variables for secrets.
    """

    # ============================================================================
    # ASTER DEX API CREDENTIALS
    # ============================================================================
    # These credentials authenticate your bot with Aster's API
    # Get them from: Aster DEX Settings > API Management > Create New Key
    #
    # Security Note:
    # - Never commit these to git (use .env file, which is in .gitignore)
    # - Use read+write permissions (bot needs to place orders)
    # - Enable IP whitelist in production for extra security
    aster_api_key: str
    aster_api_secret: str

    # Base URL for Aster's REST API (futures/perpetuals endpoint)
    # This is the production endpoint - testnet would use a different URL
    aster_base_url: str = "https://fapi.asterdex.com"

    # WebSocket URL for real-time market data (not used in current version)
    # Future versions might use this for streaming price updates
    aster_ws_url: str = "wss://fstream.asterdex.com"

    # ============================================================================
    # WALLET CONFIGURATION
    # ============================================================================
    # Your wallet address - this is where your USDT balance lives
    # Format: 0x... (Ethereum-style address)
    # This is used for account identification and tracking
    wallet_address: str

    # Private key would go here for Web3 signing (not needed for API trading)
    # private_key: str  # Uncomment if you need on-chain operations later

    # ============================================================================
    # TRADING PARAMETERS
    # ============================================================================

    # Referral code for Aster Genesis Stage 3 rewards
    # Using this code gives both you and the referrer bonus points
    # Change this to your own code if you want to refer others
    referral_code: str = "KoPPFo"

    # Trading capital in USDT
    # This is how much of your balance the bot will actively trade with
    #
    # Why it matters:
    # - Determines position sizes (larger capital = larger positions)
    # - Should be less than your total balance (leave buffer for fees/losses)
    # - Start small ($100-$500) until you understand the bot's behavior
    #
    # Example: If you have $1000 USDT, set this to $800 to keep $200 as buffer
    capital_usdt: float = 100.0

    # Leverage multiplier for positions
    #
    # What is leverage?
    # - 15x means you control $15 worth of BTC for every $1 of capital
    # - Higher leverage = more volume per dollar BUT higher liquidation risk
    #
    # Why 15x for this strategy?
    # - Generates significant volume without excessive risk
    # - Delta-neutral positions reduce directional risk
    # - Liquidation risk is ~6.7% adverse move (15x = 1/15 = 6.7%)
    #
    # Recommendations:
    # - Beginners: Start with 5-10x
    # - Intermediate: 10-15x (this bot's sweet spot)
    # - Advanced: 15-20x (monitor closely)
    # - Never exceed 25x (liquidation risk becomes too high)
    leverage: int = 15

    # Minimum position hold time in minutes
    #
    # Why 90 minutes specifically?
    # - Aster Genesis Stage 3 gives 10x reward multiplier for holds >90min
    # - Holding <90min gives only 1x multiplier (10x less rewards!)
    # - This is THE most important setting for maximizing airdrop points
    #
    # Strategy: Hold positions for 90+ minutes before rotating them
    # This maximizes "holding time equivalent" which = notional × hold_time × multiplier
    position_hold_time_min: int = 90

    # Daily volume target in USDT
    #
    # Why $15,000?
    # - Genesis Stage 3 rewards volume generation
    # - $15K daily = $105K weekly = good rewards vs risk
    # - With $100 capital at 15x leverage, this is ~10-12 rotations per day
    #
    # How to adjust:
    # - Higher target = more rotations = more fees but more rewards
    # - Lower target = fewer rotations = less risk but fewer rewards
    # - Scale with your capital (e.g., $1000 capital → $150K target)
    daily_volume_target: float = 15000.0

    # Maximum position size as percentage of capital
    #
    # Position sizing explained:
    # - 1.5% means each position uses 1.5% of your capital
    # - With $1000 capital: 1.5% = $15 per position
    # - With 15x leverage: $15 → $225 notional exposure
    #
    # Why 1.5%?
    # - Small enough to avoid concentration risk (losing everything in one trade)
    # - Large enough to generate meaningful volume
    # - Allows for ~66 positions before using full capital (1/0.015)
    #
    # Risk perspective:
    # - If one position goes completely wrong (unlikely with delta-neutral)
    # - You lose max 1.5% of capital per position
    # - Delta-neutral pairs lose even less (both sides offset each other)
    max_position_size_pct: float = 1.5

    # Trading pairs (which crypto perpetuals to trade)
    #
    # Why start with just BTCUSDT?
    # - Most liquid (easy to enter/exit, tight spreads)
    # - Most stable of all crypto (less volatility = less risk)
    # - Simplifies testing and debugging
    #
    # How to add more pairs:
    # - trading_pairs: List[str] = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    # - Make sure Aster supports them (check their markets page)
    # - More pairs = more diversification but more complexity
    #
    # Note: Current bot version only uses the first pair in the list
    trading_pairs: List[str] = ["BTCUSDT"]

    # ============================================================================
    # RISK MANAGEMENT PARAMETERS
    # ============================================================================
    # These settings are your safety net - they prevent catastrophic losses

    # Maximum drawdown percentage before stopping the bot
    #
    # What is drawdown?
    # - The peak-to-trough decline in your account balance
    # - 5% means if you start with $1000 and drop to $950, bot stops
    #
    # Why 5%?
    # - Delta-neutral strategy should rarely see >2-3% drawdown
    # - If you're down 5%, something is seriously wrong (bug, market chaos, etc.)
    # - Better to stop and investigate than continue losing
    #
    # Note: Current version logs this but doesn't auto-stop (future feature)
    max_drawdown_pct: float = 5.0

    # Maximum PnL drift percentage for delta-neutral positions
    #
    # What is drift?
    # - Delta-neutral means LONG and SHORT should offset each other
    # - If BTC moves 1%, your net PnL should be ~0%
    # - If your net PnL is >0.8%, something broke the delta-neutrality
    #
    # Why it matters:
    # - Large drift means you're no longer market-neutral (taking directional risk)
    # - Causes: price slippage, different entry prices, one leg failed to execute
    #
    # What happens at 0.8%:
    # - Bot closes both positions to reset
    # - Better to take small loss and re-enter than risk bigger loss
    #
    # Adjust if needed:
    # - Tighter (0.5%): More conservative, closes positions sooner
    # - Looser (1.5%): More tolerance for temporary imbalances
    max_pnl_drift_pct: float = 0.8

    # Stop-loss percentage per position
    #
    # Traditional stop-loss: Close if loss exceeds this percentage
    #
    # For delta-neutral strategy:
    # - Should rarely trigger (both legs offset each other)
    # - If it triggers, likely one leg had extreme slippage
    # - 1% is generous for a hedged strategy
    #
    # Example:
    # - You open LONG + SHORT for $100 each
    # - If combined loss exceeds $1 (1% of $100), close both positions
    #
    # Note: This is PER POSITION, not per leg
    # The combined pair is considered one logical position
    stop_loss_pct: float = 1.0

    # Funding rate threshold (currently not used in strategy)
    #
    # What is funding rate?
    # - Perpetual swaps pay funding every 8 hours
    # - Positive rate: Longs pay shorts
    # - Negative rate: Shorts pay longs
    #
    # Why it matters for delta-neutral:
    # - You're both long AND short, so funding often cancels out
    # - But if rates are extreme (>5%), one side pays a lot
    # - Future versions might avoid trading during extreme funding
    #
    # This threshold (0.05 = 5%) would trigger funding-based logic
    # E.g., "Don't open positions if funding rate > 5% annualized"
    funding_rate_threshold: float = 0.05

    # ============================================================================
    # DATABASE CONFIGURATION
    # ============================================================================

    # SQLite database file path
    #
    # What's stored here?
    # - Every trade executed (timestamp, price, quantity, PnL)
    # - Every position opened/closed (entry price, exit price, hold time)
    # - Daily statistics (volume, fees, estimated reward points)
    #
    # Why SQLite?
    # - No server required (just a file)
    # - Easy to inspect with DB Browser or Python
    # - Perfect for educational purposes
    # - Production bots might use PostgreSQL for better concurrency
    #
    # You can change this to:
    # - "data/trades.db" (organize in subdirectory)
    # - "aster-operator-2024-01.db" (separate DBs per month)
    db_path: str = "aster-operator.db"

    # ============================================================================
    # PYDANTIC CONFIGURATION
    # ============================================================================
    # This tells Pydantic to load settings from .env file
    # Secrets should NEVER be hardcoded - always use environment variables
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


# Global settings instance
# Import this in other modules: from aster_operator.config.settings import settings
settings = Settings()

