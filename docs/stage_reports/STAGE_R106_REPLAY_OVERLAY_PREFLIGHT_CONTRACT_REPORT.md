# Stage R106 Replay Overlay Preflight Contract Report

Work packet:
`docs/work_packets/WPR106-45-replay-overlay-preflight-contract.md`

Date: 2026-05-31

## Summary

WPR106-45 codifies the WPR106-44 exact replay-overlay preflight as reusable
research-only code. The preflight reads WPR106-31 replay specs and replay
discovery manifests, checks every replay lead against the current historical
cycle strategy/plugin contract, verifies KNN prediction and manifest boundary
evidence, and emits explicit representability rows before any
candidate-scoped overlay cycle spec can be trusted.

This packet does not expand strategy parameter domains, add `1h` support to
`hmm_knn_local_analog_filter_v2`, run historical-cycle backtests, write
candidate packs, or add any live/paper/runtime/order-placement behavior.

## Source Changes

- `src/tradingbotsuite/research_discovery/replay_overlay_preflight.py`
  - Adds `preflight_replay_overlay_cycle_specs()`.
  - Adds `write_replay_overlay_cycle_preflight_artifacts()`.
  - Adds `validate_replay_overlay_cycle_preflight_manifest()`.
  - Checks plugin holding-window and feature-set support.
  - Checks replay parameters against current strategy metadata allowed values.
  - Requires prediction artifact existence, KNN manifest existence, research
    boundary flags, split-safety status, prediction path match, and prediction
    SHA match.
- `src/tradingbotsuite/research_discovery/__init__.py`
  - Exports the reusable preflight API.
- `tests/research_discovery/test_replay_overlay_preflight.py`
  - Covers exact representable lead handling.
  - Covers WPR106-31-style `1h` and out-of-domain threshold rejection.
  - Covers prediction SHA mismatch, missing prediction, unsafe manifest flags,
    manifest validation, no candidate-pack emission, and overwrite refusal.

## Empirical Rerun

The reusable preflight was run against the actual WPR106-31 BTCUSDT and
ETHUSDT replay artifacts.

Generated under:
`data/research/operator_runs/wpr106_45_replay_overlay_preflight_contract/`

- `replay_overlay_cycle_preflight_summary.json`
- `combined_replay_overlay_cycle_preflight_rows.parquet`
- `btcusdt/replay_overlay_cycle_preflight_manifest.json`
- `btcusdt/replay_overlay_cycle_preflight_rows.parquet`
- `ethusdt/replay_overlay_cycle_preflight_manifest.json`
- `ethusdt/replay_overlay_cycle_preflight_rows.parquet`

Observed counts:

- Total replay leads checked: 48
- BTCUSDT replay leads checked: 24
- ETHUSDT replay leads checked: 24
- Prediction Parquets found: 48
- KNN manifests found: 48
- Exact replay candidates representable by current historical-cycle contract:
  0
- Unrepresentable exact replay candidates: 48
- Overlay cycle specs emitted: 0
- Candidate packs emitted: 0

The reusable code reproduces the WPR106-44 conclusion: exact WPR106-31 replay
leads are not representable by the current `hmm_knn_local_analog_filter_v2`
historical-cycle candidate contract. Zero representable candidates remains
valid research evidence.

## Validation

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_replay_overlay_preflight.py -q
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
git diff --check
```

Observed:

- compileall passed.
- replay overlay preflight tests: 5 passed.
- research-discovery suite: 231 passed.
- contracts suite: 440 passed.
- `git diff --check` passed with CRLF warnings only.

## Candidate Status

No candidate-ready claim exists. No overlay cycle spec was emitted. No
candidate pack was produced. No promotion-ready artifact exists.

## Next Work

Open a decision packet before any empirical overlay run:

- Option A: add explicit, tested historical-cycle support for exact replay lead
  parameter domains and `1h` KNN overlay horizons without weakening gates; or
- Option B: run a separately labeled approximate-current-domain overlay
  experiment that preserves original and projected parameters and does not
  claim exact WPR106-31 replay evidence.

Do not silently substitute current-domain defaults for replayed values.
