# WPR50-01 Perp Context V2 Feature Pack

Owner: Codex Research Agent
Status: closed
Stage: R50 perp context v2 feature pack
Date opened: 2026-05-05
Date closed: 2026-05-05

## Goal

Add `features_perp_context_v2` as a registered feature set built from current durable context families.

## Allowed Paths

```text
src/tradingbotsuite/features/registry.py
src/tradingbotsuite/features/packs.py
src/tradingbotsuite/features/builders.py
src/tradingbotsuite/features/cache.py
configs/features/features_perp_context_v2.json
tests/features/
tests/contracts/test_feature_contracts.py
docs/work_packets/WPR50-01-perp-context-v2-feature-pack.md
docs/stage_reports/STAGE_R50_PERP_CONTEXT_V2_FEATURE_PACK_REPORT.md
docs/ORCHESTRATOR_STAGE_LEDGER.md
docs/KNOWN_ISSUES.md
```

## Constraints

- Keep current cycle spec shape.
- Use repo-style feature ID `features_perp_context_v2`.
- Use only current durable context families: `funding_rate`, `premium_index`, `open_interest`, and optional `agg_trade`.
- Do not require liquidation, L2, cross-exchange, ETH cross-asset, or multi-symbol behavior.
- Every context join must remain completed-bar/backward-as-of aligned.
- Missing optional context must be `NaN` plus quality/missingness flags, not silent zero.
- Feature-cache identity must include context-family hashes through existing cache inputs.
- Preserve research-only boundaries and live import boundaries.
- `src/tradingbotsuite/features/packs.py` is included because current feature-pack computation dispatch lives there.

## Required Initial Columns

```text
perp_mark_index_basis
perp_premium
perp_premium_z_7d
perp_premium_slope_8h
perp_last_funding_rate
perp_funding_z_7d
perp_funding_momentum
cal_time_since_last_funding_h
cal_time_to_next_funding_h
oi_notional
oi_delta_1h
oi_delta_z_7d
oi_volume_ratio
flow_buy_sell_ratio
flow_signed_taker_notional
flow_signed_taker_z_7d
quality_context_missing_count
quality_has_funding_gap
quality_has_oi_gap
quality_has_premium_gap
quality_provider_backed_all_required
quality_latest_window_context_only
```

## Validation Plan

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_feature_contracts.py tests\features -q
```

## Close Evidence

Closed in `docs/stage_reports/STAGE_R50_PERP_CONTEXT_V2_FEATURE_PACK_REPORT.md`.

Validation:

```powershell
python -m compileall -q src\tradingbotsuite\features
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_feature_contracts.py tests\features -q
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
$env:PYTHONPATH='src'; python -m pytest tests\historical\test_full_cycle_synthetic.py tests\historical\test_full_cycle_local_fixture_pack.py -q
```

Results: feature compile passed; focused feature tests passed with 23 tests; full compile passed; full contract suite passed with 105 tests; selected historical cycle tests passed with 20 tests.
