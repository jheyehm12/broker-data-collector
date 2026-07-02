# Broker Data Collector

A broker-universal **MetaTrader 5 Expert Advisor** that records broker-specific market data to CSV for research and backtesting.

**This EA does not trade.** It only reads market and account information and writes CSV files.

## Features

- Multi-symbol collection (default: `BTCUSD`, `XAUUSD`, `US100`, `EURUSD`)
- **Multi-timeframe collection** (default: `M1,M5,M15,H1`) — separate CSV per symbol + timeframe
- Timer-driven live collection (default: **60 seconds**)
- One CSV per symbol/timeframe/day: `SYMBOL_TIMEFRAME_YYYYMMDD.csv`
- Broker metadata on every row: company, server, login, account type
- Bid, ask, spread, digits, and point at write time
- Skips duplicate candle timestamps; safe to restart the EA
- **Historical backfill on attach** — optionally seeds up to 5,000 closed bars per symbol
- **Backfill quality summary** — per-symbol stats in Experts journal + daily `summary_YYYYMMDD.csv`
- **Export formats** — `Raw` (default) or `CompetitionLab` for Quant Competition Lab import
- **`manifest.json`** — auto-maintained dataset index for Quant Competition Lab discovery

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
| `InpSymbols` | `BTCUSD,XAUUSD,US100,EURUSD` | Symbols to collect |
| `InpTimeframes` | `M1,M5,M15,H1` | Comma-separated timeframes |
| `InpTimerSeconds` | 60 | Collection interval in seconds |
| `EnableBackfill` | true | Backfill closed bars on attach |
| `BackfillBars` | 5000 | Max closed bars to backfill per symbol |
| `ExportFormat` | Raw | `Raw` or `CompetitionLab` CSV output |

## Troubleshooting

| Issue | What to check |
|-------|----------------|
| No CSV files | Algo Trading enabled; Experts journal for errors; folder permissions |
| Symbol not found | Rename in `InpSymbols` to match broker (e.g. `NAS100` vs `US100`) |
| Duplicate rows after manual edit | EA skips duplicates by timestamp; remove bad rows from CSV or delete file |
| Backfill writes fewer bars than requested | Broker may have less history; check **Experts** journal for actual count |
| Slow startup | Many symbols × timeframes × `BackfillBars` is normal; reduce scope or disable backfill |

## License / use

For personal research and backtesting. Verify compliance with your broker's terms of service before automated data collection.

## Version

See [CHANGELOG.md](CHANGELOG.md) — current release **1.5.0**.
