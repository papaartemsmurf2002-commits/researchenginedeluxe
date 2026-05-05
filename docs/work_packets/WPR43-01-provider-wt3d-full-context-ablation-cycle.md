# WPR43-01 Provider WT3D Full-Context Ablation Cycle

Status: closed
Owner: Codex Research Agent
Stage: Stage R43 provider WT3D full-context ablation cycle
Opened: 2026-05-05
Closed: 2026-05-05

## Objective

Run a non-synthetic provider-backed historical cycle that explicitly compares no-WT and WT3D feature sets on the WPR41 latest-month BTCUSDT context fixture, so the research branch has real historical-cycle ablation evidence for WT3D/no-WT/full-context variants.

## Allowed paths

- `data/research/historical_cycles/btcusdt_context_provider_wt3d_ablation_cycle/**`
- `docs/KNOWN_ISSUES.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/work_packets/WPR43-01-provider-wt3d-full-context-ablation-cycle.md`
- `docs/stage_reports/STAGE_R43_PROVIDER_WT3D_FULL_CONTEXT_ABLATION_CYCLE_REPORT.md`

## Inputs

- WPR41 fixture manifest: `data/research/fixtures/btcusdt_context_provider_latest_month_v1/fixture_pack_manifest.json`.
- Feature sets: `features_price_trend_vol`, `features_full_context_no_wt`, `features_full_context_wt3d`.
- Strategy: `trend_following_v1`.
- Holding window: `4h`.

## Non-goals

- No legacy chart export, TradingView, Pine, parity, or synthetic input use.
- No new code unless the cycle exposes a blocking defect.
- No live, paper, shadow, testnet, canary, promotion, order-placement, runtime-control, or capital-allocation work.
- No OOS acceptance, performance claim, candidate promotion, or Stage 13 execution.

## Implementation plan

1. Write a bounded historical-cycle spec using the WPR41 fixture manifest and synthetic fallback disabled.
2. Include price/trend baseline plus full-context WT3D/no-WT feature sets with metadata-valid trend-following search values.
3. Run the cycle and audit ablation rows, context materialization, candidate gates, live flags, and hashes.
4. Record whether WT3D variants pass, fail, or remain blocked by candidate gates.
5. Run validation baseline and close the packet.

## Exit criteria

- Historical cycle consumes the provider fixture with `synthetic_fixture: false`.
- WT3D and no-WT feature sets run as real historical-cycle backtests.
- Ablation evidence is candidate-tied and recorded in `ablation_report.json` and rankings.
- Candidate gate behavior is truthful and research-only.
- Validation evidence is recorded in the stage report.

## Completion evidence

- Initial draft spec with `features_price_trend_vol_wt3d` failed before output because `trend_following_v1` does not support that feature set. The packet was tightened to the supported full-context WT3D/no-WT comparison plus price/trend baseline.
- Historical cycle output: `data/research/historical_cycles/btcusdt_context_provider_wt3d_ablation_cycle/run/research_cycle_manifest.json`.
- Cycle manifest SHA-256: `a5917ec32ac7ae2a852d6ad369fc58934d6611916c4bd277f334e09cd98e8567`.
- Data source: `historical_fixture_pack`, fixture ID `btcusdt-context-provider-latest-month-v1`, synthetic false.
- Feature sets: `features_price_trend_vol`, `features_full_context_no_wt`, `features_full_context_wt3d`.
- Candidate rows: 12.
- Backtest index rows: 116, all `vector_fixed_holding`.
- Context join coverage: funding, premium, and open-interest each matched all 2,873 primary rows with zero unmatched rows.
- Ablation evidence statuses: 4 `baseline_feature_set_no_optional_claim`, 3 `comparator_feature_set_failed`, 5 `comparator_feature_set_passed`.
- Candidate pack status: `candidate_pack_written: false`, all gates blocked.

## Validation

- `python -m compileall -q src\tradingbotsuite` passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q` passed: 97 tests.
- `$env:PYTHONPATH='src'; python -m pytest tests\live\test_preflight.py -q` passed: 26 tests.
