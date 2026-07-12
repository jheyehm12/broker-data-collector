"""Orchestrate ML readiness validation."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from myalert_validate.checks import (
    check_categorical_enums,
    check_class_balance,
    check_correlation,
    check_data_types,
    check_duplicate_keys,
    check_duplicate_record_ids,
    check_feature_leakage,
    check_feature_variance,
    check_incomplete_outcomes,
    check_invalid_numerics,
    check_minimum_sample_size,
    check_missing_values,
    check_outcome_leakage,
    check_required_columns,
    check_schema,
    check_split_readiness,
    check_symbol_timeframe_consistency,
    check_timestamp_field_consistency,
    check_timestamp_order,
    check_timeframe_alignment,
    check_timezone_consistency,
)
from myalert_validate.eligibility import build_eligibility_rows, write_eligibility_csv
from myalert_validate.loader import load_csv
from myalert_validate.models import ValidationConfig, ValidationReport
from myalert_validate.recommendations import build_recommendations
from myalert_validate.report import write_json_report, write_markdown_report
from myalert_validate.schema import (
    JOIN_KEYS,
    OUTCOME_COLUMNS,
    OUTCOME_NUMERIC_COLUMNS,
    RESEARCH_COLUMNS,
    RESEARCH_NUMERIC_COLUMNS,
)
from myalert_validate.scoring import compute_overall


def _outcomes_by_key(rows: list[dict[str, str]]) -> dict[tuple[str, str, str], dict[str, str]]:
    return {
        (r.get("Symbol", ""), r.get("Timeframe", ""), r.get("Timestamp", "")): r for r in rows
    }


def run_validation(
    research_path: Path,
    outcomes_path: Path | None = None,
    output_dir: Path | None = None,
    config: ValidationConfig | None = None,
) -> ValidationReport:
    """
    Validate MyAlert research + outcomes datasets for ML readiness.

    Source CSV files are never modified. Writes reports and eligibility flags only.
    """
    cfg = config or ValidationConfig()
    out_dir = output_dir or research_path.parent / "Validation"
    out_dir.mkdir(parents=True, exist_ok=True)

    research_cols, research_rows = load_csv(research_path)
    outcome_cols: list[str] = []
    outcome_rows: list[dict[str, str]] | None = None
    if outcomes_path and outcomes_path.is_file():
        outcome_cols, outcome_rows = load_csv(outcomes_path)

    checks = [
        check_schema(research_cols, RESEARCH_COLUMNS, "research_schema", "Research"),
        check_required_columns(research_cols, list(JOIN_KEYS) + ["Close", "Direction", "ATR14"], "required_columns"),
        check_data_types(research_rows, RESEARCH_NUMERIC_COLUMNS, "research_data_types"),
        check_duplicate_keys(research_rows, "duplicate_keys"),
        check_duplicate_record_ids(research_rows, "duplicate_record_ids"),
        check_timestamp_order(research_rows, "timestamp_order"),
        check_timeframe_alignment(research_rows, "timeframe_alignment"),
        check_timestamp_field_consistency(research_rows, "timestamp_consistency"),
        check_categorical_enums(research_rows, "categorical_enums"),
        check_missing_values(research_rows, RESEARCH_COLUMNS, cfg, "missing_values"),
        check_invalid_numerics(research_rows, RESEARCH_NUMERIC_COLUMNS, "invalid_numerics"),
        check_feature_leakage(research_cols, "feature_leakage"),
        check_outcome_leakage(research_rows, outcome_rows, "outcome_leakage"),
        check_feature_variance(research_rows, RESEARCH_NUMERIC_COLUMNS, "feature_variance"),
        check_correlation(research_rows, RESEARCH_NUMERIC_COLUMNS, cfg, "correlation"),
        check_split_readiness(research_rows, cfg, "split_readiness"),
        check_symbol_timeframe_consistency(research_rows, "symbol_timeframe"),
        check_timezone_consistency(research_rows, cfg, "timezone"),
    ]

    if outcome_rows is not None:
        checks.insert(
            1,
            check_schema(outcome_cols, OUTCOME_COLUMNS, "outcomes_schema", "Outcomes"),
        )
        checks.extend(
            [
                check_data_types(outcome_rows, OUTCOME_NUMERIC_COLUMNS, "outcome_data_types"),
                check_class_balance(outcome_rows, cfg, "class_balance"),
                check_incomplete_outcomes(outcome_rows, "incomplete_outcomes"),
                check_minimum_sample_size(outcome_rows, cfg, "minimum_sample_size"),
            ]
        )
    else:
        checks.append(
            check_minimum_sample_size(None, cfg, "minimum_sample_size"),
        )

    outcomes_map = _outcomes_by_key(outcome_rows) if outcome_rows else {}
    eligibility = build_eligibility_rows(research_rows, outcomes_map)
    eligible_count = sum(1 for r in eligibility if r["Eligible For Training"] == "1")

    write_eligibility_csv(out_dir / "eligibility_flags.csv", eligibility)

    recommendations = build_recommendations()
    score, verdict, blockers, fixes = compute_overall(checks, cfg)

    generated = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    report = ValidationReport(
        research_path=str(research_path),
        outcomes_path=str(outcomes_path) if outcomes_path else None,
        checks=checks,
        overall_score=score,
        overall_verdict=verdict,
        blockers=blockers,
        recommended_fixes=fixes,
        recommendations=recommendations,
        row_count=len(research_rows),
        eligible_count=eligible_count,
        generated_at=generated,
    )

    write_markdown_report(out_dir / "ML_READINESS_REPORT.md", report)
    write_json_report(out_dir / "validation_report.json", report)
    return report
