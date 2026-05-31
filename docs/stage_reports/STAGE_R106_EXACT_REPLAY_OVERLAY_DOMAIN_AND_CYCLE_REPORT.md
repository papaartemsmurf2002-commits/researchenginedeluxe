# Stage R106 Exact Replay Overlay Domain And Cycle Report

Work packet:
`docs/work_packets/WPR106-46-exact-replay-overlay-domain-and-cycle.md`

Date: 2026-05-31

## Summary

WPR106-46 implements the Option A exact replay-overlay path after WPR106-45.
The historical-cycle strategy domain now explicitly accepts exact WPR106-31
replay lead values for `hmm_knn_local_analog_filter_v2` at `1h`, while normal
optimizer grids remain conservative. Replay preflight can now emit a second
research-only artifact family: exact singleton historical-cycle overlay spec
drafts, one per representable replay lead.

Bounded BTC and ETH singleton overlay cycle smokes were executed from generated
specs. Candidate-scoped overlay provenance flowed through rankings, backtest
index, and gate reports. No candidate pack was written because the existing
gates remained fail-closed.

## Implementation

- Added `1h` holding-window support and explicit replay-domain allowed values
  for `hmm_knn_local_analog_filter_v2`.
- Preserved conservative default search spaces; replay values are explicit
  representability values, not silent grid expansion.
- Fixed replay strategy accounting so `label_horizon="1h"` maps to
  `holding_window="1h"`.
- Added exact replay-overlay cycle spec draft builders and manifest validation.
- Generated singleton search-space entries with exact replay parameters and
  candidate-scoped materialized prediction overlays keyed by the preflight
  `CandidateConfig` cache key.
- Accepted known operator isolation metadata in discovery-run specs and
  stripped known operator wrapper keys from base cycle templates used for spec
  draft generation.
- Restored the missing top-level `sample_bars` fixture required by the full
  suite.

## Empirical Evidence

Local output root:
`data/research/operator_runs/wpr106_46_exact_replay_overlay_domain_and_cycle`

| Artifact or count | Value |
| --- | ---: |
| Exact replay leads checked | 48 |
| Exact replay leads representable | 48 |
| Overlay cycle specs emitted | 48 |
| BTC overlay cycle specs emitted | 24 |
| ETH overlay cycle specs emitted | 24 |
| Bounded historical cycle smokes run | 2 |
| Candidate-ranking rows in smokes | 4 |
| Backtest-index rows in smokes | 34 |
| Gate-report rows in smokes | 4 |
| Candidate-pack eligible rows in smokes | 0 |
| Candidate packs emitted | 0 |

Smoke cycles:

- BTC:
  `data/research/operator_runs/wpr106_46_exact_replay_overlay_domain_and_cycle/cycle_outputs/btcusdt/wpr106-46-exact-replay-overlay-btcusdt-btcusdt-mat-046e252f8fe9a490d8bc843782d931b2-6afe89cfb304`
- ETH:
  `data/research/operator_runs/wpr106_46_exact_replay_overlay_domain_and_cycle/cycle_outputs/ethusdt/wpr106-46-exact-replay-overlay-ethusdt-ethusdt-mat-71e8cbe20b1d1bf4bc0cf5de0f2898a7-16481138bb6d`

The generated artifacts are local research evidence and are not committed.

## Research Boundary

- Research outputs are not live signals.
- Exact replay-overlay artifacts remain `research_only`, `observe_only`, and
  `promotion_ready: false`.
- Overlay execution is not a candidate-ready claim by itself.
- Candidate packs remain blocked unless the existing gate stack passes.
- No Hyperliquid live execution proof, order-placement proof, sizing proof,
  paper/live runtime behavior, live configuration write, or promotion
  authorization is created by this packet.

## Issue State

`ISSUE-R104-001` remains open. WPR106-46 proves exact replay representability
and bounded overlay cycle plumbing, but does not complete the durable
candidate-depth deep cycles, full exact sweeps, exit labs, negative controls,
or eligibility review required to close that P1 blocker.

## Validation

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_strategy_contracts.py tests\research_discovery\test_replay_overlay_preflight.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_research_cycle_contract.py tests\historical\test_full_cycle_synthetic.py -q
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery tests\contracts -q
$env:PYTHONPATH='src'; python -m pytest tests\backtesting tests\features tests\historical tests\research_artifacts tests\live -q
python -m compileall -q src\tradingbot src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest -q
git diff --check
```

Results:

- `python -m compileall -q src\tradingbotsuite`: passed.
- Strategy/preflight focused suite: 284 passed.
- Research-cycle/synthetic historical suite: 80 passed.
- Research-discovery/contracts suite: 675 passed.
- High-risk backtesting/features/historical/research-artifacts/live suite:
  280 passed, 1 skipped.
- `python -m compileall -q src\tradingbot src\tradingbotsuite`: passed.
- Full `pytest -q`: 1528 passed, 1 skipped.
- `git diff --check`: passed with line-ending warnings only.

## Candidate Status

No candidate-ready claim exists. No paper-ready, live-ready, or
promotion-ready claim exists. No candidate pack was written by this packet.

## Next Research Packets

- Full frozen-entry exit lab for all 48 replay leads.
- Modern-window versus full-window replay comparison.
- AggTrade-confirmed compression breakout versus no-flow breakout.
- Trend-as-filter experiments over replay, breakout, and range families.
- BTC/ETH residual relative-value activation.
- AggTrade flow exhaustion overlay for entries/exits.
- Funding/OI/premium diagnostic packet only where provenance is strong.
- Session, weekend, and funding-window stratification.
- Negative-control and leakage stress tests using shuffled labels, shifted
  context, and no-KNN/no-regime baselines.
