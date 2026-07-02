# MASTER_PROMPT — Broker Data Collector

## Mission

Build and maintain a **broker-universal MetaTrader 5 Expert Advisor** that collects broker-specific market data for **research and backtesting only**.

The EA must **never place, modify, or close orders**. No trading logic.

## Core behavior

| Setting | Default |
|---------|---------|
| Symbols | `BTCUSD,XAUUSD,US100,EURUSD` (comma-separated input) |
| Timeframes | `M1,M5,M15,H1` (comma-separated input) |
| Timer interval | 60 seconds |
| Backfill on attach | Enabled, 5000 closed bars (configurable) |
| Output folder | `MQL5/Files/BrokerDataCollector/` (Raw) or `.../CompetitionLab/` |
| File naming | `SYMBOL_TIMEFRAME_YYYYMMDD.csv` — **filename** symbol sanitized (`# / \ : space` → `_`); broker symbol unchanged for APIs and CSV data |
| Export format | `Raw` (default) or `CompetitionLab` |

## Data contract (CSV columns)

### Raw

1. `timestamp`
2. `broker_name`
3. `server`
4. `account_login`
5. `account_type_company`
6. `symbol`
7. `timeframe`
8. `open`, `high`, `low`, `close`
9. `tick_volume`
10. `bid`, `ask`
11. `spread_points`, `spread_price`
12. `digits`, `point`

### CompetitionLab

1. `Timestamp`
2. `Open`, `High`, `Low`, `Close`
3. `Volume` (= `tick_volume`)

Completed candles only in both formats.

## Required MQL5 APIs

- Lifecycle: `OnInit`, `OnTimer`, `OnDeinit`
- Market: `SymbolSelect`, `CopyRates`, `SymbolInfoDouble`
- Account: `AccountInfoString`, `AccountInfoInteger`
- Timer: `EventSetTimer` / `EventKillTimer`

## Safety rules

1. **No trading functions** — no `Order*`, `Position*`, `Trade*`, or deal execution.
2. **Idempotent writes** — skip rows when the same candle timestamp was already saved.
3. **Header on new files** — write CSV header only when creating a new daily file.
4. **Resume-safe** — on restart, read existing daily files and continue without duplicating bars.
5. **Closed bars only** — persist `CopyRates(..., shift=1)` (last completed candle).
6. **Historical backfill** — on `OnInit`, optionally write up to `BackfillBars` closed candles per symbol into the correct daily CSV files, then continue timer collection.
7. **Quality summary** — after each symbol backfill, log bars/timestamp/spread stats and append a row to `summary_YYYYMMDD.csv`.
8. **Filename sanitization** — `SanitizeSymbolForFilename()` for CSV/manifest paths only; keep raw broker symbol for `SymbolSelect`, `CopyRates`, and Raw CSV `symbol` column.

## Design principles (v1)

- Keep the EA small, readable, and dependency-free (single `.mq5` file).
- Prefer explicit inputs over magic constants.
- Log actionable errors to the Experts journal.
- Document install path, CSV location, and Quant Competition Lab import in `README.md`.

## Out of scope (current)

- Tick-level capture
- Cloud upload / remote sync
- Multi-terminal coordination
- Strategy signals or alerts
