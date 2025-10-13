#!/usr/bin/env python3
"""
Aster Operator - Delta-Neutral Trading Bot for Aster DEX
"""
import time
from loguru import logger
from aster_operator.database.db import init_db
from aster_operator.strategy.delta_neutral import DeltaNeutralStrategy
from aster_operator.config.settings import settings

def setup_logging():
    """Configure logging"""
    logger.add(
        "logs/aster-operator_{time}.log",
        rotation="1 day",
        retention="30 days",
        level="INFO"
    )

def main():
    """Main bot loop"""
    setup_logging()
    logger.info("=" * 60)
    logger.info("🚀 Aster Operator Starting...")
    logger.info(f"Capital: ${settings.capital_usdt}")
    logger.info(f"Leverage: {settings.leverage}x")
    logger.info(f"Target Daily Volume: ${settings.daily_volume_target}")
    logger.info("=" * 60)
    
    # Initialize database
    init_db()
    
    # Initialize strategy
    strategy = DeltaNeutralStrategy()
    
    # Main loop - run every 10 minutes
    cycle_interval_seconds = 600  # 10 minutes
    
    try:
        while True:
            try:
                strategy.run_cycle()
            except Exception as e:
                logger.error(f"Cycle error: {e}")
                logger.info("Continuing in 60 seconds...")
                time.sleep(60)
                continue
            
            logger.info(f"Sleeping for {cycle_interval_seconds} seconds...")
            time.sleep(cycle_interval_seconds)
            
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        raise

if __name__ == "__main__":
    main()
