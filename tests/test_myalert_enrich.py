"""Tests for MyAlert outcome enrichment (Phase F)."""

from __future__ import annotations

import csv
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from myalert_enrich.config import EnrichmentConfig, load_config
from myalert_enrich.enricher import enrich_research_file, enrich_research_rows
from myalert_enrich.ohlc import OhlcBar, OhlcSeries, format_timestamp, load_raw_csv
from myalert_enrich.outcomes import (
    OUTCOME_BOTH,
    OUTCOME_LOSS,
    OUTCOME_NONE,
    OUTCOME_WIN,
    STATUS_INSUFFICIENT_FORWARD,
    STATUS_MATCHED,
    STATUS_MISSING_OHLC,
    STATUS_SKIP_NEUTRAL,
    simulate_outcome,
)


def _bar(ts: datetime, o: float, h: float, l: float, c: float) -> OhlcBar:
    return OhlcBar(timestamp=ts, open=o, high=h, low=l, close=c)


class OutcomeSimulationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.base = datetime(2026, 7, 13, 10, 0, 0)
        self.config = EnrichmentConfig(
            tp_sl_model="fixed_price",
            tp_price_distance=0.00050,
            sl_price_distance=0.00025,
            forward_horizon_bars=5,
            same_candle_policy="both",
        )
        self.row = {
            "Close": "1.08530",
            "Direction": "1",
            "ATR14": "0.00032",
            "Trend Bias": "1",
        }

    def test_win_when_tp_hit_first(self) -> None:
        forward = [
            _bar(self.base + timedelta(minutes=1), 1.0853, 1.0854, 1.0852, 1.08535),
            _bar(self.base + timedelta(minutes=2), 1.08535, 1.08590, 1.08530, 1.08580),
        ]
        result = simulate_outcome("EURUSD#", "M1", "ts", self.row, forward, self.config)
        self.assertEqual(result.outcome, OUTCOME_WIN)
        self.assertEqual(result.tp_hit, 1)
        self.assertEqual(result.sl_hit, 0)
        self.assertEqual(result.bars_to_outcome, 2)

    def test_loss_when_sl_hit_first(self) -> None:
        forward = [
            _bar(self.base + timedelta(minutes=1), 1.0853, 1.08535, 1.08490, 1.08500),
        ]
        result = simulate_outcome("EURUSD#", "M1", "ts", self.row, forward, self.config)
        self.assertEqual(result.outcome, OUTCOME_LOSS)
        self.assertEqual(result.sl_hit, 1)
        self.assertEqual(result.tp_hit, 0)
        self.assertEqual(result.bars_to_outcome, 1)

    def test_both_when_same_candle_hits_tp_and_sl(self) -> None:
        forward = [
            _bar(self.base + timedelta(minutes=1), 1.0853, 1.08600, 1.08490, 1.08520),
        ]
        result = simulate_outcome("EURUSD#", "M1", "ts", self.row, forward, self.config)
        self.assertEqual(result.outcome, OUTCOME_BOTH)
        self.assertEqual(result.tp_hit, 1)
        self.assertEqual(result.sl_hit, 1)
        self.assertEqual(result.tp_hit_time, result.sl_hit_time)
        self.assertEqual(result.bars_to_outcome, 1)

    def test_same_candle_loss_first_policy(self) -> None:
        config = EnrichmentConfig(
            tp_sl_model="fixed_price",
            tp_price_distance=0.00050,
            sl_price_distance=0.00025,
            forward_horizon_bars=5,
            same_candle_policy="loss_first",
        )
        forward = [
            _bar(self.base + timedelta(minutes=1), 1.0853, 1.08600, 1.08490, 1.08520),
        ]
        result = simulate_outcome("EURUSD#", "M1", "ts", self.row, forward, config)
        self.assertEqual(result.outcome, OUTCOME_LOSS)

    def test_none_when_neither_hit(self) -> None:
        forward = [
            _bar(self.base + timedelta(minutes=i), 1.0853, 1.0854, 1.0852, 1.0853)
            for i in range(1, 6)
        ]
        result = simulate_outcome("EURUSD#", "M1", "ts", self.row, forward, self.config)
        self.assertEqual(result.outcome, OUTCOME_NONE)
        self.assertEqual(result.tp_hit, 0)
        self.assertEqual(result.sl_hit, 0)
        self.assertEqual(result.bars_to_outcome, 0)

    def test_mfe_mae_and_final_return(self) -> None:
        forward = [
            _bar(self.base + timedelta(minutes=1), 1.0853, 1.08600, 1.08490, 1.08550),
            _bar(self.base + timedelta(minutes=2), 1.0855, 1.0856, 1.0850, 1.08510),
        ]
        result = simulate_outcome("EURUSD#", "M1", "ts", self.row, forward, self.config)
        self.assertAlmostEqual(result.mfe, 1.08600 - 1.08530, places=5)
        self.assertAlmostEqual(result.mae, 1.08530 - 1.08490, places=5)
        expected_return = ((1.08510 - 1.08530) / 1.08530) * 1
        self.assertAlmostEqual(result.final_forward_return, expected_return, places=8)

    def test_skip_neutral_direction(self) -> None:
        row = dict(self.row)
        row["Direction"] = "0"
        row["Trend Bias"] = "0"
        result = simulate_outcome("EURUSD#", "M1", "ts", row, [], self.config)
        self.assertEqual(result.enrichment_status, STATUS_SKIP_NEUTRAL)

    def test_insufficient_forward_status(self) -> None:
        forward = [
            _bar(self.base + timedelta(minutes=1), 1.0853, 1.0854, 1.0852, 1.08535),
        ]
        result = simulate_outcome("EURUSD#", "M1", "ts", self.row, forward, self.config)
        self.assertEqual(result.enrichment_status, STATUS_INSUFFICIENT_FORWARD)
        self.assertEqual(result.forward_bars_available, 1)


