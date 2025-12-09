# Changelog

## [Unreleased] - 2025-12-09

### Added
- Created missing Aster SDK utilities module (`aster_operator/exchange/aster/lib/`)
  - Added `utils.py` with core utility functions:
    - `get_timestamp()` - Get current timestamp in milliseconds
    - `cleanNoneValue()` - Remove None values from dictionaries
    - `encoded_string()` - Encode query parameters for API requests
    - `check_required_parameter()` - Validate single required parameters
    - `check_required_parameters()` - Validate multiple required parameters

### Fixed
- **Position Sizing for Small Capital**: Adjusted position size calculation to work with smaller capital amounts (~$38)
  - Increased default MAX_POSITION_SIZE_PCT from 1.5% to 10% for smaller accounts
  - Fixed decimal precision to match Aster DEX requirements (3 decimals for BTC)
  - Updated both `risk_manager.py` and `delta_neutral.py` rounding logic

- **Dependency Management**: Fixed `pyproject.toml` structure
  - Moved dependencies from `tool.hatch.build.targets.wheel` to `project.dependencies`
  - Ensures `uv sync` properly installs all required packages
  - Added missing packages: `pydantic-settings`, `loguru`, `sqlalchemy`, etc.

### Changed
- Updated `aster_operator/strategy/risk_manager.py`:
  - Changed position size rounding from 4 decimals to 3 decimals (line 90)
  - Comment: "Aster requires 3 decimals for BTC"

- Updated `aster_operator/strategy/delta_neutral.py`:
  - Changed randomization rounding from 3 decimals to 3 decimals with updated comment (line 428)
  - Comment: "Aster requires 3 decimals max for BTC"

### Technical Details

**Issue**: Bot was calculating position size as 0.0 BTC due to:
1. Small capital ($38) × 1.5% × 15x = $8.55 notional
2. At BTC price ~$93,000: $8.55 / $93,000 = 0.000092 BTC
3. Rounding to 3 decimals = 0.000 BTC → rejected by exchange

**Solution**:
1. Increased position size percentage to 10% for small accounts
2. New calculation: $38 × 10% × 15x = $57 notional
3. At BTC price ~$93,000: $57 / $93,000 = 0.0006 BTC
4. After randomization and rounding = 0.001 BTC ✅

**First Successful Trade**:
- LONG order: 0.001 BTC @ $93,083.60
- Notional: ~$93.09 with 15x leverage
- Order ID: 11651264965
- Timestamp: 2025-12-09 17:56:35 UTC

### Configuration

**Recommended Settings for Small Capital ($30-50)**:
```env
CAPITAL_USDT=38.0
LEVERAGE=15
MAX_POSITION_SIZE_PCT=10.0
```

**Recommended Settings for Standard Capital ($100+)**:
```env
CAPITAL_USDT=100.0
LEVERAGE=15
MAX_POSITION_SIZE_PCT=1.5
```

### Testing

All tests passing:
- ✅ API connection test
- ✅ Database initialization
- ✅ Risk manager calculations
- ✅ Live order placement (LONG filled successfully)

### Notes

- Bot is now operational and running delta-neutral strategy
- Will hold positions for 90+ minutes to qualify for 10x Aster RH point multiplier
- Automatic rotation every cycle to generate volume while maintaining delta neutrality

