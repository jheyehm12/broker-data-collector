"""Tests for MyAlert ML readiness validation (Phase G)."""

from __future__ import annotations

import csv
import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from myalert_enrich.ohlc import format_timestamp
from myalert_validate.models import VERDICT_FAIL, VERDICT_PASS, ValidationConfig
from myalert_validate.schema import RESEARCH_COLUMNS
from myalert_validate.validator import run_validation


def _minimal_research_row(base: datetime, i: int) -> dict[str, str]:
    row = {col: "0" for col in RESEARCH_COLUMNS}
    broker_ts = base + timedelta(minutes=i)
    utc_ts = broker_ts - timedelta(hours=8)
    broker_text = format_timestamp(broker_ts)
    utc_text = format_timestamp(utc_ts)
    row["Timestamp"] = broker_text
    row["UTC Timestamp"] = utc_text
    row["Broker Timestamp"] = broker_text
    row["Symbol"] = "EURUSD#"
    row["Timeframe"] = "M1"
    row["Asset Class"] = "Forex"
    row["Session"] = "Asia" if utc_ts.hour < 8 or utc_ts.hour >= 22 else "London"
    if 8 <= utc_ts.hour < 13:
        row["Session"] = "London"
    elif 13 <= utc_ts.hour < 17:
        row["Session"] = "London-NY Overlap"
    elif 17 <= utc_ts.hour < 22:
        row["Session"] = "New York"
    row["Day of Week"] = utc_ts.strftime("%A")
    row["Hour UTC"] = str(utc_ts.hour)
    row["Open"] = "1.08500"
    row["High"] = "1.08540"
    row["Low"] = "1.08490"
    row["Close"] = "1.08520"
    row["Tick Volume"] = "100"
    row["Real Volume"] = "0"
    row["Spread"] = "12"
    row["Direction"] = "1"
    row["Body Size"] = "0.00020"
    row["Range Size"] = "0.00050"
    row["Upper Wick"] = "0.00015"
    row["Lower Wick"] = "0.00010"
    row["Body-to-Range Ratio"] = "0.40"
    row["Upper Wick Ratio"] = "0.30"
    row["Lower Wick Ratio"] = "0.20"
    row["Average Body 5"] = "0.00018"
    row["Average Body 10"] = "0.00019"
    row["Average Body 20"] = "0.00020"
    row["Current Body Ratio"] = "1.00"
    row["ATR14"] = "0.00032"
    row["Range-to-ATR"] = "1.50"
    for n in range(1, 6):
        row[f"Previous Direction {n}"] = "1"
        row[f"Previous Body Ratio {n}"] = "0.35"
    row["Consecutive Bullish"] = "2"
    row["Consecutive Bearish"] = "0"
    row["Body Expansion"] = "1.05"
    row["Range Expansion"] = "1.02"
    row["Swing High"] = "1.08545"
    row["Swing Low"] = "1.08470"
    row["HH"] = "1"
    row["HL"] = "0"
    row["LH"] = "0"
    row["LL"] = "0"
    row["Trend Bias"] = "1"
    row["Breakout State"] = "0"
    row["Retest State"] = "0"
    row["Previous Body"] = "0.00018"
    row["Average Body"] = "0.00020"
    row["Previous Body Ratio"] = "0.38"
    row["Follow Through"] = "1"
    row["Distance Ratio"] = "0.62"
    row["Body Strength"] = "2"
    compact_ts = broker_ts.strftime("%Y%m%d%H%M%S")
    row["Record ID"] = f"EURUSD_M1_{compact_ts}"
    row["Direction Label"] = "Bullish"
    row["Body Expansion Label"] = "Expansion"
    row["Range Expansion Label"] = "Expansion"
    row["Trend Bias Label"] = "BULLISH"
    row["Breakout State Label"] = "NONE"
    row["Retest State Label"] = "NONE"
    row["Follow Through Label"] = "Yes"
    row["Body Strength Label"] = "STRONG"
    return row


def _write_csv(path: Path, header: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)


