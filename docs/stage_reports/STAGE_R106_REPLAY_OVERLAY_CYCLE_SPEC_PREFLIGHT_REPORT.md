# Stage R106 Replay Overlay Cycle Spec Preflight Report

Work packet:
`docs/work_packets/WPR106-44-replay-overlay-cycle-spec-preflight.md`

Date: 2026-05-31

## Summary

WPR106-44 preflighted the 48 WPR106-31 replayed KNN leads for exact
candidate-scoped historical-cycle overlay execution. The preflight accounted
for every BTCUSDT and ETHUSDT replay lead and verified all replayed prediction
Parquets and KNN manifests exist.

The exact replayed lead parameters are not representable by the current
historical-cycle `hmm_knn_local_analog_filter_v2` candidate contract. Therefore
no historical-cycle overlay specs were emitted. This is a valid research
rejection result, not a gate failure or code failure.

## Artifacts

Generated under:
`data/research/operator_runs/wpr106_44_replay_overlay_cycle_preflight/`

- `replay_overlay_cycle_preflight_summary.json`
- `combined_replay_overlay_cycle_preflight_rows.parquet`
- `btcusdt/replay_overlay_cycle_preflight_manifest.json`
- `btcusdt/replay_overlay_cycle_preflight_rows.parquet`
- `ethusdt/replay_overlay_cycle_preflight_manifest.json`
- `ethusdt/replay_overlay_cycle_preflight_rows.parquet`

## Counts

- Total replay leads checked: 48
- BTCUSDT replay leads checked: 24
- ETHUSDT replay leads checked: 24
- Prediction Parquets found: 48
- KNN manifests found: 48
- Exact replay candidates representable by current historical-cycle contract: 0
- Overlay cycle specs emitted: 0
- Candidate packs emitted: 0

## Main Rejection Reasons

All 48 replay leads use `label_horizon: 1h`, while
`hmm_knn_local_analog_filter_v2` historical-cycle candidates allow `4h`, `12h`,
`24h`, and `72h`.

All 48 replay leads use `event_spacing_bars: 4`, while the current
historical-cycle strategy domain starts at larger spacing values for this
strategy.

Many replayed KNN thresholds are also outside the current historical-cycle
strategy metadata domain, including lower `min_neighbor_count`,
`min_neighbor_agreement`, `min_neighbor_distance_quality`, `min_vote_margin`,
and `probability_threshold` values.

## Research Boundary

No source code was changed in WPR106-44. No candidate gates were weakened. No
strategy parameter domains were expanded. No live, paper, runtime,
order-placement, promotion, or candidate-pack behavior was added. No historical
cycle was run from approximate replay parameters.

## Validation

This packet used the already passing WPR106-42/WPR106-43 validation baseline:

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
$env:PYTHONPATH='src'; python -m pytest tests\research_artifacts -q
$env:PYTHONPATH='src'; python -m pytest tests\backtesting -q
$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_feature_alignment.py -q
git diff --check
```

Observed in the current session:

- compileall passed;
- contracts: 440 passed;
- research-discovery: 226 passed after WPR106-43;
- research-artifacts: 37 passed;
- backtesting: 105 passed, 1 skipped;
- feature alignment: 4 passed;
- `git diff --check` passed with CRLF warnings only before WPR106-44 docs and
  artifact writes.

## Candidate Status

No candidate-ready claim exists. No candidate pack was produced. Zero
representable exact replay candidates is valid evidence.

## Next Work

Open a decision packet before any empirical overlay run:

- Option A: add explicit, tested historical-cycle support for exact replay lead
  parameter domains and `1h` KNN overlay horizons without weakening gates; or
- Option B: run a separately labeled approximate-current-domain overlay
  experiment that does not claim to be exact WPR106-31 replay evidence.

Do not silently substitute current-domain defaults for replayed values.
