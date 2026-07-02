# MASTER_PROMPT — Broker Data Collector

## Mission

Build and maintain a **broker-universal MetaTrader 5 Expert Advisor** that collects broker-specific market data for **research and backtesting only**.

The EA must **never place, modify, or close orders**. No trading logic.

## Core behavior

| Setting | Default |
|---------|---------|
| Symbols | `BTCUSD,XAUUSD,US100,EURUSD` (comma-separated input) |
| Timeframe | M1 |
| Timer interval | 60 seconds |
| Output folder | `MQL5/Files/BrokerDataCollector/` |
| File naming | One CSV per symbol per day: `SYMBOL_YYYYMMDD.csv` |

## Data contract (CSV columns)

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

## Required MQL5 APIs

- Lifecycle: `OnInit`, `OnTimer`, `OnDeinit`
- Market: `SymbolSelect`, `CopyRates`, `SymbolInfoDouble`
- Account: `AccountInfoString`, `AccountInfoInteger`
- Timer: `EventSetTimer` / `EventKillTimer`

## Safety rules

1. **No trading functions** — no `Order*`, `Position*`, `Trade*`, or deal execution.
2. **Idempotent writes** — skip rows when the same candle timestamp was already saved.
3. **Header on new files** — write CSV header only when creating a new daily file.
4. **Resume-safe** — on restart, read today's file and continue without duplicating bars.
5. **Closed bars only** — persist `CopyRates(..., shift=1)` (last completed candle).

## Design principles (v1)

- Keep the EA small, readable, and dependency-free (single `.mq5` file).
- Prefer explicit inputs over magic constants.
- Log actionable errors to the Experts journal.
- Document install path, CSV location, and Quant Competition Lab import in `README.md`.

## Out of scope (v1)

- Historical backfill on attach
- Tick-level capture
- Cloud upload / remote sync
- Multi-terminal coordination
- Strategy signals or alerts
