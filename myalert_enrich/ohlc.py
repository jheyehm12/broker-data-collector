"""Load and index OHLC series from Broker Data Collector Raw CSV files."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable


TIMESTAMP_FORMAT = "%Y.%m.%d %H:%M:%S"
RAW_DAILY_PATTERN = re.compile(
    r"^(?P<symbol>.+)_(?P<timeframe>[A-Z0-9]+)_(?P<date>\d{8})\.csv$",
    re.IGNORECASE,
)


def sanitize_symbol_for_filename(symbol: str) -> str:
    """Match BrokerDataCollector.mq5 SanitizeSymbolForFilename."""
    result = symbol
    for ch in ("#", "/", "\\", ":", " "):
        result = result.replace(ch, "_")
    return result


def parse_timestamp(value: str) -> datetime:
    return datetime.strptime(value.strip(), TIMESTAMP_FORMAT)


def format_timestamp(value: datetime) -> str:
    return value.strftime(TIMESTAMP_FORMAT)


@dataclass(frozen=True)
class OhlcBar:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float


class OhlcSeries:
    """Time-ordered OHLC bars for one symbol/timeframe stream."""

    def __init__(self, bars: list[OhlcBar]):
        self._bars = sorted(bars, key=lambda b: b.timestamp)
        self._index = {bar.timestamp: i for i, bar in enumerate(self._bars)}

    @property
    def bars(self) -> list[OhlcBar]:
        return list(self._bars)

    def __len__(self) -> int:
        return len(self._bars)

    def find_index(self, timestamp: datetime) -> int | None:
        return self._index.get(timestamp)

    def forward_bars(self, timestamp: datetime, max_bars: int) -> list[OhlcBar]:
        idx = self.find_index(timestamp)
        if idx is None:
            return []
        end = min(len(self._bars), idx + 1 + max_bars)
        return self._bars[idx + 1 : end]


def load_raw_csv(path: Path) -> list[OhlcBar]:
    bars: list[OhlcBar] = []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            return bars
        ts_key = "timestamp" if "timestamp" in reader.fieldnames else "Timestamp"
        for row in reader:
            try:
                bars.append(
                    OhlcBar(
                        timestamp=parse_timestamp(row[ts_key]),
                        open=float(row["open" if "open" in row else "Open"]),
                        high=float(row["high" if "high" in row else "High"]),
                        low=float(row["low" if "low" in row else "Low"]),
                        close=float(row["close" if "close" in row else "Close"]),
                    )
                )
            except (KeyError, ValueError):
                continue
    return bars


def load_raw_folder(
    raw_folder: Path,
    symbol: str,
    timeframe: str,
) -> OhlcSeries:
    """Load all daily Raw CSV files for one symbol/timeframe."""
    sanitized = sanitize_symbol_for_filename(symbol)
    prefix = f"{sanitized}_{timeframe}_"
    bars: list[OhlcBar] = []

    if not raw_folder.is_dir():
        return OhlcSeries(bars)

    for path in sorted(raw_folder.glob(f"{prefix}*.csv")):
        if not RAW_DAILY_PATTERN.match(path.name):
            continue
        bars.extend(load_raw_csv(path))

    # Deduplicate by timestamp (keep last write if duplicates exist).
    dedup: dict[datetime, OhlcBar] = {}
    for bar in bars:
        dedup[bar.timestamp] = bar
    return OhlcSeries(list(dedup.values()))


def load_ohlc_table(
    raw_folder: Path,
    streams: Iterable[tuple[str, str]],
) -> dict[tuple[str, str], OhlcSeries]:
    cache: dict[tuple[str, str], OhlcSeries] = {}
    for symbol, timeframe in streams:
        key = (symbol, timeframe)
        if key not in cache:
            cache[key] = load_raw_folder(raw_folder, symbol, timeframe)
    return cache
