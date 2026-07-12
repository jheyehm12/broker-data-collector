"""Aggregate scores and verdicts."""

from __future__ import annotations

from myalert_validate.models import VERDICT_FAIL, VERDICT_PASS, VERDICT_WARNING, CheckResult, ValidationConfig


def compute_overall(checks: list[CheckResult], config: ValidationConfig) -> tuple[float, str, list[str], list[str]]:
    if not checks:
        return 0.0, VERDICT_FAIL, ["No checks ran"], []

    weights = {
        "research_schema": 2.0,
        "outcomes_schema": 1.5,
        "required_columns": 2.0,
        "duplicate_keys": 2.0,
        "feature_leakage": 2.5,
        "outcome_leakage": 2.0,
        "minimum_sample_size": 2.0,
    }
    total_w = 0.0
    weighted = 0.0
    for check in checks:
        w = weights.get(check.check_id, 1.0)
        total_w += w
        weighted += check.score * w

    score = (weighted / total_w) * 100.0 if total_w else 0.0

    blockers: list[str] = []
    fixes: list[str] = []
    has_fail = False
    has_warn = False
    for check in checks:
        if check.verdict == VERDICT_FAIL:
            has_fail = True
        elif check.verdict == VERDICT_WARNING:
            has_warn = True
        blockers.extend(check.blockers)
        fixes.extend(check.fixes)

    if has_fail:
        verdict = VERDICT_FAIL
    elif has_warn:
        verdict = VERDICT_WARNING
    else:
        verdict = VERDICT_PASS

    return round(score, 1), verdict, list(dict.fromkeys(blockers)), list(dict.fromkeys(fixes))
