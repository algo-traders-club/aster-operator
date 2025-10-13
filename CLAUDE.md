# CLAUDE.md - AI Pair Programming Guide

This document helps AI assistants (like Claude, ChatGPT, or GitHub Copilot) understand this codebase and assist users effectively.

---

## Project Overview

**Name**: Aster Operator
**Purpose**: Educational trading bot for Algo Traders Club
**Strategy**: Delta-neutral hold-and-rotate on Aster DEX
**Target Audience**: Developers learning algorithmic trading
**Language**: Python 3.9+

---

## Code Structure Philosophy

This codebase follows these principles:

1. **Explicit over Clever**: Readability > brevity
2. **Educational Comments**: Explain WHY, not just WHAT
3. **Single Responsibility**: Each file/class does ONE thing well
4. **Type Hints Everywhere**: Makes AI assistance more accurate
5. **Defensive Programming**: Validate inputs, handle errors gracefully

---

## Key Design Decisions

### Why SQLite?
- Simplicity for educational purposes
- No server setup required
- Easy to inspect with DB Browser
- Production apps should use PostgreSQL

### Why NOT async/await?
- Synchronous code is easier to understand for beginners
- Exchange APIs rate-limit anyway (no concurrency benefit)
- Production versions can add async later

### Why Hedge Mode (LONG + SHORT)?
- Teaching delta-neutral strategies
- Members see how hedging works
- Easy to modify to one-way mode

### Why Manual Rotation vs Automation?
- Teaching position lifecycle management
- Members see the decision-making process
- Easy to add full automation later

---

## How to Help Users

When a user asks you to modify this code:

### 1. Always Explain Tradeoffs

```python
# ❌ BAD: Just give code
def new_feature():
    return complicated_code()

# ✅ GOOD: Explain the tradeoff
def new_feature():
    """
    This adds [feature] with the following tradeoffs:

    Pros:
    - [Benefit 1]
    - [Benefit 2]

    Cons:
    - [Downside 1]
    - [Downside 2]

    Alternative approaches:
    - [Option A]: Simpler but less accurate
    - [Option B]: More complex but more robust
    """
    return implementation()
```

### 2. Preserve Educational Comments

When refactoring, KEEP or IMPROVE educational comments. Never delete them without replacing with better explanations.

### 3. Suggest Testing Strategies

After code changes, suggest:
- How to test on paper (theory)
- How to test on testnet (safe practice)
- What to watch for on mainnet (risk awareness)

### 4. Reference Trading Concepts

If suggesting changes involving:
- **Leverage**: Remind about liquidation risk
- **Position sizing**: Explain Kelly Criterion or fixed fractional
- **Stop losses**: Mention difference between hard stops and mental stops
- **Funding rates**: Explain how they work on perps

### 5. Maintain Type Safety

All function signatures should have type hints:

```python
def place_order(
    self,
    symbol: str,
    side: OrderSide,  # Use enums
    quantity: float,
    price: Optional[float] = None
) -> Dict[str, Any]:
```

---

## Common User Requests & How to Handle

