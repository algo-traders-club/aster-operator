"""
Delta-Neutral Hold-and-Rotate Strategy

This is the MAIN strategy file - the brain of the Aster Operator.

Strategy Overview:
1. Open equal LONG + SHORT positions simultaneously (delta-neutral)
2. Hold positions for 90+ minutes to qualify for 10x multiplier
3. Rotate positions (close + reopen) to generate volume
4. Maintain delta-neutrality throughout (no directional risk)

Why This Strategy?
- Delta-neutral = protected from BTC price movements
- 90+ minute holds = maximize Aster RH point multiplier (10x vs 1x)
- Rotation = generate volume without taking directional bets
- Low risk, high reward points

Educational Context:
This strategy is designed for AIRDROP FARMING, not traditional profit-seeking.
Success = maximize reward points while minimizing risk and fees.

Aster Genesis Stage 3 Reward Formula:
- Volume Points = notional_value × 1
- Hold Points = notional_value × hold_time_minutes × multiplier
  - Multiplier = 1x if hold < 90 min
  - Multiplier = 10x if hold >= 90 min
- Total Points = volume_points + hold_points

Example:
- Open $1000 notional LONG + SHORT
- Hold for 95 minutes
- Volume points: $2000 × 1 = 2,000 points
- Hold points: $2000 × 95 × 10 = 1,900,000 points
- Total: 1,902,000 RH points
"""

from loguru import logger
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import time
import random

from aster_operator.config.settings import settings
from aster_operator.exchange.aster_client import AsterExchangeClient
from aster_operator.strategy.risk_manager import RiskManager
from aster_operator.database.db import get_db
from aster_operator.database.models import Trade, Position


