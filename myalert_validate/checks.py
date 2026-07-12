"""Validation checks for ML readiness."""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any

from myalert_enrich.ohlc import parse_timestamp
from myalert_validate.models import VERDICT_FAIL, VERDICT_PASS, VERDICT_WARNING, CheckResult, ValidationConfig
from myalert_validate.schema import (
    CATEGORICAL_ENUMS,
    JOIN_KEYS,
    LABEL_ENUMS,
    OUTCOME_COLUMNS,
    OUTCOME_LEAKAGE_COLUMNS,
    OUTCOME_NUMERIC_COLUMNS,
    RESEARCH_COLUMNS,
    RESEARCH_NUMERIC_COLUMNS,
    TIMEFRAME_ALIGNMENT_RULES,
)


def _verdict_from_issues(fail: int, warn: int) -> str:
    if fail > 0:
        return VERDICT_FAIL
    if warn > 0:
        return VERDICT_WARNING
    return VERDICT_PASS


def _score_from_verdict(verdict: str) -> float:
    if verdict == VERDICT_PASS:
        return 1.0
    if verdict == VERDICT_WARNING:
        return 0.6
    return 0.0


def _parse_num(value: str | None) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if text == "":
        return None
    try:
        num = float(text)
    except ValueError:
        return None
    if math.isinf(num) or math.isnan(num):
        return None
    return num


def _stream_key(row: dict[str, str]) -> tuple[str, str]:
    return row.get("Symbol", ""), row.get("Timeframe", "")


def _join_key(row: dict[str, str]) -> tuple[str, str, str]:
    return row.get("Symbol", ""), row.get("Timeframe", ""), row.get("Timestamp", "")


def check_schema(columns: list[str], expected: list[str], check_id: str, label: str) -> CheckResult:
    missing = [c for c in expected if c not in columns]
    extra = [c for c in columns if c not in expected]
    order_ok = columns == expected if not missing and not extra else False
    fail = len(missing)
    warn = len(extra) + (0 if order_ok or missing else 1)
    verdict = _verdict_from_issues(1 if missing else 0, warn)
    return CheckResult(
        check_id=check_id,
        name=f"{label} schema validation",
        verdict=verdict,
        score=_score_from_verdict(verdict),
        summary=f"{len(missing)} missing, {len(extra)} extra columns",
        details={"missing": missing, "extra": extra, "order_matches": order_ok, "column_count": len(columns)},
        blockers=[f"Missing required columns: {', '.join(missing)}"] if missing else [],
        fixes=["Regenerate research CSV with current EA header"] if missing else [],
    )


def check_required_columns(columns: list[str], required: list[str], check_id: str) -> CheckResult:
    missing = [c for c in required if c not in columns]
    verdict = VERDICT_FAIL if missing else VERDICT_PASS
    return CheckResult(
        check_id=check_id,
        name="Required columns present",
        verdict=verdict,
        score=_score_from_verdict(verdict),
        summary="All required columns present" if not missing else f"{len(missing)} missing",
        details={"missing": missing},
        blockers=[f"Missing: {', '.join(missing)}"] if missing else [],
    )


def check_data_types(rows: list[dict[str, str]], numeric_cols: list[str], check_id: str) -> CheckResult:
    invalid: dict[str, int] = defaultdict(int)
    for row in rows:
        for col in numeric_cols:
            if col not in row:
                continue
            text = row[col].strip()
            if text == "":
                continue
            if _parse_num(text) is None:
                invalid[col] += 1
    total_invalid = sum(invalid.values())
    verdict = VERDICT_FAIL if total_invalid > 0 else VERDICT_PASS
    return CheckResult(
        check_id=check_id,
        name="Data types (numeric parseable)",
        verdict=verdict,
        score=_score_from_verdict(verdict),
        summary=f"{total_invalid} invalid numeric values",
        details={"invalid_by_column": dict(invalid)},
        blockers=["Fix non-numeric values in feature columns"] if total_invalid else [],
    )


