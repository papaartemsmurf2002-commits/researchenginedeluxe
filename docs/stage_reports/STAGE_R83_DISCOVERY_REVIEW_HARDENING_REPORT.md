# Stage R83 Discovery Review Hardening Report

Date: 2026-05-09
Branch: `research/v3-experimental-engine`
Packet: `docs/work_packets/WPR83-01-discovery-review-hardening.md`

## Summary

R83 fixed crosscheck findings in the V4 discovery implementation. The changes
preserve the research-only boundary while tightening split safety, artifact
integrity, resume correctness, operator path validation, and live-command
rejection coverage.

## Implemented

- Discovery candidate-pack bridge now verifies completed run state against the
  manifest, expected trial count, immutable trial records, and exact ledgers.
- Bridge eligibility fails closed for fabricated ledger rows, edited incomplete
  run state, live-adjacent trial fields, missing trial records, and existing
  audit artifacts.
- KNN study training rows now drop the label-horizon tail before validation so
  forward labels cannot cross into validation/OOS rows.
- Selected WT3D feature-column sets now require their non-WT comparator to be
  selected and enabled.
- Discovery resume now refuses state that references missing completed trial
  records or missing state hashes.
- Discovery runner now writes snapshots when the configured snapshot interval
  elapses between completed trials, not only at batch boundaries.
- HMM/KNN/bridge artifact writers refuse fixed-path overwrites and use temp-file
  replacement for parquet/text outputs.
- `run-discovery` is registered as a research command and rejected by live
  preflight.
- Operator train/calibrate/replay artifact jobs now require file paths under the
  configured research output directory.

## Boundary Decision

No live, paper, shadow, testnet, promotion, sizing, or order-placement behavior
was added. Discovery candidate-pack bridge artifacts remain:

- `research_only: true`
- `observe_only: true`
- `promotion_ready: false`
- `candidate_pack_written: false`

Candidate-pack writing remains owned by historical-cycle artifact generation.

## Validation

Passed:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
$env:PYTHONPATH='src'; python -m pytest tests\live\test_preflight.py -q
$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py -q
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
$env:PYTHONPATH='src'; python -m pytest tests\research_artifacts\test_candidate_pack.py -q
```

Results:

- `tests/research_discovery`: 71 passed.
- `tests/live/test_preflight.py`: 32 passed.
- `tests/tradingbotsuite/test_operator_ui.py`: 35 passed.
- `tests/contracts`: 372 passed.
- `tests/research_artifacts/test_candidate_pack.py`: 35 passed.

## Known Issues

No new P0/P1 issues remain open after this crosscheck.
