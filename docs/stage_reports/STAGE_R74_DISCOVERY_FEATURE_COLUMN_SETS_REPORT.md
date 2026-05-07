# Stage R74 Discovery Feature-Column Sets Report

Date: 2026-05-07
Owner: Codex Research Agent
Work packet: `docs/work_packets/WPR74-01-discovery-feature-column-sets.md`

## Scope

WPR74 adds the first bounded discovery-side KNN feature-column set contract.
It intentionally does not add new feature formulas, HMM materialization, KNN
distance computation, optimizer behavior, UI behavior, candidate-pack bridge
behavior, promotion readiness, live execution, sizing, or order placement.

## Changes

- Added `src/tradingbotsuite/research_discovery/feature_sets.py`:
  - Defines feature-column set records separate from registered `features_*`
    manifests.
  - Validates selected columns against existing registered feature manifests.
  - Enforces safe IDs, no duplicate columns, enabled dimension caps, no-WT
    comparator requirements for WT3D sets, disabled-set reasons, selected-set
    fail-closed behavior, research-only flags, and deterministic manifest
    hashes.
- Added `configs/discovery/feature_column_sets_v4.json`:
  - `price_trend_vol`
  - `compact_wt3d_base`
  - `alternative_non_wt_price_state`
  - `perp_feature_addition_smoke`
  - `liquidation_feature_addition_smoke`
  - disabled `future_ntri_entropy_additions`
- Updated `configs/discovery/quick_smoke_btcusdt_v4.json` to select the first
  bounded smoke column sets.
- Updated discovery specs and run manifests to record configured
  feature-column set path, selected IDs, manifest hash, selected registered
  feature-set IDs, WT/non-WT evidence, dimension evidence, and research-only
  flags.
- Added focused tests for config validity, unknown columns, excessive
  dimensions, WT comparator requirements, hash mismatch, disabled selected
  sets, and run-manifest evidence propagation.

## Evidence

The feature-column sets are research-only configuration for future KNN studies.
They do not materialize new columns and do not make performance claims.

Generated discovery run manifests still record:

- `research_only: true`
- `observe_only: true`
- `promotion_ready: false`
- `candidate_pack_written: false`
- `order_placement_used: false`
- `runtime_mode_changed: false`

## Validation

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
git diff --check
```

Results:

- Compile passed.
- Contracts passed: 368 passed.
- Discovery tests passed: 20 passed.
- `git diff --check` passed.

## Limitations

WPR74 selects existing columns only. Future packets must add and hand-test any
new formulas such as NTRI, entropy, autocorrelation, or HVR before those fields
can become enabled discovery columns.
