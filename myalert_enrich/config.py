"""Configuration for MyAlert outcome enrichment."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


VALID_TP_SL_MODELS = ("atr_multiple", "fixed_pct", "fixed_price")
VALID_SAME_CANDLE_POLICIES = ("both", "loss_first", "tp_first")


@dataclass
class EnrichmentConfig:
    """TP/SL model and forward-horizon settings."""

    tp_sl_model: str = "atr_multiple"
    tp_atr_multiple: float = 2.0
    sl_atr_multiple: float = 1.0
    tp_pct: float = 0.002
    sl_pct: float = 0.001
    tp_price_distance: float = 0.0
    sl_price_distance: float = 0.0
    forward_horizon_bars: int = 20
    same_candle_policy: str = "both"
    entry_price_field: str = "Close"
    direction_field: str = "Direction"
    direction_fallback_field: str = "Trend Bias"
    atr_field: str = "ATR14"

    def validate(self) -> None:
        if self.tp_sl_model not in VALID_TP_SL_MODELS:
            raise ValueError(f"tp_sl_model must be one of {VALID_TP_SL_MODELS}")
        if self.same_candle_policy not in VALID_SAME_CANDLE_POLICIES:
            raise ValueError(
                f"same_candle_policy must be one of {VALID_SAME_CANDLE_POLICIES}"
            )
        if self.forward_horizon_bars < 1:
            raise ValueError("forward_horizon_bars must be >= 1")
        if self.tp_sl_model == "atr_multiple":
            if self.tp_atr_multiple <= 0 or self.sl_atr_multiple <= 0:
                raise ValueError("ATR multiples must be > 0")
        if self.tp_sl_model == "fixed_pct":
            if self.tp_pct <= 0 or self.sl_pct <= 0:
                raise ValueError("fixed_pct values must be > 0")
        if self.tp_sl_model == "fixed_price":
            if self.tp_price_distance <= 0 or self.sl_price_distance <= 0:
                raise ValueError("fixed_price distances must be > 0")


def load_config(path: Path | None = None) -> EnrichmentConfig:
    """Load JSON config or return defaults."""
    if path is None:
        cfg = EnrichmentConfig()
        cfg.validate()
        return cfg

    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    cfg = EnrichmentConfig(
        tp_sl_model=data.get("tp_sl_model", "atr_multiple"),
        tp_atr_multiple=float(data.get("tp_atr_multiple", 2.0)),
        sl_atr_multiple=float(data.get("sl_atr_multiple", 1.0)),
        tp_pct=float(data.get("tp_pct", 0.002)),
        sl_pct=float(data.get("sl_pct", 0.001)),
        tp_price_distance=float(data.get("tp_price_distance", 0.0)),
        sl_price_distance=float(data.get("sl_price_distance", 0.0)),
        forward_horizon_bars=int(data.get("forward_horizon_bars", 20)),
        same_candle_policy=data.get("same_candle_policy", "both"),
        entry_price_field=data.get("entry_price_field", "Close"),
        direction_field=data.get("direction_field", "Direction"),
        direction_fallback_field=data.get(
            "direction_fallback_field", "Trend Bias"
        ),
        atr_field=data.get("atr_field", "ATR14"),
    )
    cfg.validate()
    return cfg


DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "default_config.json"
