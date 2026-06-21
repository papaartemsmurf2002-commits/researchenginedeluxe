# V2 Run Artifact Contract

Status: v2 Phase 16 run artifact contract
Audit IDs: `V2-AUD-BTENG-001`, `V2-AUD-BTENG-002`, `V2-AUD-COST-001`

## Purpose

Run artifacts make strategy trials reproducible and auditable.

## Schema Names

- `RunManifest`
- `RunArtifactRef`
- `BacktestMetrics`
- `BacktestRunResult`

## Required Artifacts

- `run_manifest.json`
- `strategy_spec.json`
- `params.json`
- `data_manifest.json`
- `validation_manifest.json`
- `cost_manifest.json`
- `metrics.json`
- `equity_curve.parquet`
- `daily_returns.parquet`
- `trades.parquet`
- `positions.parquet`
- `cost_stress.parquet`
- `per_instrument_metrics.parquet`
- `fold_metrics.parquet`
- `logs/log.txt`

## Required Manifest Fields

Run manifests include run ID, schema version, code/version metadata, strategy
spec hash, params hash, archive snapshot ID, universe snapshot ID, validation
policy ID, cost model ID/hash, artifact hashes, start/end timestamps, status,
and the research-only boundary.

Phase 11 `run_manifest.json` uses `schema_version: run_manifest_v1` and must
also include experiment ID, trial index, agent/user, engine lane, strategy lane,
git SHA, environment hash, strategy ID/version/hash, data manifest ID/hash,
validation manifest hash, cost manifest hash, universe mode, venue scope,
instrument count, timeframe, usable months, lockbox policy/window, coverage
floor, validation status, missing-data policy, price basis, optional failure
reason, metrics for successful runs, cost sensitivity artifacts, and
`RunArtifactRef` entries for all required artifacts.

`cost_manifest.json` uses `schema_version: cost_manifest_v1` and records the
cost model config/hash plus fee, funding, spread, slippage, impact, capacity,
stress matrix, and cost sensitivity. `cost_stress.parquet` records `base`,
`stress_2x`, and `stress_3x` rows for successful vectorized runs and is still
written as an empty required artifact for failed or blocked runs.

Successful Phase 16 event-driven skeleton runs use the same artifact set and
record `engine_lane: event_driven`. They are fixture-only research artifacts
and do not imply live/paper/order/sizing readiness or realistic queue fills.

Failed or blocked runs must still write the required artifact files. Their
manifest records failed validation status and a clear failure reason, and their
metrics artifact must remain research-only and non-promotable.

## Forbidden

- Missing boundary metadata.
- Promotion-ready manifests.
- Missing artifact hashes.
- Successful manifests without metrics.
- Failed manifests without failure reason.