def check_duplicate_keys(rows: list[dict[str, str]], check_id: str) -> CheckResult:
    seen: dict[tuple[str, str, str], int] = defaultdict(int)
    for row in rows:
        seen[_join_key(row)] += 1
    dups = {k: v for k, v in seen.items() if v > 1 and k[0]}
    verdict = VERDICT_FAIL if dups else VERDICT_PASS
    return CheckResult(
        check_id=check_id,
        name="Duplicate keys (Symbol+Timeframe+Timestamp)",
        verdict=verdict,
        score=_score_from_verdict(verdict),
        summary=f"{len(dups)} duplicate keys",
        details={"duplicate_count": len(dups), "examples": list(dups.items())[:5]},
        blockers=["Remove duplicate timestamps before training"] if dups else [],
    )


def check_timestamp_order(rows: list[dict[str, str]], check_id: str) -> CheckResult:
    violations = 0
    by_stream: dict[tuple[str, str], list[datetime]] = defaultdict(list)
    parse_errors = 0
    for row in rows:
        try:
            by_stream[_stream_key(row)].append(parse_timestamp(row["Timestamp"]))
        except (KeyError, ValueError):
            parse_errors += 1
    for stream, times in by_stream.items():
        for i in range(1, len(times)):
            if times[i] < times[i - 1]:
                violations += 1
    fail = parse_errors
    warn = violations
    verdict = _verdict_from_issues(1 if fail else 0, 1 if warn else 0)
    return CheckResult(
        check_id=check_id,
        name="Timestamp chronological order",
        verdict=verdict,
        score=_score_from_verdict(verdict),
        summary=f"{violations} order violations, {parse_errors} parse errors",
        details={"violations": violations, "parse_errors": parse_errors},
        fixes=["Sort rows by Timestamp per stream before split"] if warn else [],
    )


def check_missing_values(
    rows: list[dict[str, str]],
    columns: list[str],
    config: ValidationConfig,
    check_id: str,
) -> CheckResult:
    if not rows:
        return CheckResult(check_id, "Missing values", VERDICT_FAIL, 0.0, "No rows", {})
    missing_frac: dict[str, float] = {}
    for col in columns:
        empty = sum(1 for r in rows if not str(r.get(col, "")).strip())
        missing_frac[col] = empty / len(rows)
    max_frac = max(missing_frac.values()) if missing_frac else 0.0
    worst = sorted(missing_frac.items(), key=lambda x: -x[1])[:10]
    if max_frac >= config.missing_fail_fraction:
        verdict = VERDICT_FAIL
    elif max_frac >= config.missing_warning_fraction:
        verdict = VERDICT_WARNING
    else:
        verdict = VERDICT_PASS
    return CheckResult(
        check_id=check_id,
        name="Missing values",
        verdict=verdict,
        score=_score_from_verdict(verdict),
        summary=f"Max missing fraction {max_frac:.2%}",
        details={"worst_columns": worst, "threshold_warn": config.missing_warning_fraction},
        fixes=["Collect more history or exclude high-missing columns"] if verdict != VERDICT_PASS else [],
    )


def check_invalid_numerics(rows: list[dict[str, str]], columns: list[str], check_id: str) -> CheckResult:
    inf_count = 0
    for row in rows:
        for col in columns:
            text = str(row.get(col, "")).strip()
            if not text:
                continue
            try:
                v = float(text)
            except ValueError:
                continue
            if math.isinf(v) or math.isnan(v):
                inf_count += 1
    verdict = VERDICT_FAIL if inf_count else VERDICT_PASS
    return CheckResult(
        check_id=check_id,
        name="Infinite/invalid numeric values",
        verdict=verdict,
        score=_score_from_verdict(verdict),
        summary=f"{inf_count} inf/nan values",
        details={"count": inf_count},
    )


def check_feature_leakage(research_columns: list[str], check_id: str) -> CheckResult:
    leaked = [c for c in research_columns if c in OUTCOME_LEAKAGE_COLUMNS]
    verdict = VERDICT_FAIL if leaked else VERDICT_PASS
    return CheckResult(
        check_id=check_id,
        name="Feature leakage (outcome columns in research)",
        verdict=verdict,
        score=_score_from_verdict(verdict),
        summary="Clean" if not leaked else f"{len(leaked)} outcome columns in research",
        details={"leaked_columns": leaked},
        blockers=["Remove outcome columns from decision-time research CSV"] if leaked else [],
    )


