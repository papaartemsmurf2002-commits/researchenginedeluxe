# Stage R106 Sparse Side Veto Validation Report

Date: 2026-06-09

Work packet: `docs/work_packets/WPR106-81-sparse-side-veto-validation.md`

## Scope

WPR106-81 turned the WPR106-80 BTC sparse long-only side decomposition into a
real strategy contract. It added `allowed_sides` and `side_filter_stage` to
`sparse_event_filter_v1` and evaluated both:

- `pre_selection`: filter to one side before top-score selection;
- `post_selection`: keep the original sparse top-score and side-balance
  selection, then veto the disallowed side.

All outputs remain research-only, observe-only, and not promotion-ready. No
candidate pack, live/paper artifact, order, sizing behavior, runtime-mode
change, or live configuration write was produced.

## Artifacts

Generated cycle outputs:

- `data/research/historical_cycles/sparse_side_veto_btcusdt_r106_v1/research_cycle_manifest.json`
- `data/research/historical_cycles/sparse_side_veto_btcusdt_r106_v1/candidate_rankings.parquet`
- `data/research/historical_cycles/sparse_side_veto_btcusdt_r106_v1/candidate_gate_report.parquet`
- `data/research/historical_cycles/sparse_side_veto_btcusdt_r106_v1/backtest_index.parquet`
- `data/research/historical_cycles/sparse_side_veto_btcusdt_r106_v1/wpr106_81_candidate_summary.csv`

Generated Monte Carlo outputs:

- `data/research/monte_carlo_exit_sizing/wpr106_81/wpr106_81_monte_carlo_side_veto_summary.json`
- `data/research/monte_carlo_exit_sizing/wpr106_81/wpr106_81_monte_carlo_side_veto_candidates.csv`
- `data/research/monte_carlo_exit_sizing/wpr106_81/wpr106_81_monte_carlo_side_veto_paths.csv`

Cycle counts:

- candidates: 14;
- aggregate backtests: 14;
- split backtests: 8;
- cost-stress backtests: 22;
- candidate packs written: 0.

## Results

The pre-selection one-sided rows failed. They selected a larger one-sided event
population and lost after costs:

- price-only long pre-selection: 503 trades, net return -0.819524;
- aggTrade-contrarian long pre-selection: 513 trades, net return -0.773747;
- both short pre-selection controls were worse.

The post-selection side-veto rows reproduced the useful WPR106-80 hypothesis.
They keep the original sparse competitive selection and veto shorts after
selection:

- rank 1, aggTrade-contrarian post-selection long:
  - 346 long trades;
  - net return after cycle costs: +9.420343;
  - costed expectancy: +0.007912;
  - max drawdown: -0.303719;
  - split trade-count minimum: 116;
  - cost-stress survival rate: 1.0.
- rank 2, price-only post-selection long:
  - 313 long trades;
  - net return after cycle costs: +1.643870;
  - costed expectancy: +0.004232;
  - max drawdown: -0.454665;
  - split trade-count minimum: 108;
  - cost-stress survival rate: 1.0.

All transparent baselines and short-only controls ranked below no-trade.

## Monte Carlo

The follow-up Monte Carlo used the user-requested cost assumption:

- taker commission: 0.0432% per side;
- round-trip commission: 0.0864%;
- funding ignored;
- slippage ignored for this offline analysis.

With 10,000 bootstrap paths:

- aggTrade-contrarian post-selection long:
  - observed terminal return after user fee: +14.400048;
  - MC 5th percentile terminal return: +2.656835;
  - terminal-negative probability: 0.0011;
  - observed max loss streak: 8;
  - MC p95 max loss streak: 10.
- price-only post-selection long:
  - observed terminal return after user fee: +2.769334;
  - MC 5th percentile terminal return: -0.028303;
  - terminal-negative probability: 0.0529;
  - observed max loss streak: 6;
  - MC p95 max loss streak: 11.

Martingale x1.5 remains not applicable. These are fixed-hold exits, not
sequence-proven 1:2 fixed TP/SL exits, and WPR106-80 already rejected current
fixed TP/SL evidence as negative and path-ambiguous.

## Gate Outcome

Both top rows remain rejected by the current candidate gate despite positive
split and cost-stress evidence:

- the one-sided side-veto contract is still treated as missing same-candidate
  long/short evidence;
- the aggTrade row needs an explicit feature-ablation comparator;
- stability-region acceptance is still required before candidate-pack use.

This is a fail-closed research blocker, not a live-risk issue.

## Decision

Open WPR106-82 for a bounded expensive optimizer sweep around the two
post-selection long-only sparse rows, with the aggTrade-contrarian row as the
lead. Do not create a candidate pack or promotion claim until the gate model
can represent explicit one-sided side-veto evidence, feature ablations, and
stability-region acceptance.

## Validation

Passed:

```powershell
python -m compileall -q src/tradingbotsuite/strategies/sparse_event_filter.py src/tradingbotsuite/strategies/parameters.py
$env:PYTHONPATH='src'; python -m pytest tests/contracts/test_strategy_contracts.py::test_sparse_event_filter_metadata_covers_required_contract tests/contracts/test_strategy_contracts.py::test_sparse_event_filter_allowed_sides_vetoes_opposite_side tests/contracts/test_strategy_contracts.py::test_sparse_event_filter_post_selection_veto_preserves_top_score_competition tests/contracts/test_strategy_contracts.py::test_sparse_event_filter_outputs_research_only_signals tests/contracts/test_strategy_contracts.py::test_sparse_event_filter_side_balance_caps_dominant_side -q
$env:PYTHONPATH='src'; python -m tradingbotsuite.main run-historical-research-cycle --spec configs/research/sparse_side_veto_btcusdt_r106_v1.json
```
