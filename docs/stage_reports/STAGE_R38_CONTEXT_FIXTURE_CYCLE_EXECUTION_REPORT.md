# Stage R38 Context Fixture Cycle Execution Report

Date: 2026-05-05
Owner: Codex Research Agent
Work packet: `docs/work_packets/WPR38-01-context-fixture-cycle-execution.md`
Status: closed

## Scope

WPR38 executed a bounded historical research cycle against the generated BTCUSDT context fixture pack from WPR37.

The packet did not use legacy chart exports, Pine files, parity files, synthetic fallback, live execution, paper/shadow/testnet/canary flows, order placement, promotion, or candidate acceptance.

## Command

```powershell
$env:PYTHONPATH='src'
$env:TBS_RUNTIME_MODE='paper'
python -m tradingbotsuite.main run-historical-research-cycle --spec data\research\historical_cycles\btcusdt_context_provider_cycle\specs\btcusdt_context_provider_cycle.json
```

## Outputs

- Run directory: `data/research/historical_cycles/btcusdt_context_provider_cycle/run`
- Cycle manifest: `data/research/historical_cycles/btcusdt_context_provider_cycle/run/research_cycle_manifest.json`
- Cycle manifest SHA-256: `452dcc078e9fc5eadef767e06adff8f42d4f1ee1fcfa3f4362fb0406834d1346`
- Candidate rankings: `data/research/historical_cycles/btcusdt_context_provider_cycle/run/candidate_rankings.parquet`
- Candidate gate report: `data/research/historical_cycles/btcusdt_context_provider_cycle/run/candidate_gate_report.parquet`
- Backtest index: `data/research/historical_cycles/btcusdt_context_provider_cycle/run/backtest_index.parquet`
- Rejection report: `data/research/historical_cycles/btcusdt_context_provider_cycle/run/rejection_report.md`

The run outputs are local generated research artifacts under ignored `data/research/historical_cycles/**`.

## Data Source Evidence

- Source type: `historical_fixture_pack`
- Fixture ID: `btcusdt-context-provider-v1`
- Fixture manifest SHA-256: `7c97dfb0abfd8459e72998815b8fee25af42aac78fd0e9bd1cf9ef3523e26464`
- Synthetic source used: `false`
- Legacy chart export source used: `false`
- Fixture scope: `generated_small_provider_kline_fixture_not_oos_acceptance_evidence`
- Research limitations include `not_sufficient_for_oos_acceptance`, `not_sufficient_for_performance_claims`, and `not_promotion_ready`.

## Context Materialization

Feature set `features_full_context_no_wt` materialized with fixture-family context SHA-256 `5a8312582a987b551b2bbb8dbe5ecdd7a2050b12b3a57ecf78b8db7524fd5250`.

Joined context families:

- `funding_rate`
- `premium_index`
- `open_interest`

Joined context columns:

- `funding_rate`
- `funding_rate_change`
- `premium_basis_rate`
- `basis_bps`
- `premium_close`
- `open_interest`
- `open_interest_change`
- `open_interest_change_pct`
- `open_interest_value`

The feature build reported 144 rows, one materialized feature set, and event-time as-of context joins with `family_event_time_ms_lte_cycle_bar_time_ms`.

## Candidate Gate Result

- Candidate rows: 4
- Backtest index rows: 17
- Split metric rows: 2
- Cost-stress rows: 11
- Candidate pack written: `false`
- Candidate acceptance scope: `research_gate_evaluated_fail_closed`
- Gate status: all 4 candidates blocked

Primary rejection themes were missing ablation comparator evidence, split/cost-stress/stability gate failures, no-trade baseline failure for one candidate, cost-stress survival below the configured 1.0 floor, and split dominance. This is expected for a compact 144-row local fixture and is not a product failure.

## Boundary Notes

- The cycle manifest is `research_only`, `observe_only`, and `promotion_ready: false`.
- `live_signal_input`, `position_sizing_input`, `operator_control_input`, `live_execution_input`, `runtime_control_input`, `live_fetch_used`, and `order_placement_used` are all `false`.
- No candidate pack, promotion candidate, paper archive, shadow archive, testnet archive, or live artifact was produced.
- This packet records local execution evidence only. It is not OOS acceptance evidence and does not support performance claims.

## Validation

- `python -m compileall -q src\tradingbotsuite` passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q` passed: 97 tests.
- `$env:PYTHONPATH='src'; python -m pytest tests\live\test_preflight.py -q` passed: 26 tests.
- `git diff --check` reported only existing LF-to-CRLF normalization warnings.

## Close Decision

Stage R38 is closed. The generated BTCUSDT context fixture has now been consumed by the historical cycle runner end-to-end, with context-aware feature materialization and fail-closed candidate gate evidence recorded.