def check_outcome_leakage(
    research_rows: list[dict[str, str]],
    outcome_rows: list[dict[str, str]] | None,
    check_id: str,
) -> CheckResult:
    if not outcome_rows:
        return CheckResult(
            check_id=check_id,
            name="Outcome leakage (join separation)",
            verdict=VERDICT_WARNING,
            score=0.6,
            summary="No outcomes file provided",
            fixes=["Run myalert_enrich to produce separate outcomes CSV"],
        )
    research_keys = {_join_key(r) for r in research_rows}
    outcome_keys = {_join_key(r) for r in outcome_rows}
    only_outcomes = outcome_keys - research_keys
    only_research = research_keys - outcome_keys
    warn = len(only_outcomes) + len(only_research)
    verdict = VERDICT_WARNING if warn else VERDICT_PASS
    return CheckResult(
        check_id=check_id,
        name="Outcome leakage (join separation)",
        verdict=verdict,
        score=_score_from_verdict(verdict),
        summary=f"{len(only_research)} research-only, {len(only_outcomes)} outcome-only rows",
        details={
            "research_rows": len(research_rows),
            "outcome_rows": len(outcome_rows),
            "matched": len(research_keys & outcome_keys),
            "research_only": len(only_research),
            "outcome_only": len(only_outcomes),
        },
        fixes=["Align research and outcomes timestamps via myalert_enrich"] if warn else [],
    )


def check_class_balance(outcome_rows: list[dict[str, str]] | None, config: ValidationConfig, check_id: str) -> CheckResult:
    if not outcome_rows:
        return CheckResult(check_id, "Class balance", VERDICT_WARNING, 0.6, "No outcomes", {})
    counts = Counter(r.get("Outcome", "") for r in outcome_rows if r.get("Outcome"))
    if not counts:
        return CheckResult(check_id, "Class balance", VERDICT_FAIL, 0.0, "No outcome labels", {})
    min_count = min(counts.values())
    max_count = max(counts.values())
    ratio = min_count / max_count if max_count else 0.0
    small_classes = [k for k, v in counts.items() if v < config.min_per_outcome_class]
    if small_classes:
        verdict = VERDICT_WARNING
    elif ratio < 0.1:
        verdict = VERDICT_WARNING
    else:
        verdict = VERDICT_PASS
    return CheckResult(
        check_id=check_id,
        name="Class balance (Outcome)",
        verdict=verdict,
        score=_score_from_verdict(verdict),
        summary=f"Distribution: {dict(counts)}",
        details={"counts": dict(counts), "min_class_size": min_count, "imbalance_ratio": ratio, "small_classes": small_classes},
        fixes=[f"Collect more samples for classes: {', '.join(small_classes)}"] if small_classes else [],
    )


def _pearson(x: list[float], y: list[float]) -> float | None:
    n = len(x)
    if n < 3:
        return None
    mx = sum(x) / n
    my = sum(y) / n
    num = sum((a - mx) * (b - my) for a, b in zip(x, y))
    den_x = math.sqrt(sum((a - mx) ** 2 for a in x))
    den_y = math.sqrt(sum((b - my) ** 2 for b in y))
    if den_x == 0 or den_y == 0:
        return None
    return num / (den_x * den_y)


def check_feature_variance(rows: list[dict[str, str]], columns: list[str], check_id: str) -> CheckResult:
    zero_var: list[str] = []
    for col in columns:
        values = [_parse_num(r.get(col, "")) for r in rows]
        nums = [v for v in values if v is not None]
        if len(nums) < 2:
            zero_var.append(col)
            continue
        mean = sum(nums) / len(nums)
        var = sum((v - mean) ** 2 for v in nums) / len(nums)
        if var == 0:
            zero_var.append(col)
    verdict = VERDICT_WARNING if zero_var else VERDICT_PASS
    return CheckResult(
        check_id=check_id,
        name="Feature variance",
        verdict=verdict,
        score=_score_from_verdict(verdict),
        summary=f"{len(zero_var)} zero-variance columns",
        details={"zero_variance_columns": zero_var},
        fixes=["Drop constant columns before training"] if zero_var else [],
    )


