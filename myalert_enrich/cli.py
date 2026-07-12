"""CLI for MyAlert outcome enrichment."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from myalert_enrich.config import load_config
from myalert_enrich.enricher import enrich_research_file


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Enrich MyAlert research CSV rows with forward-looking outcomes "
            "(Phase F post-processor). Source research files are never modified."
        )
    )
    parser.add_argument(
        "research_csv",
        type=Path,
        help="Path to MyAlert_*_Research.csv",
    )
    parser.add_argument(
        "--raw-folder",
        type=Path,
        required=True,
        help="Folder containing Broker Data Collector Raw daily CSV files",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="JSON config for TP/SL model and forward horizon (optional)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output folder (default: <research>/../Enriched/)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = load_config(args.config)

    if not args.research_csv.is_file():
        print(f"Research CSV not found: {args.research_csv}", file=sys.stderr)
        return 1
    if not args.raw_folder.is_dir():
        print(f"Raw folder not found: {args.raw_folder}", file=sys.stderr)
        return 1

    output_path = enrich_research_file(
        args.research_csv,
        args.raw_folder,
        config,
        args.output_dir,
    )
    print(f"Wrote enriched outcomes: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
