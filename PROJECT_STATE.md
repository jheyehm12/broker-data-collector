# PROJECT_STATE

**Project:** Broker Data Collector  
**Version:** 1.0.0  
**Status:** Initial v1 complete  
**Last updated:** 2026-07-02

## What exists

| Artifact | Status |
|----------|--------|
| `BrokerDataCollector.mq5` | Done — timer-driven multi-symbol CSV collector |
| `README.md` | Done — install, attach, CSV path, QCL import |
| `MASTER_PROMPT.md` | Done — product contract for AI/human contributors |
| `CHANGELOG.md` | Done |
| `OPEN_TASKS.md` | Done |

## EA capabilities (v1)

- Multi-symbol collection via comma-separated input
- Configurable timeframe (default M1) and timer interval (default 60s)
- Writes to `MQL5/Files/BrokerDataCollector/`
- One CSV per symbol per calendar day
- CSV header on new files; duplicate candle timestamps skipped
- Resume after restart by reading last timestamp from today's file
- Broker/account metadata attached to every row

## Safety posture

- No order or position functions used
- Read-only market/account queries only
- Fail-soft per symbol (one bad symbol does not stop others)

## Known limitations

- Collects from EA attach time forward (no automatic historical backfill)
- Symbol names must match broker naming (e.g. `US100` vs `NAS100`)
- Daily file rollover uses terminal local time at write
- Spread/bid/ask sampled at write time, not historical tick replay

## Next recommended steps

See `OPEN_TASKS.md`.
