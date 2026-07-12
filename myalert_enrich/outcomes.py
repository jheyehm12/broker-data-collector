"""Outcome simulation over forward OHLC bars."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from myalert_enrich.config import EnrichmentConfig
from myalert_enrich.ohlc import OhlcBar, format_timestamp


OUTCOME_WIN = "WIN"
OUTCOME_LOSS = "LOSS"
OUTCOME_BOTH = "BOTH"
OUTCOME_NONE = "NONE"

STATUS_MATCHED = "MATCHED"
STATUS_MISSING_OHLC = "MISSING_OHLC"
STATUS_INSUFFICIENT_FORWARD = "INSUFFICIENT_FORWARD"
STATUS_SKIP_NEUTRAL = "SKIP_NEUTRAL"
STATUS_INVALID_ROW = "INVALID_ROW"


@dataclass
class OutcomeResult:
    symbol: str
    timeframe: str
    timestamp: str
    entry_price: float
    direction: int
    tp_level: float
    sl_level: float
    first_reaction: int
    mfe: float
    mae: float
    tp_hit: int
    sl_hit: int
    tp_hit_time: str
    sl_hit_time: str
    outcome: str
    bars_to_outcome: int
    final_forward_return: float
    forward_bars_available: int
    enrichment_status: str


def _parse_float(value: str | float | int | None, default: float = 0.0) -> float:
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if text == "":
        return default
    return float(text)


def _parse_int(value: str | float | int | None, default: int = 0) -> int:
    if value is None:
        return default
    if isinstance(value, int):
        return value
    text = str(value).strip()
    if text == "":
        return default
    return int(float(text))


def resolve_direction(row: dict[str, str], config: EnrichmentConfig) -> int:
    direction = _parse_int(row.get(config.direction_field))
    if direction != 0:
        return 1 if direction > 0 else -1
    fallback = _parse_int(row.get(config.direction_fallback_field))
    if fallback > 0:
        return 1
    if fallback < 0:
        return -1
    return 0


def compute_tp_sl_levels(
    entry: float,
    direction: int,
    row: dict[str, str],
    config: EnrichmentConfig,
) -> tuple[float, float]:
    if config.tp_sl_model == "atr_multiple":
        atr = _parse_float(row.get(config.atr_field))
        if atr <= 0:
            raise ValueError("ATR14 missing or zero for atr_multiple model")
        tp_dist = config.tp_atr_multiple * atr
        sl_dist = config.sl_atr_multiple * atr
    elif config.tp_sl_model == "fixed_pct":
        tp_dist = entry * config.tp_pct
        sl_dist = entry * config.sl_pct
    else:
        tp_dist = config.tp_price_distance
        sl_dist = config.sl_price_distance

    if direction > 0:
        return entry + tp_dist, entry - sl_dist
    return entry - tp_dist, entry + sl_dist


def _bar_touches_tp(bar: OhlcBar, direction: int, tp_level: float) -> bool:
    return bar.high >= tp_level if direction > 0 else bar.low <= tp_level


def _bar_touches_sl(bar: OhlcBar, direction: int, sl_level: float) -> bool:
    return bar.low <= sl_level if direction > 0 else bar.high >= sl_level


def _resolve_same_candle_outcome(policy: str) -> str:
    if policy == "loss_first":
        return OUTCOME_LOSS
    if policy == "tp_first":
        return OUTCOME_WIN
    return OUTCOME_BOTH


def compute_mfe_mae(
    entry: float,
    direction: int,
    forward: Sequence[OhlcBar],
) -> tuple[float, float]:
    if not forward:
        return 0.0, 0.0

    if direction > 0:
        max_high = max(bar.high for bar in forward)
        min_low = min(bar.low for bar in forward)
        mfe = max(0.0, max_high - entry)
        mae = max(0.0, entry - min_low)
    else:
        min_low = min(bar.low for bar in forward)
        max_high = max(bar.high for bar in forward)
        mfe = max(0.0, entry - min_low)
        mae = max(0.0, max_high - entry)
    return mfe, mae


def compute_first_reaction(
    entry: float,
    direction: int,
    forward: Sequence[OhlcBar],
) -> int:
    if not forward:
        return 0
    delta = forward[0].close - entry
    if delta > 0:
        return 1 if direction > 0 else -1
    if delta < 0:
        return -1 if direction > 0 else 1
    return 0


def compute_final_forward_return(
    entry: float,
    direction: int,
    forward: Sequence[OhlcBar],
) -> float:
    if not forward or entry == 0:
        return 0.0
    last_close = forward[-1].close
    raw_return = (last_close - entry) / entry
    return raw_return * direction


def simulate_outcome(
    symbol: str,
    timeframe: str,
    timestamp: str,
    row: dict[str, str],
    forward: Sequence[OhlcBar],
    config: EnrichmentConfig,
) -> OutcomeResult:
    """Simulate TP/SL path over forward bars (decision-time safe)."""
    try:
        entry = _parse_float(row.get(config.entry_price_field))
        direction = resolve_direction(row, config)
        if entry <= 0:
            raise ValueError("invalid entry price")
        if direction == 0:
            return OutcomeResult(
                symbol=symbol,
                timeframe=timeframe,
                timestamp=timestamp,
                entry_price=entry,
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
                outcome=OUTCOME_NONE,
                bars_to_outcome=0,
                final_forward_return=0.0,
                forward_bars_available=len(forward),
                enrichment_status=STATUS_SKIP_NEUTRAL,
            )
        tp_level, sl_level = compute_tp_sl_levels(entry, direction, row, config)
    except (KeyError, ValueError):
        return OutcomeResult(
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
            outcome=OUTCOME_NONE,
            bars_to_outcome=0,
            final_forward_return=0.0,
            forward_bars_available=len(forward),
            enrichment_status=STATUS_INVALID_ROW,
        )

    horizon = forward[: config.forward_horizon_bars]
    mfe, mae = compute_mfe_mae(entry, direction, horizon)
    first_reaction = compute_first_reaction(entry, direction, horizon)
    final_return = compute_final_forward_return(entry, direction, horizon)

    status = STATUS_MATCHED
    if len(horizon) < config.forward_horizon_bars:
        status = STATUS_INSUFFICIENT_FORWARD

    tp_hit = 0
    sl_hit = 0
    tp_hit_time = ""
    sl_hit_time = ""
    outcome = OUTCOME_NONE
    bars_to_outcome = 0

    for offset, bar in enumerate(horizon, start=1):
        touches_tp = _bar_touches_tp(bar, direction, tp_level)
        touches_sl = _bar_touches_sl(bar, direction, sl_level)

        if touches_tp and touches_sl:
            tp_hit = 1
            sl_hit = 1
            ts = format_timestamp(bar.timestamp)
            tp_hit_time = ts
            sl_hit_time = ts
            bars_to_outcome = offset
            outcome = _resolve_same_candle_outcome(config.same_candle_policy)
            break

        if touches_tp:
            tp_hit = 1
            tp_hit_time = format_timestamp(bar.timestamp)
            bars_to_outcome = offset
            outcome = OUTCOME_WIN
            break

        if touches_sl:
            sl_hit = 1
            sl_hit_time = format_timestamp(bar.timestamp)
            bars_to_outcome = offset
            outcome = OUTCOME_LOSS
            break

    return OutcomeResult(
        symbol=symbol,
        timeframe=timeframe,
        timestamp=timestamp,
        entry_price=entry,
        direction=direction,
        tp_level=tp_level,
        sl_level=sl_level,
        first_reaction=first_reaction,
        mfe=mfe,
        mae=mae,
        tp_hit=tp_hit,
        sl_hit=sl_hit,
        tp_hit_time=tp_hit_time,
        sl_hit_time=sl_hit_time,
        outcome=outcome,
        bars_to_outcome=bars_to_outcome,
        final_forward_return=final_return,
        forward_bars_available=len(horizon),
        enrichment_status=status,
    )


OUTCOME_CSV_HEADER = [
    "Symbol",
    "Timeframe",
    "Timestamp",
    "Entry Price",
    "Direction",
    "TP Level",
    "SL Level",
    "Forward Horizon Bars",
    "TP SL Model",
    "First Reaction",
    "MFE",
    "MAE",
    "TP Hit",
    "SL Hit",
    "TP Hit Time",
    "SL Hit Time",
    "Outcome",
    "Bars To Outcome",
    "Final Forward Return",
    "Forward Bars Available",
    "Enrichment Status",
]


def outcome_to_row(result: OutcomeResult, config: EnrichmentConfig) -> dict[str, str]:
    return {
        "Symbol": result.symbol,
        "Timeframe": result.timeframe,
        "Timestamp": result.timestamp,
        "Entry Price": f"{result.entry_price:.10g}",
        "Direction": str(result.direction),
        "TP Level": f"{result.tp_level:.10g}",
        "SL Level": f"{result.sl_level:.10g}",
        "Forward Horizon Bars": str(config.forward_horizon_bars),
        "TP SL Model": config.tp_sl_model,
        "First Reaction": str(result.first_reaction),
        "MFE": f"{result.mfe:.10g}",
        "MAE": f"{result.mae:.10g}",
        "TP Hit": str(result.tp_hit),
        "SL Hit": str(result.sl_hit),
        "TP Hit Time": result.tp_hit_time,
        "SL Hit Time": result.sl_hit_time,
        "Outcome": result.outcome,
        "Bars To Outcome": str(result.bars_to_outcome),
        "Final Forward Return": f"{result.final_forward_return:.10g}",
        "Forward Bars Available": str(result.forward_bars_available),
        "Enrichment Status": result.enrichment_status,
    }
