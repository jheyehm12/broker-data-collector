"""CLI for MyAlert ML readiness validation (Phase G)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from myalert_validate.models import ValidationConfig
from myalert_validate.validator import run_validation


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate MyAlert research + outcomes datasets for ML readiness (Phase G). "
            "Source CSV files are never modified."
        )
    )
    parser.add_argument(
        "research_csv",
        type=Path,
        help="Path to MyAlert_*_Research.csv",
    )
    parser.add_argument(
        "--outcomes-csv",
        type=Path,
        default=None,
        help="Path to MyAlert_*_Outcomes.csv (recommended)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output folder (default: <research>/../Validation/)",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="JSON validation thresholds (optional)",
    )
    return parser


def _load_validation_config(path: Path | None) -> ValidationConfig:
    if path is None:
        return ValidationConfig()
    data = json.loads(path.read_text(encoding="utf-8"))
    return ValidationConfig(
        min_rows_per_stream=int(data.get("min_rows_per_stream", 100)),
        min_per_outcome_class=int(data.get("min_per_outcome_class", 20)),
        min_eligible_fraction=float(data.get("min_eligible_fraction", 0.70)),
        correlation_threshold=float(data.get("correlation_threshold", 0.95)),
        missing_warning_fraction=float(data.get("missing_warning_fraction", 0.05)),
        missing_fail_fraction=float(data.get("missing_fail_fraction", 0.20)),
        timezone_offset_tolerance_hours=int(data.get("timezone_offset_tolerance_hours", 14)),
        train_fraction=float(data.get("train_fraction", 0.70)),
        val_fraction=float(data.get("val_fraction", 0.15)),
        test_fraction=float(data.get("test_fraction", 0.15)),
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.research_csv.is_file():
        print(f"Research CSV not found: {args.research_csv}", file=sys.stderr)
        return 1
    if args.outcomes_csv and not args.outcomes_csv.is_file():
        print(f"Outcomes CSV not found: {args.outcomes_csv}", file=sys.stderr)
        return 1

    config = _load_validation_config(args.config)
    report = run_validation(
        args.research_csv,
        args.outcomes_csv,
        args.output_dir,
        config,
    )

    out_dir = args.output_dir or args.research_csv.parent / "Validation"
    print(f"Overall verdict: {report.overall_verdict} ({report.overall_score}/100)")
    print(f"Eligible rows: {report.eligible_count}/{report.row_count}")
    print(f"Wrote: {out_dir / 'ML_READINESS_REPORT.md'}")
    print(f"Wrote: {out_dir / 'validation_report.json'}")
    print(f"Wrote: {out_dir / 'eligibility_flags.csv'}")
    return 0 if report.overall_verdict != "FAIL" else 2


if __name__ == "__main__":
    raise SystemExit(main())
