"""
Risk Manager - Position Sizing and Risk Controls

This module handles all risk-related calculations:
1. Position sizing (how much to trade)
2. Risk limit checks (when to close positions)
3. Exposure management (total capital at risk)

Educational Context:
Risk management is the MOST important part of trading bots. Even the best
strategy will fail without proper risk controls. This module is your safety net.
"""

from loguru import logger
from aster_operator.config.settings import settings
from typing import Dict, Any


class RiskManager:
    """
    Manages position sizing and risk controls for the trading bot.

    Key Responsibilities:
    - Calculate safe position sizes based on capital and leverage
    - Monitor positions for risk limit breaches
    - Prevent over-leveraging across multiple positions
    - Maintain delta-neutral balance

    Philosophy:
    Better to miss profits than to risk catastrophic losses.
    """

    def __init__(self):
        """
        Initialize risk manager with settings from config.

        These values are cached at initialization to ensure consistency
        throughout a trading cycle (even if settings file changes).
        """
        self.capital = settings.capital_usdt
        self.max_position_size_pct = settings.max_position_size_pct
        self.leverage = settings.leverage
        self.stop_loss_pct = settings.stop_loss_pct

    def calculate_position_size(self, price: float) -> float:
        """
        Calculate position size in base currency (e.g., BTC for BTCUSDT).

        Formula Breakdown:
        1. Calculate max notional (USD value): capital × position% × leverage
        2. Convert to base currency: notional ÷ price

        Example with defaults:
        - Capital: $1000
        - Max position size: 1.5% of capital
        - Leverage: 15x
        - BTC price: $50,000

        Step 1: Max notional = $1000 × 0.015 × 15 = $225
        Step 2: Quantity = $225 ÷ $50,000 = 0.0045 BTC

        This means you'd buy/sell 0.0045 BTC ($225 notional at 15x leverage).

        Why this approach?
        - Scales with your capital (more capital = larger positions)
        - Leveraged notional generates volume for rewards
        - Percentage-based keeps risk consistent across different capital levels

        Parameters:
            price: Current price of the asset (e.g., $50,000 for BTC)

        Returns:
            Position size in base currency (e.g., 0.0045 BTC)

        Note:
            Rounded to 3 decimal places for BTC. Adjust for other assets
            (e.g., ETH might use 2 decimals, altcoins might use 0-1).
        """
        # Calculate maximum notional value (USD) for this position
        # This is how much "buying power" we have with leverage
        max_notional = self.capital * (self.max_position_size_pct / 100) * self.leverage

        # Convert notional to quantity in base currency
        # E.g., $225 ÷ $50,000/BTC = 0.0045 BTC
        quantity = max_notional / price

        # Round to reasonable precision
        # BTC: 0.001 (3 decimals) is typical minimum on most exchanges
        # Adjust this for other assets (ETH = 2 decimals, DOGE = 0 decimals, etc.)
        quantity = round(quantity, 3)

        logger.debug(
            f"Position size calculated: {quantity} units @ ${price:,.2f} "
            f"= ${quantity * price:,.2f} notional (with {self.leverage}x leverage)"
        )

        return quantity

    def should_close_position(self, position: Dict[str, Any]) -> bool:
        """
        Check if a position should be closed due to risk limits.

        This function is called periodically to monitor each open position.
        It checks two main risk factors:
        1. Stop-loss: Absolute loss limit (default 1%)
        2. Drift: Delta-neutral imbalance (default 0.8%)

        Why we need this:
        - Prevents small losses from becoming large losses
        - Detects when delta-neutrality breaks down
        - Acts as automated risk management (no emotion, no hesitation)

        Parameters:
            position: Position dict from exchange API containing:
                - unRealizedProfit: Current unrealized PnL in USD
                - entryPrice: Price when position was opened
                - positionAmt: Position size (negative for shorts)

        Returns:
            True if position should be closed, False otherwise

        Example scenarios:

        Scenario 1: Normal delta-neutral position
        - LONG: 0.01 BTC @ $50,000, PnL: -$5
        - SHORT: 0.01 BTC @ $50,000, PnL: +$5
        - Combined PnL: $0 (0% drift) → Keep open ✓

        Scenario 2: Dangerous drift
        - LONG: 0.01 BTC @ $50,000, PnL: +$50
        - SHORT: 0.01 BTC @ $50,200, PnL: -$45
        - Net PnL: +$5 (1% drift) → Close and reset ✗

        Scenario 3: Stop-loss hit
        - LONG: 0.01 BTC @ $50,000, PnL: -$600
        - SHORT: 0.01 BTC @ $50,000, PnL: -$600
        - Combined PnL: -$1200 (>1% loss) → Close immediately ✗
        """
        unrealized_pnl = float(position.get("unRealizedProfit", 0))
        entry_price = float(position.get("entryPrice", 0))
        position_amt = float(position.get("positionAmt", 0))

        # Safety check: If entry price is 0, something is wrong with the data
        # Don't close based on bad data - log error and skip
        if entry_price == 0 or position_amt == 0:
            logger.error(
                f"Invalid position data: entryPrice={entry_price}, "
                f"positionAmt={position_amt}"
            )
            return False

        # Calculate PnL as percentage of position value
        # This normalizes PnL across different position sizes
        # Formula: (unrealized_pnl / position_value) × 100
        position_value = abs(entry_price * position_amt)
        pnl_pct = (unrealized_pnl / position_value) * 100

        # Risk Check #1: Stop-loss
        # If loss exceeds stop_loss_pct (default 1%), close immediately
        # Using abs() because we care about magnitude of loss, not direction
        if abs(pnl_pct) > self.stop_loss_pct:
            logger.warning(
                f"⚠️ STOP-LOSS TRIGGERED: PnL {pnl_pct:.2f}% exceeds limit of {self.stop_loss_pct}%"
            )
            logger.warning(
                f"Position details: {position_amt} units @ ${entry_price:,.2f}, "
                f"Unrealized PnL: ${unrealized_pnl:.2f}"
            )
            return True

        # Risk Check #2: Delta-neutral drift
        # For delta-neutral strategy, PnL should be near 0%
        # If it drifts too far, one leg is outperforming (or underperforming) the other
        # This means we're taking directional risk - not what we want!
        if abs(pnl_pct) > settings.max_pnl_drift_pct:
            logger.warning(
                f"⚠️ DELTA DRIFT DETECTED: PnL {pnl_pct:.2f}% exceeds drift limit of {settings.max_pnl_drift_pct}%"
            )
            logger.warning(
                f"This means your LONG and SHORT positions are imbalanced. "
                f"Closing to reset delta-neutrality."
            )
            return True

        # All checks passed - position is within acceptable risk
        return False

    def get_current_exposure(self, positions: list) -> float:
        """
        Calculate total notional exposure across all positions.

        Exposure = total dollar value at risk across all positions.

        Why track this?
        - Prevents over-leveraging (opening too many positions)
        - Ensures we stay within capital limits
        - Helps visualize total risk

        Example:
        Position 1: 0.01 BTC @ $50,000 = $500 notional
        Position 2: 0.02 BTC @ $50,000 = $1,000 notional
        Total exposure: $1,500

        If your capital is $1,000 at 15x leverage:
        Max safe exposure ≈ $7,500 (1,000 × 15 × 0.5)
        Current exposure: $1,500 (20% of max) ✓ Safe

        Parameters:
            positions: List of position dicts from exchange API

        Returns:
            Total notional exposure in USD

        Note:
            Uses abs() because we care about exposure magnitude, not direction.
            Short -0.01 BTC is same exposure as Long +0.01 BTC.
        """
        total = sum(
            abs(float(pos["positionAmt"])) * float(pos["entryPrice"])
            for pos in positions
            if float(pos["positionAmt"]) != 0  # Skip closed positions
        )

        logger.debug(f"Current total exposure: ${total:,.2f} across {len(positions)} positions")

        return total

    def can_open_new_position(self, price: float, positions: list) -> bool:
        """
        Check if we can safely open a new position.

        This prevents over-leveraging by ensuring new positions don't
        exceed our maximum exposure limits.

        Logic:
        1. Calculate current exposure from existing positions
        2. Calculate exposure from proposed new position
        3. Check if total would exceed safe limits

        Maximum safe exposure formula:
        capital × leverage × safety_factor

        Why 0.5 (50%) safety factor?
        - Gives us breathing room for price movements
        - Prevents liquidation even if positions move against us
        - Accounts for funding fees and slippage

        Example scenario:
        Capital: $1,000
        Leverage: 15x
        Max theoretical exposure: $15,000 (100%)
        Max SAFE exposure: $7,500 (50%)

        Current positions: $6,000 notional
        New position: $2,000 notional
        Total would be: $8,000

        $8,000 > $7,500 → REJECT ✗

        Parameters:
            price: Current asset price
            positions: List of existing positions

        Returns:
            True if new position is safe to open, False otherwise

        Note:
            This is a conservative check. You can adjust the 0.5 factor:
            - More aggressive: 0.7 (use 70% of max leverage)
            - More conservative: 0.3 (use 30% of max leverage)
        """
        current_exposure = self.get_current_exposure(positions)

        # Calculate notional value of proposed new position
        new_position_size = self.calculate_position_size(price)
        new_notional = new_position_size * price

        # Maximum safe exposure = 50% of full leverage capacity
        # This conservative limit protects against liquidation
        max_total_exposure = self.capital * self.leverage * 0.5

        total_exposure_if_opened = current_exposure + new_notional

        if total_exposure_if_opened > max_total_exposure:
            logger.warning(
                f"❌ Cannot open new position: would exceed safe exposure limits"
            )
            logger.warning(
                f"Current exposure: ${current_exposure:,.2f}"
            )
            logger.warning(
                f"New position notional: ${new_notional:,.2f}"
            )
            logger.warning(
                f"Total would be: ${total_exposure_if_opened:,.2f} "
                f"(max safe: ${max_total_exposure:,.2f})"
            )
            return False

        logger.debug(
            f"✅ Safe to open position: ${total_exposure_if_opened:,.2f} / ${max_total_exposure:,.2f} "
            f"({(total_exposure_if_opened/max_total_exposure)*100:.1f}% of max)"
        )

        return True

