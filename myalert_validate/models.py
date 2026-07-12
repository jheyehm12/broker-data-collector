"""Data models for ML readiness validation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


VERDICT_PASS = "PASS"
VERDICT_WARNING = "WARNING"
VERDICT_FAIL = "FAIL"


@dataclass
class ValidationConfig:
    min_rows_per_stream: int = 100
    min_per_outcome_class: int = 20
    min_eligible_fraction: float = 0.70
    correlation_threshold: float = 0.95
    missing_warning_fraction: float = 0.05
    missing_fail_fraction: float = 0.20
    timezone_offset_tolerance_hours: int = 14
    train_fraction: float = 0.70
    val_fraction: float = 0.15
    test_fraction: float = 0.15


@dataclass
class CheckResult:
    check_id: str
    name: str
    verdict: str
    score: float
    summary: str
    details: dict[str, Any] = field(default_factory=dict)
    blockers: list[str] = field(default_factory=list)
    fixes: list[str] = field(default_factory=list)


@dataclass
class ValidationReport:
    research_path: str
    outcomes_path: str | None
    checks: list[CheckResult]
    overall_score: float
    overall_verdict: str
    blockers: list[str]
    recommended_fixes: list[str]
    recommendations: dict[str, Any]
    row_count: int
    eligible_count: int
    generated_at: str
