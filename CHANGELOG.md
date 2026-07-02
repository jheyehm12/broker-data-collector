# CHANGELOG

All notable changes to Broker Data Collector are documented here.

Format based on [Keep a Changelog](https://keepachangelog.com/).

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