def check_correlation(
    rows: list[dict[str, str]],
    columns: list[str],
    config: ValidationConfig,
    check_id: str,
) -> CheckResult:
    usable = [c for c in columns if c in (rows[0] if rows else {})]
    series: dict[str, list[float]] = {}
    for col in usable:
        vals = []
        for row in rows:
            v = _parse_num(row.get(col, ""))
            if v is not None:
                vals.append(v)
        if len(vals) >= 3:
            series[col] = vals
    pairs: list[tuple[str, str, float]] = []
    cols = list(series.keys())
    for i, a in enumerate(cols):
        for b in cols[i + 1 :]:
            n = min(len(series[a]), len(series[b]))
            if n < 3:
                continue
            r = _pearson(series[a][:n], series[b][:n])
            if r is not None and abs(r) >= config.correlation_threshold:
                pairs.append((a, b, r))
    verdict = VERDICT_WARNING if pairs else VERDICT_PASS
    return CheckResult(
        check_id=check_id,
        name="Highly correlated features",
        verdict=verdict,
        score=_score_from_verdict(verdict),
        summary=f"{len(pairs)} pairs |r|>={config.correlation_threshold}",
        details={"pairs": [{"a": a, "b": b, "r": round(r, 4)} for a, b, r in pairs[:20]]},
        fixes=["Drop one column from each highly correlated pair"] if pairs else [],
    )


def check_split_readiness(
    rows: list[dict[str, str]],
    config: ValidationConfig,
    check_id: str,
) -> CheckResult:
    by_stream: dict[tuple[str, str], list[datetime]] = defaultdict(list)
    for row in rows:
        try:
            by_stream[_stream_key(row)].append(parse_timestamp(row["Timestamp"]))
        except (KeyError, ValueError):
            pass
    small_streams = []
    for stream, times in by_stream.items():
        times.sort()
        n = len(times)
        if n < config.min_rows_per_stream:
            small_streams.append({"stream": stream, "rows": n})
    train_n = int(config.min_rows_per_stream * config.train_fraction)
    verdict = VERDICT_FAIL if small_streams else VERDICT_PASS
    if not small_streams and train_n < 10:
        verdict = VERDICT_WARNING
    return CheckResult(
        check_id=check_id,
        name="Chronological split readiness",
        verdict=verdict,
        score=_score_from_verdict(verdict),
        summary=f"{len(small_streams)} streams below min rows",
        details={
            "streams": len(by_stream),
            "small_streams": small_streams,
            "recommended_split": {
                "method": "chronological_per_stream",
                "train": config.train_fraction,
                "val": config.val_fraction,
                "test": config.test_fraction,
            },
        },
        fixes=["Collect more bars per symbol/timeframe"] if small_streams else [],
    )


def check_symbol_timeframe_consistency(rows: list[dict[str, str]], check_id: str) -> CheckResult:
    mismatches = []
    for row in rows:
        sym, tf = _stream_key(row)
        if not sym or not tf:
            mismatches.append(_join_key(row))
    verdict = VERDICT_FAIL if mismatches else VERDICT_PASS
    return CheckResult(
        check_id=check_id,
        name="Symbol/timeframe consistency",
        verdict=verdict,
        score=_score_from_verdict(verdict),
        summary=f"{len(mismatches)} rows with empty symbol/timeframe",
        details={"invalid_rows": len(mismatches)},
    )


def check_timezone_consistency(rows: list[dict[str, str]], config: ValidationConfig, check_id: str) -> CheckResult:
    bad = 0
    samples = []
    for row in rows:
        try:
            broker = parse_timestamp(row["Timestamp"])
            utc = parse_timestamp(row["UTC Timestamp"])
            delta_h = abs((broker - utc).total_seconds()) / 3600.0
            if delta_h > config.timezone_offset_tolerance_hours:
                bad += 1
                if len(samples) < 5:
                    samples.append({"Timestamp": row["Timestamp"], "delta_hours": delta_h})
        except (KeyError, ValueError):
            bad += 1
    verdict = VERDICT_WARNING if bad else VERDICT_PASS
    return CheckResult(
        check_id=check_id,
        name="Session/timezone consistency",
        verdict=verdict,
        score=_score_from_verdict(verdict),
        summary=f"{bad} rows with UTC/broker offset anomalies",
        details={"anomaly_count": bad, "samples": samples, "tolerance_hours": config.timezone_offset_tolerance_hours},
    )