class IntegrationTests(unittest.TestCase):
    def test_end_to_end_enrichment_preserves_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw_folder = root / "raw"
            raw_folder.mkdir()
            research_path = root / "MyAlert" / "MyAlert_EURUSD_M1_Research.csv"
            research_path.parent.mkdir(parents=True)

            base = datetime(2026, 7, 13, 10, 0, 0)
            raw_rows = [
                ["timestamp", "symbol", "timeframe", "open", "high", "low", "close"],
            ]
            for i in range(8):
                ts = format_timestamp(base + timedelta(minutes=i))
                price = 1.08500 + i * 0.00010
                raw_rows.append(
                    [ts, "EURUSD#", "M1", f"{price:.5f}", f"{price+0.00040:.5f}",
                     f"{price-0.00020:.5f}", f"{price+0.00020:.5f}"]
                )

            raw_file = raw_folder / "EURUSD__M1_20260713.csv"
            with raw_file.open("w", newline="", encoding="utf-8") as handle:
                csv.writer(handle).writerows(raw_rows)

            research_header = [
                "Symbol", "Timeframe", "Timestamp", "Close", "Direction", "ATR14", "Trend Bias"
            ]
            research_rows = [
                research_header,
                ["EURUSD#", "M1", format_timestamp(base), "1.08500", "1", "0.00032", "1"],
                ["EURUSD#", "M1", format_timestamp(base + timedelta(minutes=8)), "1.08580", "1", "0.00032", "1"],
            ]
            with research_path.open("w", newline="", encoding="utf-8") as handle:
                csv.writer(handle).writerows(research_rows)

            original_text = research_path.read_text(encoding="utf-8")
            config = EnrichmentConfig(
                tp_sl_model="fixed_price",
                tp_price_distance=0.00050,
                sl_price_distance=0.00025,
                forward_horizon_bars=3,
            )
            output_path = enrich_research_file(research_path, raw_folder, config)
            self.assertTrue(output_path.is_file())
            self.assertEqual(research_path.read_text(encoding="utf-8"), original_text)

            with output_path.open(newline="", encoding="utf-8") as handle:
                enriched = list(csv.DictReader(handle))

            self.assertEqual(len(enriched), 2)
            self.assertEqual(enriched[0]["Outcome"], OUTCOME_WIN)
            self.assertEqual(enriched[0]["Enrichment Status"], STATUS_MATCHED)
            self.assertEqual(enriched[1]["Enrichment Status"], STATUS_MISSING_OHLC)

    def test_load_default_config(self) -> None:
        config = load_config()
        self.assertEqual(config.tp_sl_model, "atr_multiple")
        self.assertEqual(config.forward_horizon_bars, 20)


class OhlcLoaderTests(unittest.TestCase):
    def test_load_raw_csv(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, newline="", encoding="utf-8") as tmp:
            writer = csv.writer(tmp)
            writer.writerow(["timestamp", "open", "high", "low", "close"])
            writer.writerow(["2026.07.13 10:00:00", "1.1", "1.2", "1.0", "1.15"])
            path = Path(tmp.name)

        bars = load_raw_csv(path)
        path.unlink()
        self.assertEqual(len(bars), 1)
        self.assertEqual(bars[0].close, 1.15)

    def test_forward_bars_order(self) -> None:
        base = datetime(2026, 7, 13, 10, 0, 0)
        bars = [
            _bar(base, 1, 1, 1, 1),
            _bar(base + timedelta(minutes=1), 2, 2, 2, 2),
            _bar(base + timedelta(minutes=2), 3, 3, 3, 3),
        ]
        series = OhlcSeries(bars)
        forward = series.forward_bars(base, 2)
        self.assertEqual(len(forward), 2)
        self.assertEqual(forward[0].close, 2)
        self.assertEqual(forward[1].close, 3)


if __name__ == "__main__":
    unittest.main()
