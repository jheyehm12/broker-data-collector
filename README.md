# Broker Data Collector

A broker-universal **MetaTrader 5 Expert Advisor** that records broker-specific market data to CSV for research and backtesting.

**This EA does not trade.** It only reads market and account information and writes CSV files.

## Features

- Multi-symbol collection (default: `BTCUSD`, `XAUUSD`, `US100`, `EURUSD`)
- **Multi-timeframe collection** (default: `M1,M5,M15,H1`) — separate CSV per symbol + timeframe
- Timer-driven live collection (default: **60 seconds**)
- One CSV per symbol/timeframe/day: `SYMBOL_TIMEFRAME_YYYYMMDD.csv` (symbol segment sanitized for filenames — see below)
- Broker metadata on every row: company, server, login, account type
- Bid, ask, spread, digits, and point at write time
- Skips duplicate candle timestamps; safe to restart the EA
- **Historical backfill on attach** — optionally seeds up to 5,000 closed bars per symbol
- **Backfill quality summary** — per-symbol stats in Experts journal + daily `summary_YYYYMMDD.csv`
- **Export formats** — `Raw` (default) or `CompetitionLab` for Quant Competition Lab import
- **`manifest.json`** — auto-maintained dataset index for Quant Competition Lab discovery
- **MyAlert research export (optional)** — `EnableMyAlertResearchFeatures` (default off); separate `MyAlert_*_Research.csv` per symbol/timeframe
- **Startup symbol validation (v1.55+)** — invalid symbols skipped with similar-name suggestions; EA keeps running

## Finding broker symbol names

Symbol names are **broker-specific**. The EA input must match Market Watch exactly.

1. Open **View → Market Watch** (or press `Ctrl+M`)
2. Right-click → **Symbols** → search your instrument
3. Double-click to add to Market Watch
4. Copy the **exact** symbol text into `InpSymbols`

### Common broker naming differences

| Generic / common name | Broker examples |
|-----------------------|-----------------|
| `BTCUSD` | `BTCUSD#`, `BTCUSD.m`, `Bitcoin` |
| `XAUUSD` / gold | `GOLD#`, `XAUUSD#`, `XAUUSD.` |
| `US100` / Nasdaq | `US100Cash#`, `NAS100`, `USTEC`, `US100-SEP26` |
| `EURUSD` | `EURUSD#`, `EURUSD.m` |

The EA validates every symbol at startup. If a name is wrong, the Experts journal shows:

```
Configured symbol 'US100' not found.
Did you mean:
 - US100Cash#
 - US100-SEP26
```

Invalid symbols are **skipped** — the EA continues collecting the rest.

### Example `InpSymbols` inputs

All of these are equivalent:

```
BTCUSD#,GOLD#,US100Cash#,EURUSD#
```

```
BTCUSD#
GOLD#
US100Cash#
EURUSD#
```

```
BTCUSD#;GOLD#;US100Cash#;EURUSD#
```

```
BTCUSD# GOLD# US100Cash# EURUSD#
```

## CSV schema

### Raw (default)

Saved to `MQL5/Files/BrokerDataCollector/` as `SYMBOL_TIMEFRAME_YYYYMMDD.csv` (example: `EURUSD_M1_20260702.csv`).

| Column | Description |
|--------|-------------|
| `timestamp` | Bar open time (closed candle) |
| `broker_name` | Terminal company name |
| `server` | Account server |
| `account_login` | Account number |
| `account_type_company` | Account company + trade mode (demo/real/contest) |
| `symbol` | Symbol name |
| `timeframe` | e.g. `M1` |
| `open`, `high`, `low`, `close` | OHLC of closed bar |
| `tick_volume` | Tick volume |
| `bid`, `ask` | Current quotes at write time |
| `spread_points` | Spread in points |
| `spread_price` | Ask − bid |
| `digits` | Symbol digits |
| `point` | Symbol point size |

### CompetitionLab

Set `ExportFormat = CompetitionLab` for Quant Competition Lab-ready files.

Saved to `MQL5/Files/BrokerDataCollector/CompetitionLab/` as `SYMBOL_TIMEFRAME_YYYYMMDD.csv` (example: `EURUSD_M1_20260702.csv`).

| Column | Description |
|--------|-------------|
| `Timestamp` | Bar open time (closed candle) |
| `Open`, `High`, `Low`, `Close` | OHLC of closed bar |
| `Volume` | Tick volume (`tick_volume`) |

Only completed candles are exported in both formats.

## MyAlert research export (optional, v1.5.7+)

