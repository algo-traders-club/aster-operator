"""
Database Models - Trade and Position Tracking

This module defines SQLAlchemy models for storing all trading activity.

Why track everything?
1. Analyze performance: What worked? What didn't?
2. Calculate metrics: Win rate, Sharpe ratio, max drawdown
3. Debug issues: "Why did the bot do that?"
4. Tax reporting: Export trades for accounting
5. Optimization: Backtest strategy improvements

Educational Note:
- Using SQLAlchemy ORM makes database operations Pythonic
- Models map to database tables automatically
- Easy to query: db.query(Trade).filter(Trade.symbol == "BTCUSDT")
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class Trade(Base):
    """
    Records every individual order execution.

    Each market order that fills becomes a Trade record.
    This is your audit trail - every action the bot takes is logged here.

    Use cases:
    - Calculate daily volume: SUM(notional) WHERE date = today
    - Analyze entry prices: AVG(price) by side
    - Track fees paid: SUM(commission)
    - Export for tax reporting

    Example row:
    - timestamp: 2025-01-15 10:30:00
    - symbol: BTCUSDT
    - side: BUY
    - position_side: LONG
    - quantity: 0.01 BTC
    - price: $50,000
    - notional: $500
    - commission: $0.25 (0.05% maker fee)
    """

    __tablename__ = "trades"

    # Primary key (auto-incrementing ID)
    id = Column(Integer, primary_key=True)

    # When this trade executed (UTC timezone)
    # Why UTC? No daylight savings confusion, standard for exchanges
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Trading pair (e.g., "BTCUSDT", "ETHUSDT")
    symbol = Column(String, nullable=False)

    # BUY or SELL (from exchange perspective)
    # BUY = you're buying the base currency (BTC)
    # SELL = you're selling the base currency (BTC)
    side = Column(String, nullable=False)

    # LONG or SHORT (for hedge mode)
    # This is separate from side because:
    # - To open LONG: BUY with position_side=LONG
    # - To close LONG: SELL with position_side=LONG
    # - To open SHORT: SELL with position_side=SHORT
    # - To close SHORT: BUY with position_side=SHORT
    position_side = Column(String, nullable=False)

    # Order type (MARKET, LIMIT, etc.)
    # We use MARKET for instant fills (higher fees but guaranteed execution)
    order_type = Column(String, default="MARKET")

    # How much we traded (in base currency, e.g., BTC)
    quantity = Column(Float, nullable=False)

    # Execution price (average if partial fills)
    price = Column(Float, nullable=False)

    # Total USD value: quantity × price
    # This is what counts toward volume rewards on Aster
    notional = Column(Float, nullable=False)

    # Unique order ID from exchange (for reconciliation)
    order_id = Column(String, unique=True)

    # Realized PnL from this trade (if closing position)
    # Opening trade: $0 (no PnL yet)
    # Closing trade: actual profit/loss from price difference
    realized_pnl = Column(Float, default=0.0)

    # Trading fees paid (maker = lower, taker = higher)
    # Aster fees: ~0.02% maker, ~0.05% taker
    commission = Column(Float, default=0.0)

    # Order status (FILLED, PARTIALLY_FILLED, CANCELLED, etc.)
    # We only store FILLED orders
    status = Column(String, default="FILLED")

    def __repr__(self):
        return f"<Trade {self.symbol} {self.side} {self.quantity} @ {self.price}>"


class Position(Base):
    """
    Tracks the full lifecycle of each position (open → hold → close).

    A Position represents a LONG or SHORT that we hold over time.
    Unlike Trade (which is instantaneous), Position has duration.

    Why separate from Trade?
    - One Position = multiple Trades (open + close + maybe adjustments)
    - Track hold time (critical for Aster 10x multiplier)
    - Calculate position-level PnL
    - Monitor risk per position

    Example lifecycle:
    1. opened_at: 2025-01-15 10:00:00
    2. Hold for 95 minutes (above 90-min threshold)
    3. closed_at: 2025-01-15 11:35:00
    4. hold_time_minutes: 95
    5. realized_pnl: +$5.23 (lucky)

    Aster Reward Calculation:
    - Volume points: notional × 1
    - Hold points: notional × hold_time_minutes × 10 (if >90 min)
    - Total points = volume_points + hold_points
    """

    __tablename__ = "positions"

    id = Column(Integer, primary_key=True)

    # When position was opened (first trade)
    opened_at = Column(DateTime, default=datetime.utcnow)

    # When position was closed (last trade)
    # NULL = still open
    closed_at = Column(DateTime, nullable=True)

    # Trading pair
    symbol = Column(String, nullable=False)

    # LONG or SHORT
    position_side = Column(String, nullable=False)

    # Price when we entered the position
    # Used to calculate PnL: (exit_price - entry_price) × quantity
    entry_price = Column(Float, nullable=False)

    # Price when we closed (NULL if still open)
    exit_price = Column(Float, nullable=True)

    # Position size in base currency
    quantity = Column(Float, nullable=False)

    # Leverage used (e.g., 15x)
    # Important for calculating margin requirements
    leverage = Column(Integer, nullable=False)

    # Total notional value: quantity × entry_price
    # This is what counts for reward calculations
    notional = Column(Float, nullable=False)

    # How long we held this position (minutes)
    # Critical metric: >90 minutes = 10x multiplier on Aster
    hold_time_minutes = Column(Integer, default=0)

    # Final PnL when position closed
    # LONG PnL: (exit_price - entry_price) × quantity
    # SHORT PnL: (entry_price - exit_price) × quantity
    realized_pnl = Column(Float, default=0.0)

    # Is this position currently open?
    # True = open, False = closed
    # Used for querying: "Show me all active positions"
    is_active = Column(Boolean, default=True)

    def __repr__(self):
        return f"<Position {self.symbol} {self.position_side} {self.quantity}>"


class DailyStats(Base):
    """
    Aggregated daily performance metrics.

    This table summarizes each day's trading activity for quick analysis.

    Use cases:
    - Dashboard: "How did I do today?"
    - Leaderboards: "Top volume day this week?"
    - Optimization: "Which days are most profitable?"
    - Reward estimation: "How many RH points earned?"

    Updated once per day (or per cycle if you want real-time updates).

    Example row (good day):
    - date: 2025-01-15
    - total_volume: $18,450 (exceeded $15K target!)
    - num_trades: 24 (12 position rotations)
    - realized_pnl: +$23.50 (small profit, mainly from funding)
    - fees_paid: $9.23 (0.05% avg on $18,450)
    - rh_points_estimated: 2,450,000 (volume + hold time)
    """

    __tablename__ = "daily_stats"

    id = Column(Integer, primary_key=True)

    # Date of this stats snapshot (one row per day)
    date = Column(DateTime, default=datetime.utcnow)

    # Total volume traded (sum of all notional values)
    # Goal: Meet or exceed DAILY_VOLUME_TARGET from settings
    total_volume = Column(Float, default=0.0)

    # Total number of trades executed
    # More trades = more fees, but also more volume for rewards
    num_trades = Column(Integer, default=0)

    # Net profit/loss for the day
    # Includes: realized PnL from positions + funding payments - fees
    # For delta-neutral strategy, expect small positive/negative (near $0)
    realized_pnl = Column(Float, default=0.0)

    # Total trading fees paid
    # This is your main "cost" for generating volume
    # Track to ensure fees < reward value
    fees_paid = Column(Float, default=0.0)

    # Estimated Reward Handle (RH) points earned
    # Formula (Aster Genesis Stage 3):
    # - Volume points: total_volume × 1
    # - Hold points: SUM(notional × hold_time_minutes × 10) for holds >90min
    # This is an estimate - actual points calculated by Aster
    rh_points_estimated = Column(Float, default=0.0)

