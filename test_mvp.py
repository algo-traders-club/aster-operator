"""Quick MVP validation tests"""
from aster_operator.config.settings import settings
from aster_operator.exchange.aster_client import AsterExchangeClient
from aster_operator.database.db import init_db, get_db
from aster_operator.database.models import Trade
from aster_operator.strategy.risk_manager import RiskManager

def test_connection():
    """Test Aster API connection"""
    print("🧪 Testing Aster API connection...")
    client = AsterExchangeClient()
    balance = client.get_account_balance()
    print(f"✅ Connected! Balance: {balance}")
    
    price = client.get_mark_price("BTCUSDT")
    print(f"✅ BTC Price: ${price}")

def test_database():
    """Test database creation"""
    print("\n🧪 Testing database...")
    init_db()
    print("✅ Database initialized")

def test_risk_manager():
    """Test risk calculations"""
    print("\n🧪 Testing risk manager...")
    rm = RiskManager()
    
    price = 45000  # Example BTC price
    size = rm.calculate_position_size(price)
    notional = size * price
    
    print(f"✅ Position size: {size} BTC (${notional:.2f} notional)")
    assert notional <= (settings.capital_usdt * settings.max_position_size_pct / 100 * settings.leverage)

if __name__ == "__main__":
    test_connection()
    test_database()
    test_risk_manager()
    print("\n✅ All tests passed! Ready to run MVP.")

