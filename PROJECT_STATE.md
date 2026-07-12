# PROJECT_STATE

**Project:** Broker Data Collector  
**Version:** 1.8.0 (EA 1.60 + Phase F/G Python tools)  
**Status:** MyAlert Phase G complete (ML readiness validation)  
**Last updated:** 2026-07-13

## What exists

| Artifact | Status |
|----------|--------|
| `BrokerDataCollector.mq5` | Done — v1.60, full MyAlert research export (59 cols) |
| `myalert_enrich/` | Done — Phase F outcome enrichment |
| `myalert_validate/` | Done — Phase G ML readiness validation |
| `tests/` | Done — 16 unit/integration tests |
| `README.md` | Done — EA + MyAlert Phases C–G |

## Python pipeline (post-collection)

1. **Collect** — EA writes research CSV + Raw OHLC (decision-time only in research)
2. **Enrich** — `python -m myalert_enrich` → outcomes CSV
3. **Validate** — `python -m myalert_validate` → ML readiness report + eligibility flags

## Safety posture

- EA unchanged since Phase E
- No future-derived fields in research CSV
- No source file modification by Python tools
- No random splits; chronological ML split only

## Next recommended steps

MyAlert extension phases A–G are complete. See `OPEN_TASKS.md` for general EA improvements.
