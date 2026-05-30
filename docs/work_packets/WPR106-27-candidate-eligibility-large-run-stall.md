# WPR106-27 Candidate Eligibility Large-Run Stall

## Summary

Investigate and fix the latest 16-hour `run-research-autopilot` stall. The
running job reached BTCUSDT candidate-pack eligibility and then produced no
candidate-eligibility output directory or logs. The packet is scoped to the
eligibility bridge and candidate-pack gate performance path; generated research
artifacts and runtime DB rows must not be rewritten.

## Allowed Paths

Edit scope:

- `docs/work_packets/WPR106-27-candidate-eligibility-large-run-stall.md`
- `docs/stage_reports/STAGE_R106_CANDIDATE_ELIGIBILITY_LARGE_RUN_STALL_REPORT.md`
- `docs/KNOWN_ISSUES.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_artifacts/candidate_pack.py`
- `src/tradingbotsuite/research_artifacts/__init__.py`
- `src/tradingbotsuite/research_discovery/candidate_pack_bridge.py`
- `tests/research_discovery/test_candidate_pack_bridge.py`

Do not edit generated data, trial JSONs, Parquet ledgers, fixture packs,
runtime SQLite state, live config, runtime mode, sizing, order placement, or
promotion readiness behavior.

## Investigation Plan

1. Confirm the active server process and latest operator job state.
2. Inspect the latest autopilot manifest and operator logs.
3. Identify the step where the output stopped.
4. Measure BTC discovery/cycle evidence sizes.
5. Patch only confirmed P1 performance blockers.
6. Validate on focused tests and real BTC eligibility evaluation.

## Findings

- Latest job:
  `run-research-autopilot-9a4ce549dd1c4ffba99ab54449ef2a0b`.
- Status remained `running` with no error and no finished timestamp.
- Last operator log was `BTCUSDT frozen_entry_exit_lab` skipped at
  `2026-05-29T17:47:55Z`.
- No `candidate_pack_eligibility` output directory existed, proving the stall
  happened before artifact writing.
- BTC exact discovery has 570,240 completed trials and 22,560 interesting
  candidates.
- BTC historical-cycle rankings contain 63 candidates, with zero overlap
  against the BTC discovery candidate IDs.

## Fix Plan

- Keep full trial-record integrity reads for small discovery runs.
- For large completed discovery runs, replace exhaustive trial JSON rereads
  with:
  - manifest/run-state count checks;
  - ledger row count and completed-trial ID coverage checks;
  - vectorized ledger `record_sha256` versus run-state hash checks;
  - deterministic sampled trial-record checks.
- Build one reusable historical-cycle gate context per eligibility run so
  unranked discovery candidates are blocked from cached ranking membership
  evidence instead of reloading the same cycle evidence per row.
- Preserve fail-closed behavior for missing paths, bad schemas, invalid JSON,
  hash mismatches, and sampled record mismatches.

## Acceptance Criteria

- The real BTCUSDT candidate eligibility evaluator finishes quickly on current
  artifacts when run from the checkout with `PYTHONPATH=src`.
- No candidate pack is written.
- No promotion or live-readiness claim is introduced.
- Small-run tamper coverage still performs full trial-record validation.
- Large-run coverage proves exhaustive per-trial reads are sampled instead of
  repeated over every completed trial.