Set `EnableMyAlertResearchFeatures = true` to enable a **separate** research CSV alongside existing Raw/CompetitionLab exports. Default is **false** — when off, no MyAlert files are created and existing behavior is unchanged.

**Folder:**

```
<MT5 Data Folder>/MQL5/Files/BrokerDataCollector/MyAlert/
```

**Filename pattern:**

```
MyAlert_<SYMBOL>_<TIMEFRAME>_Research.csv
```

Example (broker symbol `BTCUSD#`): `MyAlert_BTCUSD_M1_Research.csv`

**Phase E (current):** all 59 columns populated when sufficient history exists. Phase D requires 20 bars of lookback; Phase E requires 36 bars.

### Timezone conversion

| Column | Source |
|--------|--------|
| `Timestamp` | Closed bar open time from `CopyRates` (`bar.time`), formatted |
| `Broker Timestamp` | Same as `Timestamp` — explicit broker/trade-server time label |
| `UTC Timestamp` | `bar.time - (TimeCurrent() - TimeGMT())` at write time |
| `Hour UTC` | Hour component (0–23) of `UTC Timestamp` |
| `Day of Week` | English name from UTC struct (`Sunday`–`Saturday`) |

**Note:** UTC offset is sampled at write time. Historical DST shifts are not replayed per bar.

### Session mapping (UTC hour, first match wins)

| UTC hour | Session |
|----------|---------|
| 13–16 | London-NY Overlap |
| 08–12 | London |
| 17–21 | New York |
| 22–23 or 00–07 | Asia |
| Other | Off-hours |

### Asset class heuristics

| Class | Detection |
|-------|-----------|
| Crypto | Symbol contains `BTC`, `ETH`, `LTC`, `XRP`, `CRYPTO` |
| Commodity | Symbol contains `XAU`, `GOLD`, `XAG`, `SILVER` |
| Index | Symbol contains `US100`, `NAS`, `USTEC`, `US30`, `US500`, `SPX`, `DAX`, `FTSE`, `JP225`, `NIK` |
| Forex | `SYMBOL_TRADE_CALC_MODE` is forex |
| Other | Fallback |

### Raw candle fields

| Column | Source |
|--------|--------|
| `Open/High/Low/Close` | `MqlRates` OHLC (closed bar) |
| `Tick Volume` | `bar.tick_volume` |
| `Real Volume` | `bar.real_volume` (often `0` on forex CFDs) |
| `Spread` | `SYMBOL_SPREAD` in points at write time (same sampling as Raw CSV) |

### Phase D — candle structure (columns 17–24)

All values use the **closed bar** at `rates[barIdx]` (`CopyRates` shift = 1). `digits` = `SYMBOL_DIGITS`.

| Column | Formula |
|--------|---------|
| `Direction` | `1` if `close > open`, `-1` if `close < open`, `0` if doji |
| `Body Size` | `abs(close - open)` |
| `Range Size` | `high - low` |
| `Upper Wick` | `high - max(close, open)` |
| `Lower Wick` | `min(close, open) - low` |
| `Body-to-Range Ratio` | `Body Size / Range Size` (0 if range = 0) |
| `Upper Wick Ratio` | `Upper Wick / Range Size` |
| `Lower Wick Ratio` | `Lower Wick / Range Size` |

### Phase D — relative features (columns 25–30)

Uses only bars at indices `barIdx` … `barIdx + N - 1` (current closed bar plus older bars; **no future bars**).

| Column | Formula |
|--------|---------|
| `Average Body 5` | SMA of `Body Size` over 5 bars starting at `barIdx` |
| `Average Body 10` | SMA of `Body Size` over 10 bars starting at `barIdx` |
| `Average Body 20` | SMA of `Body Size` over 20 bars starting at `barIdx` |
| `Current Body Ratio` | `Body Size / Average Body 20` |
| `ATR14` | SMA of true range over 14 bars starting at `barIdx` |
| `Range-to-ATR` | `Range Size / ATR14` |

**True range** at bar `j`:

```
TR(j) = max(high(j) - low(j), abs(high(j) - close(j+1)), abs(low(j) - close(j+1)))
```

(`j+1` is the next-older bar in the `CopyRates` series array.)

### Phase D — sequence features (columns 31–44)

| Column | Formula |
|--------|---------|
| `Previous Direction 1` … `5` | Direction sign of bars `barIdx+1` … `barIdx+5` (0 if unavailable) |
| `Previous Body Ratio 1` … `5` | Body-to-range ratio of bars `barIdx+1` … `barIdx+5` |
| `Consecutive Bullish` | Count of consecutive `Direction = 1` bars from `barIdx` backward |
| `Consecutive Bearish` | Count of consecutive `Direction = -1` bars from `barIdx` backward |
| `Body Expansion` | `Body Size / previous Body Size` (0 if previous = 0) |
| `Range Expansion` | `Range Size / previous Range Size` |