def check_incomplete_outcomes(outcome_rows: list[dict[str, str]] | None, check_id: str) -> CheckResult:
    if not outcome_rows:
        return CheckResult(check_id, "Incomplete outcomes (end-of-dataset)", VERDICT_WARNING, 0.6, "No outcomes", {})
    incomplete = sum(
        1
        for r in outcome_rows
        if r.get("Enrichment Status") in ("INSUFFICIENT_FORWARD", "MISSING_OHLC")
        or r.get("Outcome") == "NONE"
    )
    frac = incomplete / len(outcome_rows)
    verdict = VERDICT_WARNING if frac > 0.05 else VERDICT_PASS
    return CheckResult(
        check_id=check_id,
        name="Incomplete outcomes (end-of-dataset)",
        verdict=verdict,
        score=_score_from_verdict(verdict),
        summary=f"{incomplete} rows ({frac:.1%}) incomplete",
        details={"incomplete_count": incomplete, "fraction": frac},
        fixes=["Exclude tail rows with INSUFFICIENT_FORWARD from training eligibility"],
    )


def check_minimum_sample_size(
    outcome_rows: list[dict[str, str]] | None,
    config: ValidationConfig,
    check_id: str,
) -> CheckResult:
    if not outcome_rows:
        return CheckResult(check_id, "Minimum sample size", VERDICT_FAIL, 0.0, "No outcomes", {}, blockers=["Provide outcomes CSV"])
    by_stream: Counter[tuple[str, str]] = Counter()
    by_class: Counter[tuple[str, str, str]] = Counter()
    for row in outcome_rows:
        sk = _stream_key(row)
        by_stream[sk] += 1
        by_class[(sk[0], sk[1], row.get("Outcome", ""))] += 1
    fail_streams = [s for s, n in by_stream.items() if n < config.min_rows_per_stream]
    fail_classes = [k for k, n in by_class.items() if n < config.min_per_outcome_class]
    fail = len(fail_streams)
    warn = len(fail_classes)
    verdict = _verdict_from_issues(1 if fail else 0, 1 if warn else 0)
    return CheckResult(
        check_id=check_id,
        name="Minimum sample size",
        verdict=verdict,
        score=_score_from_verdict(verdict),
        summary=f"{len(fail_streams)} streams under {config.min_rows_per_stream} rows",
        details={
            "streams_under_min": fail_streams,
            "classes_under_min": fail_classes[:20],
            "min_rows_per_stream": config.min_rows_per_stream,
            "min_per_outcome_class": config.min_per_outcome_class,
        },
        blockers=[f"Stream {s} has <{config.min_rows_per_stream} rows" for s in fail_streams[:5]],
        fixes=["Collect more data or lower min thresholds for experimentation"] if fail or warn else [],
    )


_DAY_NAMES = (
    "Sunday",
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
)


def _session_from_utc_hour(hour: int) -> str:
    if 13 <= hour < 17:
        return "London-NY Overlap"
    if 8 <= hour < 13:
        return "London"
    if 17 <= hour < 22:
        return "New York"
    if hour >= 22 or hour < 8:
        return "Asia"
    return "Off-hours"


def _is_timeframe_aligned(ts: datetime, timeframe: str) -> bool:
    rule = TIMEFRAME_ALIGNMENT_RULES.get(timeframe.upper())
    if rule is None:
        return True
    minute_mod, second_required = rule
    if ts.second != second_required:
        return False
    if minute_mod <= 1:
        return True
    return ts.minute % minute_mod == 0


def check_duplicate_record_ids(rows: list[dict[str, str]], check_id: str) -> CheckResult:
    seen: dict[str, int] = defaultdict(int)
    for row in rows:
        rid = row.get("Record ID", "").strip()
        if rid:
            seen[rid] += 1
    dups = {k: v for k, v in seen.items() if v > 1}
    verdict = VERDICT_FAIL if dups else VERDICT_PASS
    return CheckResult(
        check_id=check_id,
        name="Duplicate Record IDs",
        verdict=verdict,
        score=_score_from_verdict(verdict),
        summary=f"{len(dups)} duplicate Record IDs",
        details={"duplicate_count": len(dups), "examples": list(dups.items())[:5]},
        blockers=["Regenerate research CSV — Record ID must be unique per row"] if dups else [],
    )