### "Make it faster"
1. Profile first (don't optimize blindly)
2. Suggest specific bottlenecks
3. Explain speed vs safety tradeoff
4. Keep educational value

### "Add machine learning"
1. Ask what problem ML solves here
2. Suggest starting with simple rules first
3. If they insist, recommend starting with scikit-learn
4. Warn about overfitting in trading

### "Connect to [OtherExchange]"
1. Point to `exchange/aster_client.py` as template
2. Help them find the other exchange's SDK
3. Suggest wrapping SDK in similar interface
4. Test authentication first

### "My bot lost money"
1. Ask for logs and trade history
2. Check risk manager limits
3. Look at funding rate costs
4. Explain risk of delta slippage
5. Suggest reducing leverage/position size

### "How do I backtest this?"
1. Point to `database/models.py` - historical data
2. Suggest separating strategy logic from execution
3. Recommend `backtesting.py` library
4. Warn about overfitting to history

---

## Code Modification Patterns

### Adding a New Strategy

```python
# 1. Create new file: strategy/momentum.py
# 2. Copy structure from delta_neutral.py
# 3. Modify run_cycle() logic
# 4. Keep risk_manager checks
# 5. Update main.py to import new strategy
```

### Adding New Risk Check

```python
# In risk_manager.py
def should_close_position(self, position: Dict) -> bool:
    # Existing checks...

    # Add new check with clear comment:
    # Check for extreme volatility (VIX-like indicator)
    # If 5-min price swing > 2%, consider closing
    if self._check_volatility_spike(position):
        logger.warning("Volatility spike detected")
        return True

    return False
```

### Adding Logging

```python
# Use loguru's structured logging
logger.info(
    f"Order placed: {symbol} {side} {quantity}",
    extra={
        "symbol": symbol,
        "side": side,
        "quantity": quantity,
        "price": price,
        "notional": quantity * price
    }
)
```

---

## Error Messages to Prioritize

When debugging, focus on:

1. **Authentication errors** → Check API keys in .env
2. **Insufficient balance** → Check wallet funding
3. **Position already exists** → Check hedge mode settings
4. **Rate limit exceeded** → Add delays between calls
5. **Invalid parameter** → Check Aster's API docs for param format

---

## Testing Recommendations

### Unit Tests (Not Included Yet)

Suggest users add:

```python
# tests/test_risk_manager.py
def test_position_sizing():
    rm = RiskManager()
    size = rm.calculate_position_size(price=50000)
    assert size > 0
    assert size <= rm.capital / 50000
```

### Integration Tests

Suggest testing on testnet:

```python
# Test full cycle with testnet credentials
def test_full_cycle_testnet():
    # Set testnet API keys
    # Run one strategy cycle
    # Verify orders placed
    # Verify positions opened
    # Verify cleanup happened
```

---

## Production Readiness Checklist

If user wants to run this live, ensure:

- [ ] Tested extensively on testnet
- [ ] API keys secured (not in git history)
- [ ] Risk limits set conservatively
- [ ] Monitoring/alerts set up
- [ ] Backup plan if bot fails
- [ ] Capital is money they can afford to lose

---

## Key File References

### Configuration
- `aster_operator/config/settings.py` - All bot settings with extensive comments

### Strategy Logic
- `aster_operator/strategy/delta_neutral.py:43` - Main strategy loop (`run_cycle()`)
- `aster_operator/strategy/delta_neutral.py:107` - Position opening logic
- `aster_operator/strategy/delta_neutral.py:180` - Position rotation logic

### Risk Management
- `aster_operator/strategy/risk_manager.py:45` - Position sizing calculation
- `aster_operator/strategy/risk_manager.py:99` - Risk limit checks
- `aster_operator/strategy/risk_manager.py:228` - Exposure management

### Exchange Integration
- `aster_operator/exchange/aster_client.py:80` - Account balance
- `aster_operator/exchange/aster_client.py:35` - Market order placement
- `aster_operator/exchange/aster_client.py:110` - Position closing

### Database
- `aster_operator/database/models.py:7` - Trade model (what trades we log)
- `aster_operator/database/models.py:27` - Position model (position lifecycle)
- `aster_operator/database/models.py:47` - Daily stats model

---

## Philosophy: Learning > Profit

**Remember**: This bot is for LEARNING, not for guaranteed profits.

When helping users:
- Prioritize understanding over optimization
- Explain concepts, don't just give fish
- Encourage experimentation on testnet
- Warn about real risks honestly

**This is educational software. Trading involves risk of loss.**

---

## Common Pitfalls to Warn About

### 1. Over-leveraging
```python
# User wants to increase leverage to 50x
# ⚠️ WARN: At 50x, 2% move = liquidation
# Suggest: Stay under 20x, especially for beginners
```

### 2. Ignoring Funding Rates
```python
# User asks why they're losing money despite delta-neutral
# CHECK: funding_rate might be extreme (>5%)
# EXPLAIN: You pay funding 3x per day, adds up over time
```

### 3. Not Testing on Testnet
```python
# User jumps straight to mainnet with $10K
# ⚠️ STOP: Test with $100 first
# THEN: Scale up gradually
```

### 4. Modifying Risk Limits Without Understanding
```python
# User sets stop_loss_pct = 10% (way too loose)
# EXPLAIN: 10% loss on leveraged position = significant capital loss
# SUGGEST: Keep at 1-2% max
```

---

## Example Conversations

### Good AI Response Example

**User**: "Can you make the bot trade faster to generate more volume?"

**AI**:
```
I can help you increase trading frequency, but let's discuss tradeoffs first:

**Current**: Bot cycles every 10 minutes, holds positions 90+ minutes
**Proposed**: Faster cycles (e.g., every 5 minutes)

Tradeoffs:
✅ Pros: More volume = more reward points
❌ Cons:
  - More trading fees (adds up quickly)
  - Less time to meet 90-min hold requirement for 10x multiplier
  - Higher chance of hitting rate limits
  - More slippage on frequent trades

Recommendation:
Instead of faster cycles, consider:
1. Increase position size (more volume per trade)
2. Trade multiple pairs simultaneously (BTCUSDT + ETHUSDT)
3. Keep 90-min holds to maximize point multiplier

Would you like me to implement any of these alternatives?
```

### Bad AI Response Example

**User**: "Can you make the bot trade faster?"

**AI**:
```python
# ❌ Don't do this - no explanation
cycle_interval_seconds = 60  # Changed from 600 to 60
```

---

## When to Refuse Changes

Politely refuse requests that would:

1. **Remove risk checks** without replacement
   - "I can't remove stop-loss checks, but I can help adjust the thresholds"

2. **Add complexity without clear benefit**
   - "Before adding neural networks, let's ensure the basic strategy works"

3. **Bypass exchange safety features**
   - "Disabling position mode checks could lead to unintended order types"

4. **Hard-code credentials**
   - "API keys must stay in .env file for security"

---

## Useful Commands for Debugging

Share these with users experiencing issues:

```bash
# Check database contents
sqlite3 aster-operator.db "SELECT * FROM trades ORDER BY timestamp DESC LIMIT 10;"

# View recent logs
tail -f logs/aster-operator_*.log

# Test API connection
python test_mvp.py

# Check current positions via Python
python -c "from aster_operator.exchange.aster_client import AsterExchangeClient; c = AsterExchangeClient(); print(c.get_position_risk())"
```

---

## Version Control Best Practices

Remind users about:

```bash
# NEVER commit .env file
git add .env.example  # ✅ Good
git add .env          # ❌ Bad - contains secrets!

# Check what's staged before committing
git status
git diff --staged

# Create feature branches
git checkout -b feature/add-new-strategy
```

---

*For questions about this codebase, ask in Algo Traders Club Discord or tag `@algotradersclub` on Twitter.*