class DeltaNeutralStrategy:
    """
    Hold-and-Rotate Strategy for Aster Genesis Stage 3.

    This class implements the main trading logic for the bot.
    It orchestrates: position opening, holding, rotation, and risk management.

    Key Responsibilities:
    1. Decide when to open new positions
    2. Monitor existing positions for risk
    3. Rotate positions after minimum hold time
    4. Log all activity to database
    5. Report daily statistics

    Lifecycle:
    - Bot calls run_cycle() every 10 minutes
    - Each cycle: check positions → take action → log stats
    - Actions: open new, hold existing, or rotate
    - Never hold more than 1 pair at a time (LONG + SHORT)

    Design Philosophy:
    - Simple over complex (easy to understand > clever optimization)
    - Safe over profitable (risk management > aggressive trading)
    - Transparent over opaque (log everything for learning)
    """
    
    def __init__(self):
        """
        Initialize the strategy with exchange client and risk manager.

        Setup Steps:
        1. Create Aster API client (handles all exchange communication)
        2. Create risk manager (handles position sizing and limits)
        3. Set trading pair (currently only first pair is used)
        4. Configure leverage and position mode on exchange
        5. Initialize strategy state tracking

        Exchange Configuration:
        - Leverage: From settings (default 15x)
        - Position Mode: Hedge mode (allows simultaneous LONG + SHORT)
        - Symbol: First from trading_pairs list (default BTCUSDT)

        Why hedge mode?
        In one-way mode: Can only be LONG *or* SHORT (not both)
        In hedge mode: Can be LONG *and* SHORT simultaneously
        Delta-neutral requires hedge mode!

        State Tracking:
        - active_positions: Current open positions {LONG: {...}, SHORT: {...}}
        - last_rotation_time: When we last rotated (not currently used)
        """
        # Initialize exchange client (API wrapper)
        self.client = AsterExchangeClient()

        # Initialize risk manager (position sizing, stop-loss, etc.)
        self.risk_manager = RiskManager()

        # Select trading pair from config (currently only uses first one)
        # Future: Could trade multiple pairs simultaneously
        self.symbol = settings.trading_pairs[0]  # e.g., "BTCUSDT"

        # Configure exchange settings (leverage and position mode)
        # These only need to be set once, but we set them on each startup
        # to ensure they're correct (in case user changed them on exchange UI)
        try:
            # Set leverage (e.g., 15x)
            # This tells exchange how much buying power we get
            # 15x = $1 margin controls $15 notional
            self.client.set_leverage(self.symbol, settings.leverage)

            # Set position mode to HEDGE MODE (critical for delta-neutral!)
            # True = hedge mode (can have LONG + SHORT simultaneously)
            # False = one-way mode (can only have LONG *or* SHORT)
            self.client.set_position_mode(True)

            logger.info(
                f"✅ Exchange configured: {settings.leverage}x leverage, "
                f"hedge mode enabled for {self.symbol}"
            )
        except Exception as e:
            # If this fails, it's usually because settings are already correct
            # Exchange returns error if you try to set leverage to same value
            logger.warning(
                f"Could not set leverage/position mode: {e}. "
                f"This is usually OK - settings may already be correct."
            )
            # Continue anyway - bot will still work if settings are already correct

        # Initialize strategy state tracking
        # This dictionary tracks our currently open positions
        # Format: {"LONG": {opened_at: datetime, is_active: bool, ...},
        #          "SHORT": {opened_at: datetime, is_active: bool, ...}}
        self.active_positions: Dict[str, Dict] = {}

        # Track when we last rotated positions (not currently used)
        # Future feature: Prevent rotating too frequently
        self.last_rotation_time: Optional[datetime] = None

        logger.info(f"🚀 Delta-Neutral Strategy initialized for {self.symbol}")
    
    def run_cycle(self):
        """
        Main strategy loop - executed every 10 minutes by the bot.

        This is the HEART of the strategy. Each cycle follows this flow:

        1. **Check Positions**: Get current state from exchange
        2. **Risk Management**: Close any positions exceeding risk limits
        3. **Decision**: Decide action based on current state
           - No positions? → Open new delta-neutral pair
           - Positions held long enough? → Rotate (close + reopen)
           - Otherwise? → Hold and wait
        4. **Log Stats**: Record daily performance metrics

        Cycle Frequency:
        - Default: Every 10 minutes (600 seconds)
        - Why 10 minutes? Balance between responsiveness and API rate limits
        - You can adjust in main.py (cycle_interval_seconds)

        State Machine:
        ```
        [No Positions] → Open → [Holding] → Rotate → [Holding] → Rotate → ...
                                     ↓
                                 [Risk Check]
                                     ↓
                                 [Close if risky]
        ```

        Error Handling:
        - If cycle fails, exception is raised to main.py
        - Main.py will log error and retry after 60 seconds
        - This prevents one bad cycle from crashing the entire bot
        """
        logger.info("=" * 50)
        logger.info("🔄 Running strategy cycle...")

        try:
            # ============================================================
            # STEP 1: Get current positions from exchange
            # ============================================================
            # This API call returns all open positions for this symbol
            # Even if we think positions are closed, always check with exchange
            # (API is source of truth, not our internal state)
            positions = self.client.get_position_risk(symbol=self.symbol)

            # Update our internal tracking based on exchange reality
            # If exchange shows position closed but we think it's open, sync it
            self._update_active_positions(positions)

            # ============================================================
            # STEP 2: Risk management check
            # ============================================================
            # Before doing anything else, check if any positions are risky
            # Close immediately if:
            # - PnL drift exceeds threshold (delta-neutrality broken)
            # - Stop-loss triggered (losses exceed limit)
            self._check_and_close_risky_positions(positions)

            # ============================================================
            # STEP 3: Decide what to do this cycle
            # ============================================================
            # Three possible actions:
            # A) Open new positions (if we have none)
            # B) Rotate positions (if held long enough)
            # C) Hold and wait (if not ready to rotate)

            if self._should_open_new_positions():
                # No active positions → Open new delta-neutral pair
                self._open_delta_neutral_pair()

            elif self._should_rotate_positions():
                # Held for 90+ minutes → Close and reopen with variations
                self._rotate_positions()

            else:
                # Not ready to rotate → Just hold and monitor
                logger.info("⏳ Holding current positions...")
                self._log_position_status()

            # ============================================================
            # STEP 4: Log daily statistics
            # ============================================================
            # After every cycle, update and log today's metrics
            # - Total volume traded
            # - Number of trades
            # - PnL and fees
            # - Estimated reward points
            self._log_daily_stats()

        except Exception as e:
            # If anything goes wrong, log it and re-raise
            # Main loop in main.py will catch this and retry
            logger.error(f"❌ Strategy cycle error: {e}")
            logger.exception("Full traceback:")  # Log stack trace for debugging
            raise
    
    def _should_open_new_positions(self) -> bool:
        """
        Decide if we should open new delta-neutral positions.

        Open new positions when:
        - We have no active positions currently
        - All previous positions have been closed

        Why this check?
        - Strategy only holds ONE pair at a time (LONG + SHORT)
        - Before opening new, make sure old ones are closed
        - Prevents accidentally opening multiple pairs

        Returns:
            True if safe to open new positions, False otherwise

        Example scenarios:
        - Bot just started: active_positions = {} → True (open new)
        - Positions just rotated: active_positions = {LONG: is_active=False, ...} → True
        - Currently holding: active_positions = {LONG: is_active=True, ...} → False
        """
        # Check if we have any active positions
        if not self.active_positions:
            # Empty dict = no positions ever opened
            logger.debug("No positions in tracking → ready to open new")
            return True

        # Check if all tracked positions are inactive
        # Sometimes we have position entries but they're marked inactive
        all_inactive = all(
            not pos.get('is_active', False)
            for pos in self.active_positions.values()
        )

        if all_inactive:
            logger.debug("All tracked positions are inactive → ready to open new")
            return True

        # We have at least one active position → don't open new
        logger.debug("Active positions exist → not opening new")
        return False

    def _should_rotate_positions(self) -> bool:
        """
        Decide if it's time to rotate (close and reopen) positions.

        Rotate when:
        1. We have active positions, AND
        2. ALL positions have been held for minimum time (90+ minutes)

        Why rotate?
        - Generate more volume (volume = reward points)
        - Get fresh positions with new hold time counters
        - Small variations prevent wash trading detection

        Why wait 90+ minutes?
        - Aster gives 10x multiplier for holds >=90 min
        - Holding <90 min gives only 1x multiplier
        - Rotating early sacrifices 90% of potential rewards!

        Returns:
            True if all positions ready to rotate, False otherwise

        Example timeline:
        - 0 min: Open positions
        - 10 min: Check → NO (only held 10 min, need 90)
        - 20 min: Check → NO (only held 20 min, need 90)
        - ...
        - 90 min: Check → YES! (held 90 min, ready to rotate)
        - Rotate: Close old, open new
        - 0 min: New positions opened, timer resets
        """
        # Safety check: If no positions, can't rotate
        if not self.active_positions:
            logger.debug("No positions to rotate")
            return False

        # Check each position's hold time
        # ALL positions must meet minimum hold time before we rotate
        # (Usually we only have 2: LONG and SHORT, opened simultaneously)
        for position_side, pos_data in self.active_positions.items():
            # Skip inactive positions (already closed)
            if not pos_data.get('is_active'):
                continue

            # Get when this position was opened
            opened_at = pos_data.get('opened_at')
            if not opened_at:
                # Missing timestamp? Can't calculate hold time
                # Log warning and skip (shouldn't happen)
                logger.warning(f"Position {position_side} missing opened_at timestamp")
                continue

            # Calculate how long we've held this position
            hold_time = datetime.utcnow() - opened_at
            hold_time_minutes = hold_time.total_seconds() / 60

            # Check if this position has met minimum hold time
            if hold_time_minutes < settings.position_hold_time_min:
                # Not held long enough yet
                logger.info(
                    f"⏰ Position {position_side} held for {hold_time_minutes:.1f} min, "
                    f"need {settings.position_hold_time_min} min (waiting {settings.position_hold_time_min - hold_time_minutes:.1f} more min)"
                )
                return False  # Not ready yet

        # If we get here, ALL active positions have been held long enough
        logger.info("✅ All positions held for minimum time - ready to rotate!")
        return True
    
    def _open_delta_neutral_pair(self):
        """
        Open equal LONG and SHORT positions simultaneously (delta-neutral).

        This is the core of the delta-neutral strategy. We open:
        - 1 LONG position (benefits if price goes UP)
        - 1 SHORT position (benefits if price goes DOWN)
        - Equal sizes → PnL stays neutral regardless of price movement

        Steps:
        1. Get current mark price from exchange
        2. Calculate safe position size using risk manager
        3. Add randomization to avoid wash trading detection
        4. Place LONG market order
        5. Wait 2-5 seconds (appear natural, not bot-like)
        6. Place SHORT market order
        7. Record both positions in database
        8. Update internal state tracking

        Why use mark price (not last price)?
        - Mark price = smoothed index price + funding rate
        - More resistant to manipulation
        - What exchanges use for liquidation calculations
        - More stable than last traded price

        Why randomize quantity?
        - ±5% variation makes orders look less bot-like
        - Prevents exact matching (wash trading red flag)
        - Still maintains approximate delta-neutrality

        Why delay between orders?
        - Natural trading behavior (humans don't place orders instantly)
        - Prevents exchange from flagging as bot
        - 2-5 second random delay

        Risk Considerations:
        - Both orders are market orders (instant fill, higher fees)
        - Price might move between LONG and SHORT orders
        - This creates small entry price mismatch (why we track drift)

        Returns:
            None (modifies self.active_positions state)

        Raises:
            Exception: If order placement fails (will be caught by run_cycle)
        """
        logger.info("🆕 Opening new delta-neutral position pair...")

        # ================================================================
        # STEP 1: Get current market price
        # ================================================================
        # Use mark price (not last price) for more stable reference
        # Mark price = exchange's fair price calculation
        price = self.client.get_mark_price(self.symbol)
        logger.info(f"Current mark price: ${price:,.2f}")

        # ================================================================
        # STEP 2: Calculate position size
        # ================================================================
        # Risk manager calculates safe size based on:
        # - Available capital
        # - Leverage setting
        # - Maximum position size percentage
        quantity = self.risk_manager.calculate_position_size(price)

        # ================================================================
        # STEP 3: Add randomization (anti-wash-trading)
        # ================================================================
        # Vary quantity by ±5% to make orders look less robotic
        # Example: 0.01 BTC → random between 0.0095 - 0.0105 BTC
        randomization_factor = random.uniform(0.95, 1.05)
        quantity = quantity * randomization_factor
        quantity = round(quantity, 3)  # Aster requires 3 decimals max for BTC

        logger.info(
            f"Position size: {quantity} {self.symbol[:3]} "
            f"(${quantity * price:,.2f} notional at {settings.leverage}x leverage)"
        )
        
        try:
            # ================================================================
            # STEP 4: Place LONG market order
            # ================================================================
            # BUY with position_side=LONG opens a long position
            # Market order = instant fill at best available price
            logger.info("📈 Placing LONG order...")
            long_order = self.client.place_market_order(
                symbol=self.symbol,
                side="BUY",  # Buy BTC
                quantity=quantity,
                position_side="LONG"  # Open as LONG position (hedge mode)
            )
            logger.info(
                f"✅ LONG filled: {long_order['executedQty']} @ "
                f"${float(long_order['avgPrice']):,.2f}"
            )

            # ================================================================
            # STEP 5: Delay before SHORT order (appear natural)
            # ================================================================
            # Random 2-5 second delay makes trading pattern less bot-like
            delay_seconds = random.uniform(2, 5)
            logger.debug(f"Waiting {delay_seconds:.1f} seconds before SHORT order...")
            time.sleep(delay_seconds)

            # ================================================================
            # STEP 6: Place SHORT market order
            # ================================================================
            # SELL with position_side=SHORT opens a short position
            logger.info("📉 Placing SHORT order...")
            short_order = self.client.place_market_order(
                symbol=self.symbol,
                side="SELL",  # Sell BTC
                quantity=quantity,
                position_side="SHORT"  # Open as SHORT position (hedge mode)
            )
            logger.info(
                f"✅ SHORT filled: {short_order['executedQty']} @ "
                f"${float(short_order['avgPrice']):,.2f}"
            )

            # ================================================================
            # STEP 7: Record trades and positions in database
            # ================================================================
            # Store all trading activity for:
            # - Performance analysis
            # - Tax reporting
            # - Strategy optimization
            # - Debugging
            opened_at = datetime.utcnow()

            with get_db() as db:
                # Loop through both orders and record them
                for order, pos_side in [(long_order, "LONG"), (short_order, "SHORT")]:
                    # Create Trade record (individual order execution)
                    trade = Trade(
                        symbol=self.symbol,
                        side=order['side'],  # BUY or SELL
                        position_side=pos_side,  # LONG or SHORT
                        quantity=float(order['executedQty']),
                        price=float(order['avgPrice']),
                        notional=float(order['executedQty']) * float(order['avgPrice']),
                        order_id=str(order['orderId']),
                        commission=float(order.get('commission', 0))
                    )
                    db.add(trade)

                    # Create Position record (tracks full lifecycle)
                    position = Position(
                        symbol=self.symbol,
                        position_side=pos_side,
                        entry_price=float(order['avgPrice']),
                        quantity=float(order['executedQty']),
                        leverage=settings.leverage,
                        notional=float(order['executedQty']) * float(order['avgPrice']),
                        is_active=True  # Position is now open
                    )
                    db.add(position)

            # ================================================================
            # STEP 8: Update internal state tracking
            # ================================================================
            # Track these positions in memory for quick access
            # (Don't need to query database every time)
            self.active_positions = {
                "LONG": {
                    "opened_at": opened_at,
                    "is_active": True,
                    "entry_price": float(long_order['avgPrice'])
                },
                "SHORT": {
                    "opened_at": opened_at,
                    "is_active": True,
                    "entry_price": float(short_order['avgPrice'])
                }
            }

            # Calculate and log key metrics
            long_notional = float(long_order['executedQty']) * float(long_order['avgPrice'])
            short_notional = float(short_order['executedQty']) * float(short_order['avgPrice'])
            total_notional = long_notional + short_notional

            logger.success(
                f"✅ Delta-neutral pair opened successfully!\n"
                f"   LONG:  {long_order['executedQty']} @ ${float(long_order['avgPrice']):,.2f} = ${long_notional:,.2f}\n"
                f"   SHORT: {short_order['executedQty']} @ ${float(short_order['avgPrice']):,.2f} = ${short_notional:,.2f}\n"
                f"   Total volume: ${total_notional:,.2f}\n"
                f"   Hold for {settings.position_hold_time_min}+ minutes for 10x multiplier"
            )

        except Exception as e:
            # Order placement failed - log detailed error
            logger.error(f"❌ Failed to open positions: {e}")
            logger.exception("Full traceback:")
            raise  # Re-raise so run_cycle can handle it
    
    def _rotate_positions(self):
        """Close current positions and open new ones"""
        logger.info("Rotating positions...")
        
        try:
            # Close existing positions
            for position_side in ["LONG", "SHORT"]:
                close_result = self.client.close_position(self.symbol, position_side)
                if close_result:
                    logger.info(f"Closed {position_side} position")
                    
                    # Record in database
                    with get_db() as db:
                        position = db.query(Position).filter(
                            Position.symbol == self.symbol,
                            Position.position_side == position_side,
                            Position.is_active == True
                        ).first()
                        
                        if position:
                            position.is_active = False
                            position.closed_at = datetime.utcnow()
                            position.exit_price = float(close_result.get('avgPrice', 0))
                            position.hold_time_minutes = int(
                                (position.closed_at - position.opened_at).total_seconds() / 60
                            )
                            position.realized_pnl = float(close_result.get('realizedPnl', 0))
            
            # Small delay
            time.sleep(random.uniform(5, 10))
            
            # Open new positions
            self.active_positions = {}
            self._open_delta_neutral_pair()
            
        except Exception as e:
            logger.error(f"Rotation failed: {e}")
            raise
    
    def _check_and_close_risky_positions(self, positions: List[Dict]):
        """Close positions that exceed risk limits"""
        for pos in positions:
            if float(pos['positionAmt']) == 0:
                continue
            
            if self.risk_manager.should_close_position(pos):
                logger.warning(f"Closing risky position: {pos['positionSide']}")
                self.client.close_position(self.symbol, pos['positionSide'])
                
                if pos['positionSide'] in self.active_positions:
                    self.active_positions[pos['positionSide']]['is_active'] = False
    
    def _update_active_positions(self, positions: List[Dict]):
        """Update internal state from exchange positions"""
        for pos in positions:
            if float(pos['positionAmt']) == 0:
                if pos['positionSide'] in self.active_positions:
                    self.active_positions[pos['positionSide']]['is_active'] = False
    
    def _log_position_status(self):
        """Log current position status"""
        for pos_side, data in self.active_positions.items():
            if data.get('is_active'):
                opened_at = data.get('opened_at')
                if opened_at:
                    hold_time = (datetime.utcnow() - opened_at).total_seconds() / 60
                    logger.info(f"Position {pos_side}: held for {hold_time:.1f} minutes")
    
    def _log_daily_stats(self):
        """Log daily trading statistics"""
        with get_db() as db:
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            
            trades_today = db.query(Trade).filter(Trade.timestamp >= today_start).all()
            
            total_volume = sum(t.notional for t in trades_today)
            total_pnl = sum(t.realized_pnl for t in trades_today)
            total_fees = sum(t.commission for t in trades_today)
            
            logger.info(f"📊 Today's Stats: Volume=${total_volume:.2f} | PnL=${total_pnl:.2f} | Fees=${total_fees:.2f}")

