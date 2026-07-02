# OPEN_TASKS

Future work for Broker Data Collector. v1 is intentionally minimal.

## High value

- [x] **Historical backfill on attach** — optionally seed N closed bars when EA starts
- [ ] **Symbol alias map** — input mapping for broker suffixes (e.g. `BTCUSD` → `BTCUSD.a`)
- [ ] **Configurable output folder** — input parameter instead of fixed `BrokerDataCollector`
- [ ] **Forming-bar mode** — optional flag to update the current (unclosed) bar in place

## Quality / ops

- [ ] **Journal status panel** — on-chart comment with last write time per symbol
- [ ] **Error counter** — track and expose repeated `CopyRates` / file I/O failures
- [ ] **Unit-style MQL5 tests** — extract CSV/path helpers into `.mqh` for testability

## Integration

- [ ] **Quant Competition Lab sample notebook** — documented import + schema validation
- [x] **Dataset manifest (`manifest.json`)** — auto-discovery index for QCL
- [ ] **Optional JSON lines export** — parallel format for programmatic pipelines
- [x] **Multi-timeframe mode** — collect several TFs per symbol in one run

- [ ] **FILE_COMMON toggle** — share CSV across MT5 data folders on same machine
- [ ] **Midnight rollover hook** — explicit day-change handling and file rotation log
