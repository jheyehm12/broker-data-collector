"""Report writers for Phase G validation."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from myalert_validate.models import ValidationReport


def write_json_report(path: Path, report: ValidationReport) -> None:
    payload: dict[str, Any] = {
        "generated_at": report.generated_at,
        "research_path": report.research_path,
        "outcomes_path": report.outcomes_path,
        "overall_score": report.overall_score,
        "overall_verdict": report.overall_verdict,
        "row_count": report.row_count,
        "eligible_count": report.eligible_count,
        "blockers": report.blockers,
        "recommended_fixes": report.recommended_fixes,
        "recommendations": report.recommendations,
        "checks": [
            {
                "check_id": c.check_id,
                "name": c.name,
                "verdict": c.verdict,
                "score": c.score,
                "summary": c.summary,
                "details": c.details,
                "blockers": c.blockers,
                "fixes": c.fixes,
            }
            for c in report.checks
        ],
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_markdown_report(path: Path, report: ValidationReport) -> None:
    lines = [
        "# ML Readiness Report",
        "",
        f"**Generated:** {report.generated_at}",
        f"**Research file:** `{report.research_path}`",
        f"**Outcomes file:** `{report.outcomes_path or 'not provided'}`",
        "",
        f"## Overall verdict: **{report.overall_verdict}**",
        "",
        f"**Readiness score:** {report.overall_score}/100",
        f"**Research rows:** {report.row_count}",
        f"**Eligible for training:** {report.eligible_count} ({report.eligible_count / report.row_count:.1%} of rows)"
        if report.row_count
        else "**Eligible for training:** 0",
        "",
    ]

    if report.blockers:
        lines.append("## Blockers")
        lines.append("")
        for b in report.blockers:
            lines.append(f"- {b}")
        lines.append("")

    if report.recommended_fixes:
        lines.append("## Recommended fixes")
        lines.append("")
        for f in report.recommended_fixes:
            lines.append(f"- {f}")
        lines.append("")

    lines.extend(["## Check results", "", "| Check | Verdict | Score | Summary |", "|-------|---------|-------|---------|"])
    for c in report.checks:
        lines.append(f"| {c.name} | {c.verdict} | {c.score:.2f} | {c.summary} |")
    lines.append("")

    rec = report.recommendations
    lines.extend(
        [
            "## Recommended feature list",
            "",
            ", ".join(f"`{c}`" for c in rec["recommended_features"][:20]),
            f"... ({len(rec['recommended_features'])} total)",
            "",
            "## Columns to exclude from training",
            "",
            ", ".join(f"`{c}`" for c in rec["exclude_from_training"][:15]),
            "...",
            "",
            "## Suggested target labels",
            "",
            f"- **Classification primary:** `{rec['suggested_targets']['classification']['primary']}`",
            f"- **Regression primary:** `{rec['suggested_targets']['regression']['primary']}`",
            "",
            "## Chronological split method",
            "",
            f"- Method: `{rec['chronological_split']['method']}`",
            f"- Train / val / test: {rec['chronological_split']['train_fraction']:.0%} / "
            f"{rec['chronological_split']['validation_fraction']:.0%} / "
            f"{rec['chronological_split']['test_fraction']:.0%}",
            "- **No random shuffle**",
            "",
            "## Baseline model suggestions",
            "",
        ]
    )
    for item in rec["baseline_models"]:
        lines.append(f"- **{item['task']}:** {', '.join(item['models'])}")
    lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
