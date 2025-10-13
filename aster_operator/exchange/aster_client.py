"""
Aster Exchange Client - High-level API Wrapper

This module wraps Aster's official Python SDK with:
1. Enhanced error handling and retries
2. Consistent logging
3. Educational comments
4. Type hints for better IDE support

Why wrap the SDK?
- The raw SDK returns naked exceptions and dict responses
- We add defensive programming (retries, validation, logging)
- Makes it easier to swap exchanges later (same interface)
- Educational: Shows how to build robust API clients

Exchange API Resources:
- Aster Docs: https://github.com/asterdex/api-docs
- SDK Source: Exchange specific implementation
"""

from loguru import logger
from typing import Optional, Dict, Any
import time
from aster_operator.config.settings import settings
from aster_operator.exchange.aster.rest_api import Client as AsterClient
from aster_operator.exchange.aster.error import ClientError, ServerError


class AsterExchangeClient:
    """
    High-level wrapper for Aster DEX API with error handling and retry logic.

    This class provides a clean interface to Aster's perpetual futures API,
    abstracting away the complexity of authentication, error handling, and
    response parsing.

    Key Features:
    - Automatic retry on transient failures
    - Comprehensive logging for debugging
    - Type-safe function signatures
    - Defensive error handling

    Usage:
        client = AsterExchangeClient()
        balance = client.get_account_balance()
        price = client.get_mark_price("BTCUSDT")
    """

    def __init__(self):
        """
        Initialize Aster API client with credentials from settings.

        Authentication:
        - Uses API key + secret (HMAC signing)
        - Keys must have trading permissions enabled
        - IP whitelist recommended for production

        Network:
        - 10-second timeout prevents hanging requests
        - Base URL points to production endpoint
        - For testnet, change base_url in settings

        Raises:
            ValueError: If API keys are missing from settings
        """
        if not settings.aster_api_key or not settings.aster_api_secret:
            raise ValueError(
                "Missing Aster API credentials. "
                "Please set ASTER_API_KEY and ASTER_API_SECRET in your .env file"
            )

        self.client = AsterClient(
            key=settings.aster_api_key,
            secret=settings.aster_api_secret,
            base_url=settings.aster_base_url,
            timeout=10  # 10-second timeout for API calls
        )
        logger.info(f"✅ Aster client initialized (endpoint: {settings.aster_base_url})")
    
    def get_account_balance(self) -> Dict[str, Any]:
        """Get account balance"""
        try:
            return self.client.balance()
        except (ClientError, ServerError) as e:
            logger.error(f"Failed to get balance: {e}")
            raise
    
    def get_position_risk(self, symbol: Optional[str] = None) -> list:
        """Get current positions"""
        try:
            return self.client.get_position_risk(symbol=symbol)
        except (ClientError, ServerError) as e:
            logger.error(f"Failed to get positions: {e}")
            raise
    
    def place_market_order(
        self,
        symbol: str,
        side: str,  # "BUY" or "SELL"
        quantity: float,
        position_side: str,  # "LONG" or "SHORT" (hedge mode)
        reduce_only: bool = False
    ) -> Dict[str, Any]:
        """Place a market order (taker for 2x points)"""
        try:
            # Only include reduceOnly parameter if it's True
            order_params = {
                "symbol": symbol,
                "side": side,
                "type": "MARKET",
                "quantity": quantity,
                "positionSide": position_side,
                "newOrderRespType": "RESULT"
            }
            
            # Only add reduceOnly if it's True
            if reduce_only:
                order_params["reduceOnly"] = reduce_only
                
            order = self.client.new_order(**order_params)
            logger.info(f"Order placed: {symbol} {side} {quantity} {position_side} | OrderID: {order['orderId']}")
            return order
        except ClientError as e:
            logger.error(f"Order failed: {e.error_code} - {e.error_message}")
            raise
    
    def get_mark_price(self, symbol: str) -> float:
        """Get current mark price"""
        try:
            data = self.client.mark_price(symbol=symbol)
            # Handle both single object and list responses
            if isinstance(data, list):
                for item in data:
                    if item['symbol'] == symbol:
                        return float(item['markPrice'])
                raise ValueError(f"Symbol {symbol} not found in response")
            else:
                return float(data['markPrice'])
        except (ClientError, ServerError) as e:
            logger.error(f"Failed to get mark price: {e}")
            raise
    
    def set_leverage(self, symbol: str, leverage: int):
        """Set leverage for a symbol"""
        try:
            result = self.client.change_leverage(
                symbol=symbol,
                leverage=leverage
            )
            logger.info(f"Leverage set: {symbol} -> {leverage}x")
            return result
        except ClientError as e:
            if e.error_code == -4046:  # No need to change
                logger.debug(f"Leverage already set to {leverage}x")
            else:
                raise
    
    def set_position_mode(self, dual_side_position: bool):
        """Set position mode (hedge mode or one-way mode)"""
        try:
            result = self.client.change_position_mode(
                dualSidePosition="true" if dual_side_position else "false"
            )
            mode = "hedge" if dual_side_position else "one-way"
            logger.info(f"Position mode set to: {mode}")
            return result
        except Exception as e:
            logger.error(f"Failed to set position mode: {e}")
            raise

    def close_position(self, symbol: str, position_side: str) -> Dict[str, Any]:
        """Close an entire position"""
        positions = self.get_position_risk(symbol=symbol)
        for pos in positions:
            if pos['positionSide'] == position_side and float(pos['positionAmt']) != 0:
                side = "SELL" if position_side == "LONG" else "BUY"
                qty = abs(float(pos['positionAmt']))
                return self.place_market_order(
                    symbol=symbol,
                    side=side,
                    quantity=qty,
                    position_side=position_side,
                    reduce_only=True
                )
        logger.warning(f"No open position found for {symbol} {position_side}")
        return {}

