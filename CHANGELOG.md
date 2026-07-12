# CHANGELOG

All notable changes to Broker Data Collector are documented here.

Format based on [Keep a Changelog](https://keepachangelog.com/).

## [1.8.1] - 2026-07-13

### Added (MyAlert research CSV hardening — validator)

- Extended `RESEARCH_COLUMNS` to 68 (Record ID + 8 readable labels)
- New validation checks: duplicate Record IDs, timeframe boundary alignment, timestamp field consistency, categorical enum verification
- `docs/MYALERT_CATEGORICAL_CODES.md` — authoritative code/label mappings
- Unit tests: `tests/test_myalert_validate.py` (5 tests)

### Changed

- Python tools version → `1.8.1`
- `myalert_validate` expects v1.61+ research CSV header

## [1.61] - 2026-07-13

### Added (MyAlert research CSV hardening — EA)

- **Record ID** (col 60): `SYMBOL_TIMEFRAME_YYYYMMDDHHMMSS` from aligned broker candle open
- **Readable labels** (cols 61–68): Direction, expansion, trend, breakout, retest, follow-through, body strength
- `AlignBarOpenTimeToTimeframe()` — snaps broker bar open to exact timeframe boundaries
- `docs/MYALERT_CATEGORICAL_CODES.md` referenced from README

### Fixed

- Timestamp alignment: `Timestamp`, `Broker Timestamp`, `UTC Timestamp`, `Hour UTC`, `Session`, `Day of Week` all derived from the same aligned closed-candle open (fixes M1 `19:41:59` → `19:42:00` drift)

### Safety

- Core 59 columns unchanged in name and order; extension append-only
- Raw/CompetitionLab exports unchanged when `EnableMyAlertResearchFeatures = false`
- Legacy 59-column header still recognized for resume timestamp reads

## [1.8.0] - 2026-07-13

### Added (MyAlert Phase G — ML readiness validator)

- Python package `myalert_validate/` — validates research + outcomes for ML readiness
- Outputs: `ML_READINESS_REPORT.md`, `validation_report.json`, `eligibility_flags.csv`
- 17 checks: schema, types, duplicates, timestamp order, missing/invalid values, leakage, balance, variance, correlation, split readiness, timezone, incomplete outcomes, sample size
- PASS / WARNING / FAIL per check; weighted overall readiness score (0–100)
- Per-row `Eligible For Training` flags without modifying source CSVs
- ML recommendations: feature list, exclusions, targets, chronological split, baseline models
- CLI: `python -m myalert_validate` / `myalert-validate`
- Unit tests: `tests/test_myalert_validate.py` (4 tests)
- Default config: `myalert_validate/default_config.json`

### Safety

- No EA changes; no source CSV modification; no imputation; no random train/test split
- Decision-time and outcome data remain in separate files

## [1.7.0] - 2026-07-13

### Added (MyAlert Phase F — separate post-processor)

- Python package `myalert_enrich/` — outcome enrichment utility (does **not** modify EA or research CSV)
- Inputs: MyAlert research CSV + Raw OHLC folder + JSON config (TP/SL model, forward horizon)
- Outputs: `MyAlert/Enriched/MyAlert_*_Outcomes.csv` linked by `Symbol`, `Timeframe`, `Timestamp`
- Outcome fields: First Reaction, MFE, MAE, TP Hit, SL Hit, hit times, Outcome (WIN/LOSS/BOTH/NONE), Bars To Outcome, Final Forward Return
- Configurable TP/SL models: `atr_multiple`, `fixed_pct`, `fixed_price`
- Same-candle policies: `both`, `loss_first`, `tp_first`
- Enrichment status codes for row matching, missing OHLC, insufficient forward bars, neutral direction
- Unit tests: `tests/test_myalert_enrich.py` (12 tests)
- `pyproject.toml` with `myalert-enrich` CLI entry point

### Documented

- Phase F usage, schema, event-order logic, and validation in `README.md`
- Default config: `myalert_enrich/default_config.json`

### Safety

- Decision-time research CSV preserved unchanged — no future leakage into EA features
- Forward paths built only from Raw OHLC bars after decision timestamp

## [1.6.0] - 2026-07-13

### Added (MyAlert Phase E)

- **Market structure (cols 45–53):** Swing High, Swing Low, HH, HL, LH, LL, Trend Bias, Breakout State, Retest State
- Swing pivots: left/right = 5 (MyAlert `pivotLen`); confirmed after 5 bars without future leakage
- Trend bias: MyAlert struct short/long = 10/25 (bullish/bearish/neutral codes `1`/`-1`/`0`)
- BOS breakout/retest simulation: `bosPivotLen=3`, `breakoutLookback=10`, `retestWindow=6`
- `MYALERT_LOOKBACK_BARS` increased from 35 → **80** for structure history
- `MYALERT_MIN_HISTORY_BARS` = 36 for Phase E gate

### Documented

- Swing confirmation rules, structure flag formulas, trend/breakout/retest code tables in `README.md`
- Partial-history behavior: Phase E empty when `< 36` bars lookback; Phase D empty when `< 20`
- Performance impact of 80-bar lookback + BOS simulation

### Changed

- `#property version` → `1.60`
- MyAlert research CSV fully populated (59 columns) when history permits

### Safety

- Phase E logic only when `EnableMyAlertResearchFeatures = true`
- Closed candles only; no future leakage
- Raw/CompetitionLab exports unchanged when flag is off

## [1.5.9] - 2026-07-13

### Added (MyAlert Phase D)

- **Structure (cols 17–24):** Direction, Body Size, Range Size, wicks, body/wick ratios
- **Relative (cols 25–30):** Average Body 5/10/20, Current Body Ratio, ATR14 (SMA), Range-to-ATR
- **Sequence (cols 31–44):** Previous Direction 1–5, Previous Body Ratio 1–5, Consecutive Bullish/Bearish, Body/Range Expansion ratios
- **MyAlert raw inputs (cols 54–59):** Previous Body, Average Body, Previous Body Ratio, Follow Through, Distance Ratio, Body Strength
- `MYALERT_LOOKBACK_BARS` (35) for timer `CopyRates`; backfill copies extra lookback bars without writing them
- Helpers: `SafeDiv`, `GetBarBodySize`, `CalcAtrSma`, `CalcAverageBody`, `CountConsecutiveDirection`, `CalcFollowThrough`, `CalcMyAlertBodyStrengthCode`

### Documented

- All Phase D formulas in `README.md` (structure, relative, sequence, MyAlert raw, expansion classification)
- Insufficient-history placeholder rows (43 empty Phase D+ fields when `barIdx + 20 >= barsCount`)
- Duplicate/timestamp alignment validation vs main Raw CSV
- Performance impact: extra `CopyRates(35)` per stream per timer tick when enabled

### Changed

- MyAlert research schema: **59 columns** (was 58); cols 45–53 reserved for Phase E
- `#property version` → `1.59`

### Safety

- Phase D logic runs only when `EnableMyAlertResearchFeatures = true`
- Closed candles only (`CopyRates` shift = 1); no future leakage
- Raw/CompetitionLab exports unchanged when flag is off

## [1.5.8] - 2026-07-13

### Added (MyAlert Phase C)

- Timing fields: Timestamp, UTC Timestamp, Broker Timestamp, Symbol, Timeframe, Asset Class, Session, Day of Week, Hour UTC
- Raw candle fields: Open, High, Low, Close, Tick Volume, Real Volume, Spread (points at write time)
- `BarTimeToUtc()`, `ClassifySessionUtc()`, `ClassifyAssetClass()`, `DayOfWeekLabel()`
- Columns 17–58 remain empty (deferred to Phase D+)

### Documented

- UTC conversion: `UTC = bar.time - (TimeCurrent() - TimeGMT())`
- Session mapping by UTC hour (priority: Overlap → London → New York → Asia)
- Asset class heuristics from symbol name + `SYMBOL_TRADE_CALC_MODE`

## [1.5.7] - 2026-07-13

### Added

- `EnableMyAlertResearchFeatures` input (default **false**) — optional MyAlert research CSV export
- Separate MyAlert research file per symbol/timeframe: `BrokerDataCollector/MyAlert/MyAlert_SYMBOL_TIMEFRAME_Research.csv`
- Full 58-column research schema header (features populated in later phases)
- Phase B skeleton rows: `Timestamp` only; all feature columns empty until Phase C+
- Independent duplicate tracking via `g_lastMyAlertWrittenBarTime[]`
- MyAlert files excluded from `manifest.json` disk scan

### Safety

- When `EnableMyAlertResearchFeatures = false`, existing Raw/CompetitionLab exports and behavior are unchanged

## [1.5.5] - 2026-06-08

### Added

- **Startup symbol validation** — `SymbolExist` + `SymbolSelect` for every configured symbol before collection; invalid symbols skipped with warnings (EA continues)
- **Similar symbol suggestions** — scans terminal symbols and prints "Did you mean:" hints (e.g. `US100` → `US100Cash#`, `XAUUSD` → `GOLD#`)
- **Startup summary** — formatted journal block listing valid symbols, skipped symbols, timeframes, backfill, export format, and stream count
- **Improved symbol parser** — supports comma, semicolon, space, tab, and newline separators

## [1.5.4] - 2026-06-08

### Fixed

- **Backfill FileOpen 5004 storms** — group bars by calendar day; open each daily CSV once per symbol/timeframe/day, write all rows, then close (no per-candle FileOpen)
- **Manifest throttling** — `WriteManifest()` once after full OnInit backfill pass; once per timer cycle (not per bar or per stream)

### Added

- `BuildBarRow()` shared row builder for timer append and batched backfill writes

## [1.5.3] - 2026-06-08

### Fixed

- **Symbol propagation audit** — confirmed entire pipeline uses configured loop symbols from `g_symbols[]`; no `_Symbol` or `Symbol()` usage
- Silent `SymbolSelect` failures in `BackfillSymbol` and `CollectSymbolBar` now log clearly
- `PrepareSymbolForData()` centralizes `SymbolSelect` with `SYMBOL_EXIST` check before every collection stage
- `CopyRatesForLoopSymbol()` logs and calls `CopyRates` with explicit loop symbol only

### Added

- Pipeline debug logging: `Processing symbol=<…>`, `CopyRates symbol=<…>`, `Writing CSV symbol=<…> Filename=<…>`
- `LogConfiguredSymbols()` on init and manifest write
- `ParseSymbolList` logs each added symbol; supports comma, semicolon, and newline delimiters; skips duplicates

## [1.5.2] - 2026-06-08

### Added

- **Filename symbol sanitization** — broker symbols with `#`, `/`, `\`, `:`, or spaces are sanitized for CSV/manifest filenames only (`#` → `_`, etc.)
- `SanitizeSymbolForFilename()` — examples: `BTCUSD#` → `BTCUSD_`, `GOLD#` → `GOLD_`, `US100Cash#` → `US100Cash_`
- Raw symbol unchanged for `SymbolSelect`, `CopyRates`, and CSV row `symbol` column

### Changed

- Daily data files: `SANITIZED_SYMBOL_TIMEFRAME_YYYYMMDD.csv`
- Manifest `files[].filename` and parsed `files[].symbol` reflect sanitized names; top-level `symbols` array keeps broker symbols

## [1.5.1] - 2026-06-08

### Fixed

- Intermittent `FileOpen` error **5004** (`ERR_FILE_CANNOT_OPEN`) on CompetitionLab and Raw CSV writes
- All `FileOpen()` calls routed through `OpenFileWithRetry()` with parent-folder verification, full-path logging, and EA-level concurrent-access warnings

### Added

- `OpenFileWithRetry()` — logs full `MQL5/Files` path, verifies folder before open, retries 5004 up to 3 times (100 ms delay), logs final failure
- `CloseTrackedFile()` — ensures every successful open is paired with `FileClose()` and lock release
- `BuildFilesFullPath()`, `VerifyFolderBeforeFileOpen()`, in-process open-path tracking for concurrent write diagnostics

## [1.5.0] - 2026-07-02

### Added

- Dataset manifest export: `BrokerDataCollector/manifest.json`
- Manifest fields: broker, server, account, export format, symbols, timeframes, file index
- Per-file manifest stats: rows, first/last timestamp, folder, filename
- `WriteManifest()` refreshed after backfill, timer writes, attach, and detach
- Disk scan helpers: `CollectManifestFilesFromDisk()`, `ParseDataFileName()`, `GetFileRowStats()`

## [1.4.0] - 2026-07-02

### Added

- Multi-timeframe input `InpTimeframes` (default `M1,M5,M15,H1`)
- Per symbol/timeframe collection, backfill, and duplicate tracking
- Unified filename `SYMBOL_TIMEFRAME_YYYYMMDD.csv` for both Raw and CompetitionLab formats
- `ParseTimeframeList()`, `ParseTimeframeLabel()`, `StreamIndex()`, `StreamCount()`

### Changed

- Replaced single `InpTimeframe` input with comma-separated `InpTimeframes`
- Timer and backfill iterate all symbol × timeframe streams
- Quality summary logged per symbol/timeframe pair

## [1.3.0] - 2026-07-02

### Added

- `ExportFormat` input: `Raw` (default) or `CompetitionLab`
- CompetitionLab CSV: `Timestamp,Open,High,Low,Close,Volume` in `BrokerDataCollector/CompetitionLab/`
- CompetitionLab filename: `SYMBOL_TIMEFRAME_YYYYMMDD.csv`
- `BuildCompetitionLabRow()`, `GetDataOutputFolder()`, `ExportFormatLabel()`

## [1.2.0] - 2026-07-02

### Added

- Per-symbol backfill quality summary printed to Experts journal (bars, first/last timestamp, spread stats)
- Daily summary CSV: `BrokerDataCollector/summary_YYYYMMDD.csv`
- `BackfillStats` struct with `RecordWrittenBar()`, `PrintBackfillSummary()`, `AppendDailySummaryRow()`

## [1.1.0] - 2026-07-02

### Added

- Historical backfill on attach via `EnableBackfill` (default true) and `BackfillBars` (default 5000)
- `BackfillSymbol()` — writes oldest-to-newest closed bars into correct daily CSV files
- `BarDayStart()` and `ReadLastTimestampFromDailyFile()` for per-day duplicate detection
- Daily CSV filenames now derived from each bar's timestamp (fixes midnight rollover)

### Changed

- `OnInit` runs backfill before starting the timer when backfill is enabled
- Resume logic scans the relevant daily file per bar day instead of today only

## [1.0.0] - 2026-07-02

### Added

- Initial `BrokerDataCollector.mq5` Expert Advisor
- Multi-symbol input (`BTCUSD,XAUUSD,US100,EURUSD` default)
- Configurable timeframe (M1 default) and 60-second timer
- CSV export to `MQL5/Files/BrokerDataCollector/` (one file per symbol per day)
- CSV header on new files; duplicate bar timestamps prevented
- Resume-safe restart by scanning today's CSV for last timestamp
- Broker, server, account, OHLCV, bid/ask, spread, digits, and point fields
- Project docs: `README.md`, `MASTER_PROMPT.md`, `PROJECT_STATE.md`, `OPEN_TASKS.md`

### Safety

- No trading or order functions — data collection only
