"""Orchestrate MyAlert research CSV outcome enrichment."""

from __future__ import annotations

import csv
from pathlib import Path

from myalert_enrich.config import EnrichmentConfig
from myalert_enrich.ohlc import OhlcSeries, load_ohlc_table, parse_timestamp
from myalert_enrich.outcomes import (
    OUTCOME_CSV_HEADER,
    STATUS_MISSING_OHLC,
    OutcomeResult,
    outcome_to_row,
    simulate_outcome,
)


def _read_research_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            return []
        return list(reader)


def _stream_key(row: dict[str, str]) -> tuple[str, str]:
    return row.get("Symbol", ""), row.get("Timeframe", "")


def enrich_research_rows(
    research_rows: list[dict[str, str]],
    ohlc_by_stream: dict[tuple[str, str], OhlcSeries],
    config: EnrichmentConfig,
) -> list[OutcomeResult]:
    results: list[OutcomeResult] = []
    for row in research_rows:
        symbol, timeframe = _stream_key(row)
        timestamp = row.get("Timestamp", "")
        series = ohlc_by_stream.get((symbol, timeframe))

        if series is None or not timestamp:
            results.append(
                OutcomeResult(
                    symbol=symbol,
                    timeframe=timeframe,
                    timestamp=timestamp,
                    entry_price=0.0,
                    direction=0,
                    tp_level=0.0,
                    sl_level=0.0,
                    first_reaction=0,
                    mfe=0.0,
                    mae=0.0,
                    tp_hit=0,
                    sl_hit=0,
                    tp_hit_time="",
                    sl_hit_time="",
                    outcome="NONE",
                    bars_to_outcome=0,
                    final_forward_return=0.0,
                    forward_bars_available=0,
                    enrichment_status=STATUS_MISSING_OHLC,
                )
            )
            continue

        try:
            ts = parse_timestamp(timestamp)
        except ValueError:
            results.append(
                OutcomeResult(
                    symbol=symbol,
                    timeframe=timeframe,
                    timestamp=timestamp,
                    entry_price=0.0,
                    direction=0,
                    tp_level=0.0,
                    sl_level=0.0,
                    first_reaction=0,
                    mfe=0.0,
                    mae=0.0,
                    tp_hit=0,
                    sl_hit=0,
                    tp_hit_time="",
                    sl_hit_time="",
                    outcome="NONE",
                    bars_to_outcome=0,
                    final_forward_return=0.0,
                    forward_bars_available=0,
                    enrichment_status=STATUS_MISSING_OHLC,
                )
            )
            continue

        if series.find_index(ts) is None:
            results.append(
                OutcomeResult(
                    symbol=symbol,
                    timeframe=timeframe,
                    timestamp=timestamp,
                    entry_price=0.0,
                    direction=0,
                    tp_level=0.0,
                    sl_level=0.0,
                    first_reaction=0,
                    mfe=0.0,
                    mae=0.0,
                    tp_hit=0,
                    sl_hit=0,
                    tp_hit_time="",
                    sl_hit_time="",
                    outcome="NONE",
                    bars_to_outcome=0,
                    final_forward_return=0.0,
                    forward_bars_available=0,
                    enrichment_status=STATUS_MISSING_OHLC,
                )
            )
            continue

        forward = series.forward_bars(ts, config.forward_horizon_bars)
        results.append(
            simulate_outcome(symbol, timeframe, timestamp, row, forward, config)
        )
    return results


def build_output_path(research_path: Path, output_dir: Path | None) -> Path:
    stem = research_path.stem
    if stem.endswith("_Research"):
        stem = stem[: -len("_Research")] + "_Outcomes"
    else:
        stem = f"{stem}_Outcomes"
    folder = output_dir if output_dir is not None else research_path.parent / "Enriched"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / f"{stem}.csv"


def write_outcomes_csv(
    path: Path,
    results: list[OutcomeResult],
    config: EnrichmentConfig,
) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTCOME_CSV_HEADER)
        writer.writeheader()
        for result in results:
            writer.writerow(outcome_to_row(result, config))


def enrich_research_file(
    research_path: Path,
    raw_folder: Path,
    config: EnrichmentConfig,
    output_dir: Path | None = None,
) -> Path:
    """
    Enrich one MyAlert research CSV using Raw OHLC for forward paths.

    The source research CSV is never modified.
    """
    rows = _read_research_csv(research_path)
    streams = {_stream_key(row) for row in rows if row.get("Symbol")}
    ohlc_by_stream = load_ohlc_table(raw_folder, streams)
    results = enrich_research_rows(rows, ohlc_by_stream, config)
    output_path = build_output_path(research_path, output_dir)
    write_outcomes_csv(output_path, results, config)
    return output_path