**Expansion classification** (derived from ratio, not a separate column):

| Ratio | Classification |
|-------|----------------|
| `> 1` | Expansion |
| `< 1` | Contraction |
| `= 1` | Neutral |

### Phase D — MyAlert-compatible raw inputs (columns 54–59)

| Column | Formula |
|--------|---------|
| `Previous Body` | `Body Size` of bar `barIdx+1` |
| `Average Body` | Same as `Average Body 20` |
| `Previous Body Ratio` | Body-to-range ratio of bar `barIdx+1` |
| `Follow Through` | `1` if current direction equals previous direction **and** current body > previous body; else `0` |
| `Distance Ratio` | `Body Size / ATR14` |
| `Body Strength` | `2` = STRONG, `1` = NEUTRAL (doji), `0` = WEAK |

**Body Strength (STRONG)** matches MyAlert execution candle filter thresholds:

- Bullish: `body >= 0.5 × ATR14`, close within 25% of range from high, upper wick ≤ `0.6 × body`
- Bearish: `body >= 0.5 × ATR14`, close within 25% of range from low, lower wick ≤ `0.6 × body`

### Phase E — market structure (columns 45–53)

Uses only closed bars at indices `barIdx` and older. No future bars.

#### Swing detection (columns 45–46)

| Parameter | Value |
|-----------|-------|
| Pivot length (`left` / `right`) | **5** / **5** (matches MyAlert zone `pivotLen`) |
| Confirmation | Pivot at index `p` is valid at bar `barIdx` when `p - barIdx >= 5` and `high[p]` (or `low[p]`) is the extreme over indices `p-5` … `p+5` |
| `Swing High` | `high` of the **most recent** confirmed swing high; `0` if none |
| `Swing Low` | `low` of the **most recent** confirmed swing low; `0` if none |

#### Structure flags (columns 47–50)

| Column | Formula |
|--------|---------|
| `HH` | `1` if `Swing High > previous Swing High`, else `0` |
| `HL` | `1` if `Swing Low > previous Swing Low`, else `0` |
| `LH` | `1` if `Swing High < previous Swing High`, else `0` |
| `LL` | `1` if `Swing Low < previous Swing Low`, else `0` |

#### Trend Bias (column 51)

| Code | Condition |
|------|-----------|
| `1` (BULLISH) | `highest(high,10) > highest(high,25)` **and** `lowest(low,10) > lowest(low,25)` |
| `-1` (BEARISH) | `lowest(low,10) < lowest(low,25)` **and** `highest(high,10) < highest(high,25)` |
| `0` (NEUTRAL) | Otherwise |

#### Breakout State (column 52)

BOS simulation (`bosPivotLen=3`, close-break) from oldest bar in window to `barIdx`:

| Code | Meaning |
|------|---------|
| `0` | NONE |
| `1` | BULL_CONFIRMED — close crosses above lower-high BOS level |
| `2` | BEAR_CONFIRMED — close crosses below higher-low BOS level |
| `3` | BULL_FAILED — close at or below prior 10-bar high (shifted) |
| `4` | BEAR_FAILED — close at or above prior 10-bar low (shifted) |

#### Retest State (column 53)

Within **6** bars after a BOS break:

| Code | Meaning |
|------|---------|
| `0` | NONE |
| `1` | BULL_PENDING |
| `2` | BULL_DONE — `low <= level` and `close >= level` |
| `3` | BEAR_PENDING |
| `4` | BEAR_DONE — `high >= level` and `close <= level` |

### Insufficient history

| Gate | Condition | Effect |
|------|-----------|--------|
| Phase D | `barIdx + 20 >= barsCount` | Columns 17–59 empty |
| Phase E only | `barIdx + 36 >= barsCount` (Phase D ok) | Columns 45–53 empty |

Backfill copies `BackfillBars + 80` closed bars; only `BackfillBars` rows are written.

### Exact header (59 columns)

