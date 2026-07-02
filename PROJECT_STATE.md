# PROJECT_STATE

**Project:** Broker Data Collector  
**Version:** 1.5.5  
**Status:** Startup symbol validation + batched backfill writes  
**Last updated:** 2026-06-08

## What exists

| Artifact | Status |
|----------|--------|
| `BrokerDataCollector.mq5` | Done — multi-TF collector with backfill + manifest |
| `README.md` | Done — install, attach, CSV path, QCL import |
| `MASTER_PROMPT.md` | Done — product contract for AI/human contributors |
| `CHANGELOG.md` | Done |
| `OPEN_TASKS.md` | Done |

## EA capabilities (v1.1)

- Multi-symbol and multi-timeframe collection via comma-separated inputs
- Configurable timer interval (default 60s)
- Historical backfill on attach (`EnableBackfill`, `BackfillBars`)
- Backfill quality summary in journal + `summary_YYYYMMDD.csv`
- Export formats: `Raw` (broker metadata) or `CompetitionLab` (QCL OHLCV)
- `manifest.json` for Quant Competition Lab auto-discovery
- Writes to `MQL5/Files/BrokerDataCollector/`
- One CSV per symbol/timeframe/calendar day (`SANITIZED_SYMBOL_TIMEFRAME_YYYYMMDD.csv`)
- Filename symbol sanitization: `# / \ : space` → `_` (broker symbol unchanged for market APIs and CSV row data)
- CSV header on new files; duplicate candle timestamps skipped
- Resume after restart by reading last timestamp from daily files
- Broker/account metadata attached to every row

## Safety posture

- No order or position functions used
- Read-only market/account queries only
- Fail-soft per symbol (one bad symbol does not stop others)

## Known limitations

- Symbol names must match broker naming (e.g. `US100` vs `NAS100`)
- Daily file rollover uses each bar's calendar day (terminal time)
- Spread/bid/ask sampled at write time, not historical tick replay
- Backfill limited by broker history depth and `BackfillBars` cap

## Next recommended steps

See `OPEN_TASKS.md`.