def check_timeframe_alignment(rows: list[dict[str, str]], check_id: str) -> CheckResult:
    misaligned = 0
    samples: list[dict[str, str]] = []
    for row in rows:
        tf = row.get("Timeframe", "").strip()
        ts_text = row.get("Timestamp", "").strip()
        if not tf or not ts_text:
            continue
        try:
            ts = parse_timestamp(ts_text)
        except ValueError:
            misaligned += 1
            continue
        if not _is_timeframe_aligned(ts, tf):
            misaligned += 1
            if len(samples) < 5:
                samples.append({"Timestamp": ts_text, "Timeframe": tf})
    verdict = VERDICT_FAIL if misaligned else VERDICT_PASS
    return CheckResult(
        check_id=check_id,
        name="Timeframe boundary alignment",
        verdict=verdict,
        score=_score_from_verdict(verdict),
        summary=f"{misaligned} misaligned timestamps",
        details={"misaligned_count": misaligned, "samples": samples},
        blockers=["Upgrade to EA v1.61+ for aligned candle open timestamps"] if misaligned else [],
    )


def check_timestamp_field_consistency(rows: list[dict[str, str]], check_id: str) -> CheckResult:
    violations = 0
    samples: list[dict[str, str]] = []
    for row in rows:
        try:
            broker_ts = row.get("Timestamp", "").strip()
            broker_label = row.get("Broker Timestamp", "").strip()
            utc_ts = parse_timestamp(row["UTC Timestamp"])
            hour_utc = int(row["Hour UTC"])
            day_name = row.get("Day of Week", "").strip()
            session = row.get("Session", "").strip()
        except (KeyError, ValueError):
            violations += 1
            continue

        if broker_ts != broker_label:
            violations += 1
            if len(samples) < 5:
                samples.append({"issue": "broker_mismatch", "Timestamp": broker_ts, "Broker Timestamp": broker_label})
            continue

        if utc_ts.hour != hour_utc:
            violations += 1
            if len(samples) < 5:
                samples.append({"issue": "hour_utc", "UTC Timestamp": row["UTC Timestamp"], "Hour UTC": row["Hour UTC"]})
            continue

        mql_dow = (utc_ts.weekday() + 1) % 7
        expected_day = _DAY_NAMES[mql_dow]
        if day_name != expected_day:
            violations += 1
            if len(samples) < 5:
                samples.append({"issue": "day_of_week", "expected": expected_day, "actual": day_name})
            continue

        expected_session = _session_from_utc_hour(utc_ts.hour)
        if session != expected_session:
            violations += 1
            if len(samples) < 5:
                samples.append({"issue": "session", "expected": expected_session, "actual": session})
    verdict = VERDICT_FAIL if violations else VERDICT_PASS
    return CheckResult(
        check_id=check_id,
        name="Timestamp field consistency (broker/UTC/session)",
        verdict=verdict,
        score=_score_from_verdict(verdict),
        summary=f"{violations} inconsistent timestamp-derived fields",
        details={"violation_count": violations, "samples": samples},
        fixes=["Use EA v1.61+ aligned broker open time for all timing columns"] if violations else [],
    )


def check_categorical_enums(rows: list[dict[str, str]], check_id: str) -> CheckResult:
    invalid: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        for col, allowed in CATEGORICAL_ENUMS.items():
            text = str(row.get(col, "")).strip()
            if text == "":
                continue
            if text not in allowed:
                if len(invalid[col]) < 3:
                    invalid[col].append(text)
    label_invalid: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        for col, allowed in LABEL_ENUMS.items():
            text = str(row.get(col, "")).strip()
            if text == "":
                continue
            if text not in allowed:
                if len(label_invalid[col]) < 3:
                    label_invalid[col].append(text)
    total = sum(len(v) for v in invalid.values()) + sum(len(v) for v in label_invalid.values())
    verdict = VERDICT_FAIL if total else VERDICT_PASS
    return CheckResult(
        check_id=check_id,
        name="Categorical code and label enums",
        verdict=verdict,
        score=_score_from_verdict(verdict),
        summary=f"{total} invalid enum values",
        details={"invalid_numeric": dict(invalid), "invalid_labels": dict(label_invalid)},
        blockers=["Fix categorical values to match docs/MYALERT_CATEGORICAL_CODES.md"] if total else [],
    )
