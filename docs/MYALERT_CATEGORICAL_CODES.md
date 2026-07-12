# MyAlert Research CSV — Categorical Codes

Authoritative mappings for numeric categorical columns emitted by `BrokerDataCollector.mq5` (v1.61+).  
Readable label columns (appended after `Record ID`) mirror these codes and are optional for ML — keep numeric columns as the source of truth.

## Direction (column 17)

| Code | Label | Rule |
|------|-------|------|
| `1` | Bullish | `close > open` |
| `-1` | Bearish | `close < open` |
| `0` | Doji | `close == open` |

## Body Expansion / Range Expansion (columns 43–44)

Stored as **numeric ratios** (`current / previous`). Classification is derived, not a separate code column:

| Condition | Label |
|-----------|-------|
| Ratio `> 1` | Expansion |
| Ratio `< 1` | Contraction |
| Ratio `= 1` | Neutral |

`0` is written when the previous body/range is `0` (undefined ratio).

## Trend Bias (column 51)

| Code | Label | Condition |
|------|-------|-----------|
| `1` | BULLISH | `highest(high,10) > highest(high,25)` **and** `lowest(low,10) > lowest(low,25)` |
| `-1` | BEARISH | `lowest(low,10) < lowest(low,25)` **and** `highest(high,10) < highest(high,25)` |
| `0` | NEUTRAL | Otherwise |

## Breakout State (column 52)

BOS simulation (`bosPivotLen=3`, close-break). Latest state at the closed bar:

| Code | Label | Meaning |
|------|-------|---------|
| `0` | NONE | No active breakout state |
| `1` | BULL_CONFIRMED | Close crosses above lower-high BOS level |
| `2` | BEAR_CONFIRMED | Close crosses below higher-low BOS level |
| `3` | BULL_FAILED | Close at or below prior 10-bar high (shifted) |
| `4` | BEAR_FAILED | Close at or above prior 10-bar low (shifted) |

## Retest State (column 53)

Within **6** bars after a BOS break:

| Code | Label | Meaning |
|------|-------|---------|
| `0` | NONE | No retest activity |
| `1` | BULL_PENDING | Bull BOS level not yet retested |
| `2` | BULL_DONE | `low <= level` and `close >= level` |
| `3` | BEAR_PENDING | Bear BOS level not yet retested |
| `4` | BEAR_DONE | `high >= level` and `close <= level` |

## Follow Through (column 57)

| Code | Label | Rule |
|------|-------|------|
| `1` | Yes | Current direction equals previous **and** current body > previous body |
| `0` | No | Otherwise |

## Body Strength (column 59)

| Code | Label | Rule |
|------|-------|------|
| `2` | STRONG | Bull/bear body ≥ `0.5 × ATR14`, close near extreme (≤25% of range), opposing wick ≤ `0.6 × body` |
| `1` | NEUTRAL | Doji (`close == open`) |
| `0` | WEAK | Directional bar that fails STRONG thresholds |

## HH / HL / LH / LL (columns 47–50)

Binary flags (`0` or `1`) comparing the most recent confirmed swing to the prior swing of the same type:

| Column | Code `1` when | Code `0` when |
|--------|---------------|-----------------|
| `HH` | Swing High > previous Swing High | No higher high or no prior swing |
| `HL` | Swing Low > previous Swing Low | No higher low or no prior swing |
| `LH` | Swing High < previous Swing High | No lower high or no prior swing |
| `LL` | Swing Low < previous Swing Low | No lower low or no prior swing |

Only one of `HH`/`LH` (or `HL`/`LL`) may be `1` when both swings exist; both may be `0` when equal or unavailable.

## Appended label columns (60–68)

| Column | Maps from | Allowed values |
|--------|-----------|----------------|
| `Direction Label` | Direction | Bullish, Bearish, Doji |
| `Body Expansion Label` | Body Expansion ratio | Expansion, Contraction, Neutral |
| `Range Expansion Label` | Range Expansion ratio | Expansion, Contraction, Neutral |
| `Trend Bias Label` | Trend Bias | BULLISH, BEARISH, NEUTRAL |
| `Breakout State Label` | Breakout State | NONE, BULL_CONFIRMED, BEAR_CONFIRMED, BULL_FAILED, BEAR_FAILED |
| `Retest State Label` | Retest State | NONE, BULL_PENDING, BULL_DONE, BEAR_PENDING, BEAR_DONE |
| `Follow Through Label` | Follow Through | Yes, No |
| `Body Strength Label` | Body Strength | STRONG, NEUTRAL, WEAK |

Labels may be empty when Phase D columns are empty (insufficient history). `Record ID` is always populated from the aligned broker candle open.

## Record ID (column 60)

Format: `SYMBOL_TIMEFRAME_YYYYMMDDHHMMSS`

- `SYMBOL` — broker symbol sanitized (`# / \ : space` → `_`, trailing `_` stripped)
- `TIMEFRAME` — e.g. `M1`, `H1`
- `YYYYMMDDHHMMSS` — **aligned** closed-candle broker open time (same instant as `Timestamp`)

Example: `BTCUSD_M1_20260710194200`
