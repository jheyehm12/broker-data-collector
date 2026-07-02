# CHANGELOG

All notable changes to Broker Data Collector are documented here.

Format based on [Keep a Changelog](https://keepachangelog.com/).

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
