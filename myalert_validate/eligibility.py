"""Per-row training eligibility flags (separate output file)."""

from __future__ import annotations

import csv
from pathlib import Path

from myalert_validate.schema import JOIN_KEYS

ELIGIBILITY_HEADER = [
    *JOIN_KEYS,
    "Eligible For Training",
    "Eligibility Reasons",
    "Research Row Index",
    "Outcome Matched",
    "Enrichment Status",
    "Outcome",
]


def build_eligibility_rows(
    research_rows: list[dict[str, str]],
    outcomes_by_key: dict[tuple[str, str, str], dict[str, str]],
    min_forward_bars: int | None = None,
) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    for idx, row in enumerate(research_rows):
        key = (row.get("Symbol", ""), row.get("Timeframe", ""), row.get("Timestamp", ""))
        outcome = outcomes_by_key.get(key)
        reasons: list[str] = []
        eligible = 1

        if not key[0] or not key[1] or not key[2]:
            eligible = 0
            reasons.append("MISSING_KEY")

        if outcome is None:
            eligible = 0
            reasons.append("NO_OUTCOME_MATCH")
        else:
            status = outcome.get("Enrichment Status", "")
            if status == "MISSING_OHLC":
                eligible = 0
                reasons.append("MISSING_OHLC")
            if status == "INSUFFICIENT_FORWARD":
                eligible = 0
                reasons.append("INSUFFICIENT_FORWARD")
            if status == "SKIP_NEUTRAL":
                eligible = 0
                reasons.append("SKIP_NEUTRAL")
            if status == "INVALID_ROW":
                eligible = 0
                reasons.append("INVALID_ROW")
            if outcome.get("Outcome") == "NONE":
                reasons.append("OUTCOME_NONE")
            if min_forward_bars is not None:
                try:
                    avail = int(outcome.get("Forward Bars Available", "0"))
                    if avail < min_forward_bars:
                        eligible = 0
                        reasons.append("SHORT_FORWARD_WINDOW")
                except ValueError:
                    eligible = 0
                    reasons.append("BAD_FORWARD_BARS")

        # Critical feature empties (Phase D/E gate)
        for col in ("Direction", "ATR14", "Close"):
            if not str(row.get(col, "")).strip():
                eligible = 0
                reasons.append(f"MISSING_{col.upper().replace(' ', '_')}")

        results.append(
            {
                "Symbol": key[0],
                "Timeframe": key[1],
                "Timestamp": key[2],
                "Eligible For Training": str(eligible),
                "Eligibility Reasons": ";".join(reasons) if reasons else "OK",
                "Research Row Index": str(idx),
                "Outcome Matched": "1" if outcome else "0",
                "Enrichment Status": outcome.get("Enrichment Status", "") if outcome else "",
                "Outcome": outcome.get("Outcome", "") if outcome else "",
            }
        )
    return results


def write_eligibility_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=ELIGIBILITY_HEADER)
        writer.writeheader()
        writer.writerows(rows)