```
Timestamp,UTC Timestamp,Broker Timestamp,Symbol,Timeframe,Asset Class,Session,Day of Week,Hour UTC,Open,High,Low,Close,Tick Volume,Real Volume,Spread,Direction,Body Size,Range Size,Upper Wick,Lower Wick,Body-to-Range Ratio,Upper Wick Ratio,Lower Wick Ratio,Average Body 5,Average Body 10,Average Body 20,Current Body Ratio,ATR14,Range-to-ATR,Previous Direction 1,Previous Direction 2,Previous Direction 3,Previous Direction 4,Previous Direction 5,Previous Body Ratio 1,Previous Body Ratio 2,Previous Body Ratio 3,Previous Body Ratio 4,Previous Body Ratio 5,Consecutive Bullish,Consecutive Bearish,Body Expansion,Range Expansion,Swing High,Swing Low,HH,HL,LH,LL,Trend Bias,Breakout State,Retest State,Previous Body,Average Body,Previous Body Ratio,Follow Through,Distance Ratio,Body Strength
```

**Sample row (Phase E complete, EURUSD# M1 — illustrative):**

```
2026.07.13 10:15:00,2026.07.13 02:15:00,2026.07.13 10:15:00,EURUSD#,M1,Forex,London,Monday,2,1.08510,1.08545,1.08500,1.08530,128,0,12,1,0.00020,0.00045,0.00015,0.00010,0.44,0.33,0.22,0.00018,0.00019,0.00020,1.00,0.00032,1.41,1,1,1,0,-1,0.40,0.38,0.35,0.30,0.25,3,0,1.11,1.05,1.08545,1.08470,1,1,0,0,1,0,1,0.00018,0.00020,0.40,1,0.63,2
```

**Sample row (insufficient history — first ~20 bars):**

```
2026.07.13 09:55:00,2026.07.13 01:55:00,2026.07.13 09:55:00,EURUSD#,M1,Forex,Asia,Monday,1,1.08480,1.08495,1.08470,1.08488,95,0,11,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,
```

### Duplicate and alignment validation

| Check | Mechanism |
|-------|-----------|
| Closed candles only | `CopyRates(..., shift=1)` — same as main Raw/CompetitionLab export |
| No future leakage | All lookback reads `barIdx+1` and older; ATR/body averages use current + past bars only |
| Duplicate timestamps | `g_lastMyAlertWrittenBarTime[stream]` skips rows with `barTime <= lastWritten`; resume reads last timestamp from file on init/backfill |
| Alignment with main CSV | `Timestamp` column should match the `timestamp` column in the daily Raw CSV for the same symbol/timeframe/bar (compare after a collection run) |
| Missing candles | If the broker has gaps, both exports skip those bars; MyAlert rows exist only for bars actually written |

**Regression:** when `EnableMyAlertResearchFeatures = false`, no MyAlert folder I/O, no extra `CopyRates`, and Raw/CompetitionLab behavior is unchanged.

### Performance impact (MyAlert research)

| Path | Extra work when flag is on |
|------|----------------------------|
| Timer (per stream, per cycle) | One additional `CopyRates` of **80** closed bars + feature math + one MyAlert file append |
| Backfill (per stream) | `CopyRates` count increased by **80** (lookback-only bars are not written as rows) |
| Memory | `MqlRates[80]` temporary array on timer path |

Typical overhead: low for live collection. Backfill adds ~1.6% more bars copied (`80 / 5000`). Phase E BOS simulation is O(window) per bar (worst case ~80 iterations).

MyAlert files are **not** included in `manifest.json` (existing manifest unchanged).

## MyAlert outcome enrichment (Phase F post-processor)

Phase F is a **separate Python utility** — it does **not** modify `BrokerDataCollector.mq5` or the decision-time research CSV. Future-derived labels are written only to enriched outcome files.

### Inputs

| Input | Description |
|-------|-------------|
| MyAlert research CSV | `MyAlert_<SYMBOL>_<TIMEFRAME>_Research.csv` from the EA |
| Raw OHLC folder | Broker Data Collector `Raw` daily CSVs (`SYMBOL_TIMEFRAME_YYYYMMDD.csv`) |
| Config JSON (optional) | TP/SL model, forward horizon, same-candle policy |

### Outputs

| Output | Location |
|--------|----------|
| Enriched outcomes CSV | `MyAlert/Enriched/MyAlert_<SYMBOL>_<TIMEFRAME>_Outcomes.csv` |

**Join keys:** `Symbol`, `Timeframe`, `Timestamp` (match research CSV exactly).

**Source research CSV is never modified.**

### Run

```bash
python -m myalert_enrich path/to/MyAlert_EURUSD_M1_Research.csv \
  --raw-folder "C:/Users/<you>/AppData/Roaming/MetaQuotes/Terminal/<id>/MQL5/Files/BrokerDataCollector" \
  --config myalert_enrich/default_config.json
```

### Config (`default_config.json`)

| Field | Default | Description |
|-------|---------|-------------|
| `tp_sl_model` | `atr_multiple` | `atr_multiple`, `fixed_pct`, or `fixed_price` |
| `tp_atr_multiple` | `2.0` | TP distance = multiple × `ATR14` |
| `sl_atr_multiple` | `1.0` | SL distance = multiple × `ATR14` |
| `tp_pct` / `sl_pct` | `0.002` / `0.001` | Used when `tp_sl_model=fixed_pct` |
| `tp_price_distance` / `sl_price_distance` | — | Used when `tp_sl_model=fixed_price` |
| `forward_horizon_bars` | `20` | Max forward bars scanned for TP/SL |
| `same_candle_policy` | `both` | `both`, `loss_first`, or `tp_first` |
| `entry_price_field` | `Close` | Decision-time entry price column |
| `direction_field` | `Direction` | `1` long / `-1` short; `0` falls back to `Trend Bias` |

### Outcome CSV schema (21 columns)

```
Symbol,Timeframe,Timestamp,Entry Price,Direction,TP Level,SL Level,Forward Horizon Bars,TP SL Model,First Reaction,MFE,MAE,TP Hit,SL Hit,TP Hit Time,SL Hit Time,Outcome,Bars To Outcome,Final Forward Return,Forward Bars Available,Enrichment Status
```

| Column | Description |
|--------|-------------|
| `First Reaction` | Signed reaction of first forward close vs entry (`1` / `-1` / `0`) in trade direction |
| `MFE` | Maximum favorable excursion (price units) over forward window |
| `MAE` | Maximum adverse excursion (price units) over forward window |
| `TP Hit` / `SL Hit` | `1` if level touched within horizon, else `0` |
| `TP Hit Time` / `SL Hit Time` | Timestamp of first touch (empty if not hit) |
| `Outcome` | `WIN`, `LOSS`, `BOTH`, or `NONE` |
| `Bars To Outcome` | Forward bar index of first decisive event (`0` if `NONE`) |
| `Final Forward Return` | Direction-signed return at last available forward bar in horizon |
| `Enrichment Status` | `MATCHED`, `MISSING_OHLC`, `INSUFFICIENT_FORWARD`, `SKIP_NEUTRAL`, `INVALID_ROW` |

### Decision-time rules

- **Entry** = `Close` of the research row (decision bar close).
- **Direction** = `Direction` column; if `0`, uses `Trend Bias`; neutral rows → `SKIP_NEUTRAL`.
- **Forward path** = Raw OHLC bars strictly **after** the decision timestamp (no same-bar future data).
- **TP/SL scan** = forward bars `1 … forward_horizon_bars` in chronological order.

### Same-candle TP + SL event order

When **both** TP and SL are inside the same bar's range:

| Policy | `Outcome` | Notes |
|--------|-----------|-------|
| `both` (default) | `BOTH` | `TP Hit Time` = `SL Hit Time` = that bar's timestamp |
| `loss_first` | `LOSS` | Conservative intrabar assumption |
| `tp_first` | `WIN` | Optimistic intrabar assumption |

When TP and SL occur on **different** bars, the **earlier** bar determines `WIN` or `LOSS`.

### Sample outcome row

```
EURUSD#,M1,2026.07.13 10:15:00,1.08530,1,1.08594,1.08498,20,atr_multiple,1,0.00045,0.00018,1,0,2026.07.13 10:18:00,,WIN,3,0.00012,20,MATCHED
```

### Validation

| Case | Handling |
|------|----------|
| Row matching | Requires exact `Timestamp` in Raw OHLC for same `Symbol`/`Timeframe` |
| Missing OHLC | `Enrichment Status=MISSING_OHLC`, outcome fields empty/zero |
| End of dataset | `INSUFFICIENT_FORWARD` when fewer than `forward_horizon_bars` exist; MFE/MAE/return use available bars |
| Duplicate timestamps in Raw | Last row wins when building OHLC series |

### Tests

```bash
python -m unittest tests.test_myalert_enrich -v
```

## MyAlert ML readiness validation (Phase G post-processor)

Phase G validates that research + enriched outcome datasets are **ML-ready** without modifying the EA or any source CSV.

### Inputs

| Input | Description |
|-------|-------------|
| MyAlert research CSV | Decision-time features (`MyAlert_*_Research.csv`) |
| Outcomes CSV (recommended) | Phase F output (`MyAlert_*_Outcomes.csv`) |
| Config JSON (optional) | Thresholds: `myalert_validate/default_config.json` |

### Outputs (written to `MyAlert/Validation/` by default)

| File | Description |
|------|-------------|
| `ML_READINESS_REPORT.md` | Human-readable report with verdicts and recommendations |
| `validation_report.json` | Machine-readable check results + readiness score |
| `eligibility_flags.csv` | Per-row training eligibility (source files unchanged) |

### Run

```bash
python -m myalert_validate path/to/MyAlert_EURUSD_M1_Research.csv \
  --outcomes-csv path/to/MyAlert/Enriched/MyAlert_EURUSD_M1_Outcomes.csv \
  --config myalert_validate/default_config.json
```

Exit code `0` = PASS/WARNING, `2` = FAIL.

### Checks performed

| Check | Verdict levels |
|-------|----------------|
| Schema validation (research + outcomes) | PASS / FAIL |
| Required columns | PASS / FAIL |
| Data types (numeric parseable) | PASS / FAIL |
| Duplicate keys (`Symbol+Timeframe+Timestamp`) | PASS / FAIL |
| Timestamp chronological order | PASS / WARNING |
| Missing values | PASS / WARNING / FAIL |
| Infinite/invalid numerics | PASS / FAIL |
| Feature leakage (outcome cols in research) | PASS / FAIL |
| Outcome leakage (join separation) | PASS / WARNING |
| Class balance (`Outcome`) | PASS / WARNING |
| Feature variance (zero-variance cols) | PASS / WARNING |
| Highly correlated features (\|r\| ≥ 0.95) | PASS / WARNING |
| Chronological split readiness | PASS / FAIL |
| Symbol/timeframe consistency | PASS / FAIL |
| Session/timezone consistency | PASS / WARNING |
| Incomplete outcomes (end-of-dataset) | PASS / WARNING |
| Minimum sample size per stream/class | PASS / WARNING / FAIL |

**Overall readiness score:** weighted 0–100. **Overall verdict:** `PASS` (no FAIL), `WARNING` (warnings only), `FAIL` (any blocker).

### Eligibility flags (separate file)

`eligibility_flags.csv` columns:

```
Symbol,Timeframe,Timestamp,Eligible For Training,Eligibility Reasons,Research Row Index,Outcome Matched,Enrichment Status,Outcome
```

- `Eligible For Training = 1` only when keys match, enrichment `MATCHED`, critical features present
- **No imputation** — ineligible rows are flagged, not modified
- Use eligibility file to filter rows before training; never merge outcomes into feature matrix

### ML recommendations (included in reports)

| Topic | Guidance |
|-------|----------|
| **Recommended features** | Derived structure/relative/sequence/market-structure columns (not raw OHLC) |
| **Exclude from training** | Timestamps, Symbol, Timeframe, raw OHLC, spread, all outcome-only columns |
| **Suggested targets** | `Outcome` (classification), `TP Hit` / `Final Forward Return` (binary/regression) |
| **Split method** | Chronological per symbol/timeframe: 70% / 15% / 15% train/val/test — **no random shuffle** |
| **Baselines** | LogisticRegression / RandomForest (classification), Ridge / RandomForest (regression) |

### Tests

```bash
python -m unittest tests.test_myalert_validate tests.test_myalert_enrich -v
```

## Filename symbol sanitization

Broker symbols often include characters that are invalid or awkward in filenames (e.g. `BTCUSD#`, `GOLD#`). The EA keeps the **original symbol** for all market data APIs (`SymbolSelect`, `CopyRates`, `SymbolInfo*`) and for the `symbol` column in Raw CSV rows.

**Filenames only** use a sanitized symbol:

| Character | Replaced with |
|-----------|----------------|
| `#` | `_` |
| `/` | `_` |
| `\` | `_` |
| `:` | `_` |
| space | `_` |

Examples:

| Broker symbol | Filename prefix |
|---------------|-----------------|
| `BTCUSD#` | `BTCUSD_` |
| `GOLD#` | `GOLD_` |
| `US100Cash#` | `US100Cash_` |

File example: broker symbol `BTCUSD#` on M1 → `BTCUSD_M1_20260702.csv`.

The manifest top-level `symbols` array lists configured **broker** symbols. Each `files[]` entry uses the **sanitized** symbol/filename as on disk.

## Dataset manifest (`manifest.json`)

The EA maintains a machine-readable manifest at:

```
<MT5 Data Folder>/MQL5/Files/BrokerDataCollector/manifest.json
```

Updated after backfill, timer writes, attach, and detach. Quant Competition Lab can read this file to auto-discover datasets.

**Top-level fields:**

| Field | Description |
|-------|-------------|
| `generated_at` | Last manifest update time |
| `broker` | Terminal company name |
| `server` | Account server |
| `account_login` | Account number |
| `account_company` | Account company |
| `export_format` | `Raw` or `CompetitionLab` |
| `symbols` | Configured symbol list |
| `timeframes` | Configured timeframe list |
| `files` | Array of exported CSV file entries |

**Each `files[]` entry:**

| Field | Description |
|-------|-------------|
| `symbol` | Symbol name |
| `timeframe` | e.g. `M1` |
| `date` | Calendar date (`YYYY-MM-DD`) |
| `filename` | CSV filename |
| `folder` | Relative folder under `MQL5/Files/` |
| `rows_written` | Data rows in file (excludes header) |
| `first_timestamp` | Earliest bar timestamp in file |
| `last_timestamp` | Latest bar timestamp in file |

Example loader:

```python
import json
from pathlib import Path

manifest = json.loads(Path("manifest.json").read_text(encoding="utf-8"))
for entry in manifest["files"]:
    csv_path = Path(entry["folder"]) / entry["filename"]
    print(entry["symbol"], entry["timeframe"], csv_path, entry["rows_written"])
```

## Backfill quality summary

After each symbol backfill, the EA prints a quality summary to the **Experts** journal:

```
BrokerDataCollector: quality summary EURUSD M1 | bars=5000 | first=2026.06.29 10:15:00 | last=2026.07.02 19:21:00 | avg_spread=12.50 | min_spread=8 | max_spread=24
```

It also appends one row per symbol/timeframe to a daily summary file:

```
<MT5 Data Folder>/MQL5/Files/BrokerDataCollector/summary_YYYYMMDD.csv
```

| Column | Description |
|--------|-------------|
| `date` | Summary date (EA run date) |
| `broker` | Terminal company name |
| `server` | Account server |
| `symbol` | Symbol name |
| `timeframe` | e.g. `M1` |
| `bars_written` | New bars written during this backfill |
| `avg_spread` | Average spread points across written bars |
| `min_spread` | Minimum spread points |
| `max_spread` | Maximum spread points |

Spread stats reflect the live quote spread at each write time (same as bar CSV rows).

## Install the EA

1. Copy `BrokerDataCollector.mq5` into your MT5 data folder:
   ```
   <MT5 Data Folder>/MQL5/Experts/BrokerDataCollector.mq5
   ```
   Typical Windows path:
   ```
   %APPDATA%\MetaQuotes\Terminal\<HASH>\MQL5\Experts\
   ```

2. Open **MetaEditor** (F4 from MT5) or use the Navigator panel.

3. Compile the EA (**Compile** button or F7). Fix any errors shown in the Toolbox.

4. Refresh **Navigator → Expert Advisors** in the MT5 terminal if needed.

## Attach to a chart

1. Open any chart in MT5 (symbol on the chart does not limit collection; inputs control symbols).

2. Drag **BrokerDataCollector** from Navigator onto the chart.

3. On the **Inputs** tab, adjust if needed:
   - `InpSymbols` — comma-separated list (must match your broker's symbol names)
   - `InpTimeframes` — default `M1,M5,M15,H1` (comma-separated: M1, M5, M15, M30, H1, H4, D1, W1, MN1)
   - `InpTimerSeconds` — default 60
   - `EnableBackfill` — default **true**; seeds historical closed bars on attach
   - `BackfillBars` — default **5000**; number of closed bars to request per symbol
   - `ExportFormat` — default **Raw**; set to **CompetitionLab** for QCL-ready OHLCV files
   - `EnableMyAlertResearchFeatures` — default **false**; enables separate MyAlert research CSV

4. Enable **Algo Trading** (toolbar button must be green).

5. Check the **Experts** journal for startup messages, backfill counts, and any symbol errors.

On attach, the EA runs a one-time backfill (if enabled), then continues on the timer. It does not require fast ticks. Leave the terminal running while you want live data collected.

## Where CSV files are saved

**Raw format** (default):

```
<MT5 Data Folder>/MQL5/Files/BrokerDataCollector/
```

Example: `EURUSD_M1_20260702.csv`, `EURUSD_H1_20260702.csv`

**CompetitionLab format**:

```
<MT5 Data Folder>/MQL5/Files/BrokerDataCollector/CompetitionLab/
```

Example: `EURUSD_M5_20260702.csv`

Find your data folder in MT5: **File → Open Data Folder**.

A new file is created per symbol/timeframe each calendar day (based on each bar's timestamp). If a file already exists, new rows are appended (no duplicate timestamps per symbol/timeframe). Backfill writes older bars into the correct daily files automatically.

## Import CSV into Quant Competition Lab

### Option A — CompetitionLab export (recommended)

1. Set `ExportFormat = CompetitionLab` in EA inputs.
2. Attach the EA and let backfill/timer collection run.
3. Copy `manifest.json` and CSV files from `MQL5/Files/BrokerDataCollector/CompetitionLab/`.
4. Point Quant Competition Lab at `manifest.json` for auto-discovery, or load CSVs directly.
5. Columns match QCL: `Timestamp`, `Open`, `High`, `Low`, `Close`, `Volume`.

```python
import pandas as pd

df = pd.read_csv("EURUSD_M1_20260702.csv", parse_dates=["Timestamp"])
df = df.sort_values("Timestamp").drop_duplicates(subset=["Timestamp"], keep="last")
```

### Option B — Raw export with manual mapping

1. **Locate CSV files** — copy from `MQL5/Files/BrokerDataCollector/` to your project or QCL data directory.

2. **Load in Python (pandas)** — typical pattern:
   ```python
   import pandas as pd

   df = pd.read_csv("EURUSD_M1_20260702.csv", parse_dates=["timestamp"])
   df = df.sort_values("timestamp").drop_duplicates(subset=["timestamp"], keep="last")
   ```

3. **Map columns in QCL** — align fields to your lab's expected schema:
   - Time column → `timestamp` → `Timestamp`
   - Price columns → `open`, `high`, `low`, `close` → `Open`, `High`, `Low`, `Close`
   - Volume → `tick_volume` → `Volume`
   - Broker context → `broker_name`, `server`, `spread_points`, `spread_price`

4. **Compare brokers** — because each row includes broker and server metadata, you can concatenate CSVs from different MT5 installations and tag by `broker_name` + `server` + `account_login`.

5. **Validate** — confirm symbol names, timezone of timestamps, and that only closed bars are present (one row per candle time per file).

> Adjust import code to match your Quant Competition Lab project's exact loader API if it provides a dedicated CSV ingest module.

## Inputs reference

| Input | Default | Description |
|-------|---------|-------------|
| `InpSymbols` | `BTCUSD,XAUUSD,US100,EURUSD` | Symbols to collect (comma, semicolon, space, or newline separated — use exact broker names) |
| `InpTimeframes` | `M1,M5,M15,H1` | Comma-separated timeframes |
| `InpTimerSeconds` | 60 | Collection interval in seconds |
| `EnableBackfill` | true | Backfill closed bars on attach |
| `BackfillBars` | 5000 | Max closed bars to backfill per symbol |
| `ExportFormat` | Raw | `Raw` or `CompetitionLab` CSV output |
| `EnableMyAlertResearchFeatures` | false | Separate MyAlert research CSV (Phase E: full 59-column schema) |

## Troubleshooting

| Issue | What to check |
|-------|----------------|
| No CSV files | Algo Trading enabled; Experts journal for errors; folder permissions |
| Invalid symbol at startup | Check startup summary — skipped symbols listed with `✗`. Use exact Market Watch names |
| Only one symbol produces files | Experts log: `Processing symbol=<…>`, `SymbolSelect failed`, or `symbol does not exist on this broker`. Each symbol must match broker Market Watch names exactly (e.g. `BTCUSD#` not `BTCUSD`) |
| Symbol not found | Read "Did you mean:" suggestions in Experts journal; rename in `InpSymbols` (e.g. `NAS100` vs `US100`, `GOLD#` vs `XAUUSD`) |
| EA won't start | All configured symbols invalid — fix at least one name in `InpSymbols` |
| Duplicate rows after manual edit | EA skips duplicates by timestamp; remove bad rows from CSV or delete file |
| Backfill writes fewer bars than requested | Broker may have less history; check **Experts** journal for actual count |
| FileOpen error 5004 during backfill | Fixed in v1.54+ (batched per-day file writes). Recompile and re-attach |
| Slow startup | Many symbols × timeframes × `BackfillBars` is normal; reduce scope or disable backfill |

### Startup summary (v1.55+)

On attach, the Experts journal prints:

```
=========================================
Broker Data Collector Startup
=========================================

Configured Symbols:
✓ BTCUSD#
✓ GOLD#
✓ US100Cash#
✓ EURUSD#

Skipped Symbols:
(none)

Timeframes:
M15
H1

Backfill:
1000 bars

Export:
CompetitionLab

Streams:
8

=========================================
```

## License / use

For personal research and backtesting. Verify compliance with your broker's terms of service before automated data collection.

## Version

See [CHANGELOG.md](CHANGELOG.md) — current release **1.8.0** (EA **1.60** + Phase F/G tools).
