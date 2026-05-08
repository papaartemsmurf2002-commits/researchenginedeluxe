# Stage R82 Candidate Pack Bridge Report

Date: 2026-05-09
Branch: `research/v3-experimental-engine`
Packet: `docs/work_packets/WPR82-01-candidate-pack-bridge.md`

## Summary

WPR82 added a research-only discovery candidate-pack eligibility bridge. The
bridge evaluates completed discovery-run candidates against the existing
historical-cycle research candidate-pack validator and writes audit artifacts
only. It does not write candidate packs, does not alter historical-cycle gates,
and does not create promotion or live readiness evidence.

## Implemented

- Added `src/tradingbotsuite/research_discovery/candidate_pack_bridge.py`.
- The bridge validates discovery manifest boundary flags, completed run state,
  trial-record hash integrity, and discovery ledgers before evaluating
  candidates.
- Candidates must come from `interesting_candidates`; candidates also present in
  blocked or filter-blocker ledgers fail closed.
- Historical-cycle eligibility delegates to
  `evaluate_research_candidate_gate`, preserving fixture provenance, split,
  cost-stress, stability, ablation, backtest, side, regime, and lower-timeframe
  evidence requirements.
- The bridge writes:
  - `candidate_pack_eligibility_manifest.json`
  - `candidate_pack_eligibility.parquet`
  - `candidate_pack_bridge_rejections.md`
- Added `evaluate-discovery-candidate-pack-eligibility` CLI as an audit command.
- Registered the CLI in `RESEARCH_COMMANDS` so live preflight rejects it.
- Added `configs/discovery/discovery_candidate_pack_bridge_v4.json` as a
  checked research-only config stub.

## Boundary Decision

The bridge intentionally does not call `write_research_candidate_pack`. Candidate
pack writing remains owned by historical-cycle output generation. Bridge
artifacts always record:

- `research_only: true`
- `observe_only: true`
- `promotion_ready: false`
- `candidate_pack_written: false`
- empty `candidate_pack_paths`

## Validation

Passed:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_candidate_pack_bridge.py -q
$env:PYTHONPATH='src'; python -m pytest tests\live\test_preflight.py -q
$env:PYTHONPATH='src'; python -m pytest tests\research_artifacts\test_candidate_pack.py -q
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Results:

- `tests/research_discovery/test_candidate_pack_bridge.py`: 7 passed.
- `tests/live/test_preflight.py`: 30 passed.
- `tests/research_artifacts/test_candidate_pack.py`: 35 passed.
- `tests/research_discovery`: 60 passed.
- `tests/contracts`: 372 passed.

## Known Issues

No new P0/P1 issues were discovered.
