# Aster Operator 🤖

*Part of the [Algo Traders Club](https://algotradersclub.com) Operator Series*

> "An operator is a crewmember who assists redpills in the Matrix by providing information, resources, and protection." - The Matrix

In crypto trading, an **Operator** is your automated assistant that connects to a perps DEX, executes strategies, manages risk, and logs everything for analysis.

This is the **Aster Operator** - a delta-neutral trading bot for [Aster DEX](https://asterdex.com) designed to farm Reward Handle (RH) points during their Genesis Stage 3 airdrop program.

---

## 🎯 What This Bot Does

**Strategy**: Delta-Neutral Hold-and-Rotate
- Opens equal LONG and SHORT positions (no directional bias)
- Holds for 90+ minutes (10x holding time multiplier for points)
- Rotates positions to generate volume while staying market-neutral
- Targets: $15K daily volume, $200K weekly holding time equivalent

**Why This Strategy?**
1. **Low Risk**: Delta-neutral = protected from BTC price swings
2. **High Points**: Volume + hold time = maximum Aster RH points
3. **Educational**: Learn position management, risk controls, exchange APIs
4. **Reproducible**: Works on other DEXs with similar reward structures

---

## 📚 Learning Objectives

By studying and running this bot, you'll learn:

- ✅ **Exchange API Integration**: Connect to perps DEX, authenticate, place orders
- ✅ **Position Management**: Open, monitor, and close leveraged positions
- ✅ **Risk Management**: Calculate position sizes, set stop-losses, handle liquidations
- ✅ **Delta-Neutral Strategies**: How to profit without predicting price direction
- ✅ **Database Design**: Store trades for analysis and optimization
- ✅ **Error Handling**: Retry logic, rate limiting, graceful failures
- ✅ **Airdrop Farming**: Optimize trading for reward points (not just P&L)

---

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Aster DEX account ([Sign up](https://asterdex.com))
- Basic understanding of perpetual futures trading
- Testnet USDT (for practice) or Real USDT (for production)

### Installation

1. **Clone the repo**
   ```bash
   git clone https://github.com/algotradersclub/aster-operator.git
   cd aster-operator
   ```

2. **Install dependencies**
   ```bash
   # Using uv (recommended)
   uv sync

   # Or using pip
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

4. **Initialize database**
   ```bash
   python -m aster_operator.database.db
   ```

5. **Run the bot**
   ```bash
   # Using uv
   uv run python main.py

   # Or using python directly
   python main.py
   ```

---

## ⚙️ Configuration

Edit `.env` to customize the strategy:

```bash
# API Credentials (get from Aster DEX settings)
ASTER_API_KEY=your_api_key_here
ASTER_API_SECRET=your_api_secret_here
WALLET_ADDRESS=your_wallet_address

# Trading Settings
CAPITAL_USDT=100.0          # How much capital to deploy
LEVERAGE=15                 # Leverage multiplier (15x recommended)
TRADING_PAIRS=["BTCUSDT"]   # Which pairs to trade

# Strategy Parameters
POSITION_HOLD_TIME_MIN=90   # Hold positions for 90+ minutes (10x multiplier)
MAX_POSITION_SIZE_PCT=1.5   # Use 1.5% of capital per position
DAILY_VOLUME_TARGET=15000   # Target $15K daily volume

# Risk Management
STOP_LOSS_PCT=1.0           # Close if loss exceeds 1%
MAX_PNL_DRIFT_PCT=0.8       # Close if delta neutrality drifts >0.8%
```

**Important Settings Explained:**

- **LEVERAGE**: Higher leverage = more volume per dollar BUT higher liquidation risk. Start low (5-10x), increase gradually.
- **POSITION_HOLD_TIME_MIN**: Aster rewards 10x points for holds >90 min. Don't go below this.
- **MAX_POSITION_SIZE_PCT**: Keeps each position small relative to capital. Protects from single-position wipeout.

---

## 📖 How It Works

### The Strategy Loop

```
1. Check Current Positions
   ↓
2. Are positions risky? → YES → Close them
   ↓ NO
3. Should we open new positions? → YES → Open delta-neutral pair
   ↓ NO
4. Should we rotate? → YES → Close + reopen with variations
   ↓ NO
5. Hold and monitor
   ↓
6. Log stats
   ↓
[Repeat every 10 minutes]
```

### Delta-Neutral Explained

**Delta-neutral** = Your P&L doesn't change when price moves.

Example:
- BTC at $50,000
- Open LONG: Buy 0.1 BTC
- Open SHORT: Sell 0.1 BTC

**Outcome:**
- BTC up to $51,000? → LONG gains $100, SHORT loses $100 = Net $0
- BTC down to $49,000? → LONG loses $100, SHORT gains $100 = Net $0

**Why do this?**
- You're not gambling on price direction
- You earn reward points from volume + hold time
- Risk is minimized to funding rate exposure (small)

---

## 🗂️ Project Structure

```
aster-operator/
├── aster_operator/
│   ├── config/
│   │   └── settings.py          # All configuration in one place
│   ├── database/
│   │   ├── db.py                # Database connection & session management
│   │   └── models.py            # Trade, Position, DailyStats models
│   ├── exchange/
│   │   ├── aster/               # Aster DEX official SDK (wrapped)
│   │   └── aster_client.py      # High-level client (error handling, retries)
│   ├── strategy/
│   │   ├── delta_neutral.py     # The main strategy logic
│   │   └── risk_manager.py      # Position sizing, stop-loss, exposure limits
│   └── utils/
│       └── (utilities)
├── main.py                       # Main entry point
├── test_mvp.py                   # Quick validation tests
├── requirements.txt              # Python dependencies
├── .env.example                  # Example environment file
└── README.md                     # You are here
```

---

## 🎓 Understanding the Code

### Key Files to Study:

1. **`strategy/delta_neutral.py`** - Start here
   - Read `run_cycle()` to understand the main loop (line 43)
   - See how positions are opened, held, and rotated
   - Notice the timing logic (90-minute holds)

2. **`exchange/aster_client.py`** - Next
   - How we wrap the Aster SDK
   - Error handling patterns
   - Order placement functions (line 35)

3. **`strategy/risk_manager.py`** - Then this
   - Position sizing calculations (line 45)
   - Risk limit checks (line 99)
   - Exposure management

4. **`database/models.py`** - Finally
   - What data we track
   - How to query trading history

### Common Modifications:

**Change the trading pair:**
```python
# In .env
TRADING_PAIRS=["ETHUSDT"]  # Trade ETH instead of BTC
```

**Adjust hold time:**
```python
# In .env
POSITION_HOLD_TIME_MIN=120  # Hold for 2 hours instead of 90 min
```

**Change position size:**
```python
# In .env
MAX_POSITION_SIZE_PCT=2.0   # Use 2% per position (more aggressive)
```

---

## 🛠️ Customization Guide

### Add a New Strategy

1. Create `strategy/your_strategy.py`
2. Inherit from a base strategy class (or copy delta_neutral structure)
3. Implement `run_cycle()` with your logic
4. Update `main.py` to use your strategy

### Connect to a Different DEX

1. Create `exchange/newdex_client.py`
2. Wrap their SDK/API calls
3. Implement same interface as `aster_client.py`:
   - `place_market_order()`
   - `get_position_risk()`
   - `get_mark_price()`
   - `close_position()`
4. Update config to point to new exchange

### Modify Risk Parameters

Edit `strategy/risk_manager.py`:
```python
def calculate_position_size(self, price: float) -> float:
    # Current formula (line 81):
    max_notional = self.capital * (self.max_position_size_pct / 100) * self.leverage

    # Add your modifications:
    # - Volatility-based sizing
    # - Time-of-day adjustments
    # - Balance-based scaling
```

---

## 📊 Monitoring & Analytics

### View Trading Stats

```python
from aster_operator.database.db import get_db
from aster_operator.database.models import Trade, Position

with get_db() as db:
    # Total volume today
    trades_today = db.query(Trade).filter(
        Trade.timestamp >= datetime.today()
    ).all()

    volume = sum(t.notional for t in trades_today)
    print(f"Today's volume: ${volume:,.2f}")
```

### Export Data for Analysis

```python
import pandas as pd

with get_db() as db:
    trades = db.query(Trade).all()
    df = pd.DataFrame([{
        'timestamp': t.timestamp,
        'symbol': t.symbol,
        'side': t.side,
        'price': t.price,
        'quantity': t.quantity,
        'pnl': t.realized_pnl
    } for t in trades])

    df.to_csv('trading_history.csv')
```

---

## ⚠️ Risk Warnings

**This bot trades with REAL MONEY on leveraged positions. Understand the risks:**

- ✋ **Leverage Risk**: 15x leverage means 6.7% adverse move = liquidation
- ⚡ **Funding Risk**: Long/short imbalance can cause daily costs
- 🔥 **API Risk**: Bugs in code can place unintended orders
- 📉 **Market Risk**: Flash crashes can liquidate before you close
- 🏦 **Exchange Risk**: Exchange could be hacked, go offline, or freeze funds

**Start small. Test on testnet. Understand every line before running live.**

---

## 🤝 Contributing

This is an educational project for Algo Traders Club members. Contributions welcome!

**Ways to contribute:**
- 🐛 Bug fixes
- 📚 Documentation improvements
- 🎨 Code refactoring
- 🧪 Test coverage
- 💡 Strategy improvements

**Before submitting PRs:**
1. Test on testnet
2. Add comments explaining your changes
3. Update documentation if needed

---

## 📜 License

MIT License - Copyright (c) 2025 Algo Traders Club LLC

See [LICENSE](LICENSE) file for details.

---

## 🔗 Resources

- **Algo Traders Club**: [algotradersclub.com](https://algotradersclub.com)
- **Aster DEX**: [asterdex.com](https://asterdex.com)
- **Aster API Docs**: [Aster Finance API](https://github.com/asterdex/api-docs)
- **Community Discord**: [Join here](https://discord.gg/algotradersclub)
- **YouTube Tutorials**: [Our Channel](https://youtube.com/@algotradersclub)

---

## 💬 Questions?

- **General trading questions**: Post in the Algo Traders Club Discord
- **Code issues**: Open a GitHub issue
- **Strategy discussions**: Join our weekly community call
- **Private consultation**: [Book a session](https://algotradersclub.com/coaching)

---

**Built with ❤️ by the Algo Traders Club community**

*"There is no spoon. There are only operators."* 🥄🤖