class ValidationTests(unittest.TestCase):
    def test_valid_dataset_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            research_path = root / "MyAlert_EURUSD_M1_Research.csv"
            outcomes_path = root / "MyAlert_EURUSD_M1_Outcomes.csv"
            base = datetime(2026, 7, 13, 10, 0, 0)

            research_rows = [_minimal_research_row(base, i) for i in range(120)]
            _write_csv(research_path, RESEARCH_COLUMNS, research_rows)

            outcome_header = [
                "Symbol", "Timeframe", "Timestamp", "Entry Price", "Direction",
                "TP Level", "SL Level", "Forward Horizon Bars", "TP SL Model",
                "First Reaction", "MFE", "MAE", "TP Hit", "SL Hit",
                "TP Hit Time", "SL Hit Time", "Outcome", "Bars To Outcome",
                "Final Forward Return", "Forward Bars Available", "Enrichment Status",
            ]
            outcome_rows = []
            for i, rr in enumerate(research_rows):
                outcome_rows.append(
                    {
                        "Symbol": rr["Symbol"],
                        "Timeframe": rr["Timeframe"],
                        "Timestamp": rr["Timestamp"],
                        "Entry Price": rr["Close"],
                        "Direction": "1",
                        "TP Level": "1.08570",
                        "SL Level": "1.08495",
                        "Forward Horizon Bars": "20",
                        "TP SL Model": "atr_multiple",
                        "First Reaction": "1",
                        "MFE": "0.00040",
                        "MAE": "0.00010",
                        "TP Hit": "1" if i % 2 == 0 else "0",
                        "SL Hit": "0" if i % 2 == 0 else "1",
                        "TP Hit Time": rr["Timestamp"] if i % 2 == 0 else "",
                        "SL Hit Time": "" if i % 2 == 0 else rr["Timestamp"],
                        "Outcome": "WIN" if i % 2 == 0 else "LOSS",
                        "Bars To Outcome": "3",
                        "Final Forward Return": "0.0001",
                        "Forward Bars Available": "20",
                        "Enrichment Status": "MATCHED",
                    }
                )
            _write_csv(outcomes_path, outcome_header, outcome_rows)

            original_research = research_path.read_text(encoding="utf-8")
            config = ValidationConfig(min_rows_per_stream=100, min_per_outcome_class=20)
            report = run_validation(research_path, outcomes_path, root / "Validation", config)

            self.assertEqual(research_path.read_text(encoding="utf-8"), original_research)
            self.assertIn(report.overall_verdict, (VERDICT_PASS, "WARNING"))
            self.assertGreater(report.overall_score, 50)
            self.assertTrue((root / "Validation" / "ML_READINESS_REPORT.md").is_file())
            self.assertTrue((root / "Validation" / "validation_report.json").is_file())
            self.assertTrue((root / "Validation" / "eligibility_flags.csv").is_file())

            payload = json.loads((root / "Validation" / "validation_report.json").read_text())
            self.assertEqual(payload["row_count"], 120)
            self.assertGreater(payload["eligible_count"], 0)

    def test_schema_fail_on_missing_columns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            research_path = root / "bad_research.csv"
            _write_csv(research_path, ["Symbol", "Timeframe", "Timestamp"], [{"Symbol": "X", "Timeframe": "M1", "Timestamp": "2026.07.13 10:00:00"}])
            report = run_validation(research_path, None, root / "Validation", ValidationConfig())
            self.assertEqual(report.overall_verdict, VERDICT_FAIL)
            schema_checks = [c for c in report.checks if c.check_id == "research_schema"]
            self.assertEqual(schema_checks[0].verdict, VERDICT_FAIL)

    def test_duplicate_keys_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            research_path = root / "dup.csv"
            row = _minimal_research_row(datetime(2026, 7, 13, 10, 0, 0), 0)
            _write_csv(research_path, RESEARCH_COLUMNS, [row, row])
            report = run_validation(research_path, None, root / "Validation", ValidationConfig())
            dup = next(c for c in report.checks if c.check_id == "duplicate_keys")
            self.assertEqual(dup.verdict, VERDICT_FAIL)

    def test_feature_leakage_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            research_path = root / "leak.csv"
            cols = RESEARCH_COLUMNS + ["Outcome", "MFE"]
            row = _minimal_research_row(datetime(2026, 7, 13, 10, 0, 0), 0)
            row["Outcome"] = "WIN"
            row["MFE"] = "0.001"
            _write_csv(research_path, cols, [row])
            report = run_validation(research_path, None, root / "Validation", ValidationConfig())
            leak = next(c for c in report.checks if c.check_id == "feature_leakage")
            self.assertEqual(leak.verdict, VERDICT_FAIL)


    def test_duplicate_record_ids_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            research_path = root / "dup_rid.csv"
            row = _minimal_research_row(datetime(2026, 7, 13, 10, 0, 0), 0)
            dup = dict(row)
            dup["Timestamp"] = "2026.07.13 10:01:00"
            dup["UTC Timestamp"] = "2026.07.13 02:01:00"
            dup["Broker Timestamp"] = "2026.07.13 10:01:00"
            _write_csv(research_path, RESEARCH_COLUMNS, [row, dup])
            report = run_validation(research_path, None, root / "Validation", ValidationConfig())
            rid = next(c for c in report.checks if c.check_id == "duplicate_record_ids")
            self.assertEqual(rid.verdict, VERDICT_FAIL)


if __name__ == "__main__":
    unittest.main()
