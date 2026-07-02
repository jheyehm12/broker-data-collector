# Broker Data Collector

A broker-universal **MetaTrader 5 Expert Advisor** that records broker-specific market data to CSV for research and backtesting.

**This EA does not trade.** It only reads market and account information and writes CSV files.

## Features

- Multi-symbol collection (default: `BTCUSD`, `XAUUSD`, `US100`, `EURUSD`)
- Configurable timeframe (default: **M1**) and timer (default: **60 seconds**)
- One CSV per symbol per day under `MQL5/Files/BrokerDataCollector/`
- Broker metadata on every row: company, server, login, account type
- Bid, ask, spread, digits, and point at write time
- Skips duplicate candle timestamps; safe to restart the EA

## CSV schema

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

**File naming:** `SYMBOL_YYYYMMDD.csv` (example: `EURUSD_20260702.csv`)

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
   - `InpTimeframe` — default M1
   - `InpTimerSeconds` — default 60

4. Enable **Algo Trading** (toolbar button must be green).

5. Check the **Experts** journal for startup messages and any symbol errors.

The EA runs on a timer and does not require fast ticks. Leave the terminal running while you want data collected.

## Where CSV files are saved

Files are written to:

```
<MT5 Data Folder>/MQL5/Files/BrokerDataCollector/
```

Example:

```
C:\Users\<You>\AppData\Roaming\MetaQuotes\Terminal\<HASH>\MQL5\Files\BrokerDataCollector\EURUSD_20260702.csv
```

Find your data folder in MT5: **File → Open Data Folder**.

A new file is created per symbol each calendar day. If a file already exists, new rows are appended (no duplicate timestamps).

## Import CSV into Quant Competition Lab

Use this workflow when loading broker captures into **Quant Competition Lab** for research or competition prep.

1. **Locate CSV files** — copy from `MQL5/Files/BrokerDataCollector/` to your project or QCL data directory.

2. **Load in Python (pandas)** — typical pattern:
   ```python
   import pandas as pd

   df = pd.read_csv("EURUSD_20260702.csv", parse_dates=["timestamp"])
   df = df.sort_values("timestamp").drop_duplicates(subset=["timestamp"], keep="last")
   ```

3. **Map columns in QCL** — align fields to your lab's expected schema:
   - Time column → `timestamp`
   - Price columns → `open`, `high`, `low`, `close`
   - Volume → `tick_volume`
   - Broker context → `broker_name`, `server`, `spread_points`, `spread_price`

4. **Compare brokers** — because each row includes broker and server metadata, you can concatenate CSVs from different MT5 installations and tag by `broker_name` + `server` + `account_login`.

5. **Validate** — confirm symbol names, timezone of `timestamp`, and that only closed bars are present (one row per candle time per file).

> Adjust import code to match your Quant Competition Lab project's exact loader API if it provides a dedicated CSV ingest module.

## Inputs reference

| Input | Default | Description |
|-------|---------|-------------|
| `InpSymbols` | `BTCUSD,XAUUSD,US100,EURUSD` | Symbols to collect |
| `InpTimeframe` | M1 | Bar period |
| `InpTimerSeconds` | 60 | Collection interval in seconds |

## Troubleshooting

| Issue | What to check |
|-------|----------------|
| No CSV files | Algo Trading enabled; Experts journal for errors; folder permissions |
| Symbol not found | Rename in `InpSymbols` to match broker (e.g. `NAS100` vs `US100`) |
| Duplicate rows after manual edit | EA skips duplicates by timestamp; remove bad rows from CSV or delete file |
| Missing historical bars | v1 collects forward from attach time only |

## License / use

For personal research and backtesting. Verify compliance with your broker's terms of service before automated data collection.

## Version

See [CHANGELOG.md](CHANGELOG.md) — current release **1.0.0**.
