# PROJECT_STATE

**Project:** Broker Data Collector  
**Version:** 1.8.1 (EA 1.61 + Phase F/G Python tools)  
**Status:** MyAlert research CSV hardened for VPS deployment  
**Last updated:** 2026-07-13

## What exists

| Artifact | Status |
|----------|--------|
| `BrokerDataCollector.mq5` | Done — v1.61, MyAlert research export (68 cols) |
| `docs/MYALERT_CATEGORICAL_CODES.md` | Done — categorical code reference |
| `myalert_enrich/` | Done — Phase F outcome enrichment |
| `myalert_validate/` | Done — Phase G ML readiness + v1.61 hardening checks |
| `tests/` | Done — 17 unit/integration tests |
| `README.md` | Done — EA + MyAlert Phases C–G + hardening |

## MyAlert research CSV (v1.61)

| Item | Value |
|------|-------|
| Core columns | 59 (unchanged order) |
| Extension columns | 9 appended (Record ID + 8 labels) |
| Total columns | 68 |
| Timestamp source | Aligned closed-candle broker open |
| Record ID | `SYMBOL_TF_YYYYMMDDHHMMSS` |

## Python pipeline (post-collection)

1. **Collect** — EA writes research CSV + Raw OHLC (decision-time only in research)
2. **Enrich** — `python -m myalert_enrich` → outcomes CSV
3. **Validate** — `python -m myalert_validate` → ML readiness report + eligibility flags

## Safety posture

- Raw/CompetitionLab unchanged when MyAlert flag is off
- No future-derived fields in research CSV
- No source file modification by Python tools
- No random splits; chronological ML split only
- Archive pre-v1.61 research CSVs before VPS upgrade (header change 59 → 68)

## Next recommended steps

MyAlert extension phases A–G and VPS hardening are complete. See `OPEN_TASKS.md` for general EA improvements.
