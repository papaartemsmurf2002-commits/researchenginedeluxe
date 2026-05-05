# Stage R43 Provider WT3D Full-Context Ablation Cycle Report

Date: 2026-05-05
Owner: Codex Research Agent
Work packet: `docs/work_packets/WPR43-01-provider-wt3d-full-context-ablation-cycle.md`
Status: closed

## Scope

WPR43 ran a non-synthetic provider-backed historical cycle to compare price/trend, full-context no-WT, and full-context WT3D feature sets on the WPR41 latest-month BTCUSDT context fixture.

No legacy TradingView exports, Pine files, parity files, synthetic input, live execution, paper/shadow/testnet/canary flows, order placement, promotion, or candidate acceptance were used.

The initial draft spec included `features_price_trend_vol_wt3d` with `trend_following_v1`. That failed before outputs because `trend_following_v1` does not support the price-WT3D feature set. The packet was tightened to the supported full-context WT3D/no-WT comparison plus the price/trend baseline.

## Cycle Evidence

- Cycle spec: `data/research/historical_cycles/btcusdt_context_provider_wt3d_ablation_cycle/specs/btcusdt_context_provider_wt3d_ablation_cycle.json`
- Cycle manifest: `data/research/historical_cycles/btcusdt_context_provider_wt3d_ablation_cycle/run/research_cycle_manifest.json`
- Cycle manifest SHA-256: `a5917ec32ac7ae2a852d6ad369fc58934d6611916c4bd277f334e09cd98e8567`
- Data source: `historical_fixture_pack`
- Fixture ID: `btcusdt-context-provider-latest-month-v1`
- Fixture manifest SHA-256: `3f6264f446217fc0a81964ddff71f2f07f35c862665687bca27abe58136d46ac`
- Synthetic source: false
- Feature sets: `features_price_trend_vol`, `features_full_context_no_wt`, `features_full_context_wt3d`
- Strategy: `trend_following_v1`
- Holding window: `4h`
- Candidate rows: 12
- Backtest index rows: 116
- Backtest backend used: `vector_fixed_holding`
- Split rows: 16
- Cost-stress rows: 88

Context materialization joined all supplied families for all rows:

- Funding matched rows: 2,873; unmatched rows: 0
- Premium matched rows: 2,873; unmatched rows: 0
- Open interest matched rows: 2,873; unmatched rows: 0

## Ablation And Gates

Ablation evidence statuses:

- `baseline_feature_set_no_optional_claim`: 4
- `comparator_feature_set_failed`: 3
- `comparator_feature_set_passed`: 5

Full-context WT3D rows received comparator evidence against full-context no-WT rows. Full-context no-WT rows received comparator evidence against the price/trend baseline. The ablation decision remained `no_feature_claim_accepted` because candidate-pack gates are evaluated separately and all candidates remained rejected.

All 12 candidate gate rows were `blocked`, and no candidate pack was written.

Common blockers included no-trade baseline not beaten, max single-split PnL concentration, cost-stress survival below floor, split or cost-stress evidence reserved for shortlist, and stability-region acceptance requirements.

## Boundary Notes

- The cycle artifacts are `research_only`, `observe_only`, and `promotion_ready: false`.
- `live_signal_input`, `position_sizing_input`, `operator_control_input`, `live_execution_input`, `runtime_control_input`, `live_fetch_used`, and `order_placement_used` are all `false`.
- This is local provider-fixture ablation evidence only. It is not OOS acceptance evidence, promotion evidence, or a performance claim.

## Validation

- `python -m compileall -q src\tradingbotsuite` passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q` passed: 97 tests.
- `$env:PYTHONPATH='src'; python -m pytest tests\live\test_preflight.py -q` passed: 26 tests.

## Close Decision

Stage R43 is closed. The plan implementation stop point has been reached: the branch now has provider-backed full-cycle, context, ablation, and benchmark evidence with fail-closed research gates and no live execution path.
