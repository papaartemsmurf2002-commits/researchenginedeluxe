# Work Packet: WPR106-46 exact replay overlay domain and cycle

## Goal

Implement the Option A exact replay-overlay path for WPR106-31 replay leads.
The packet makes those replay leads exactly representable by the historical
cycle candidate contract, emits singleton replay-overlay historical-cycle spec
drafts, and runs bounded BTC/ETH overlay cycle smokes without weakening gates
or making candidate-ready claims.

## Current Repo Facts

- Current implementation branch: `codex/wpr106-46-exact-replay-overlay`.
- WPR106-42 added candidate-scoped materialized prediction overlay routing in
  historical-cycle infrastructure.
- WPR106-43 restored `discovery-lead-replay-spec-v1` compatibility.
- WPR106-44 and WPR106-45 both found all 48 WPR106-31 replay leads
  unrepresentable by the then-current historical-cycle
  `hmm_knn_local_analog_filter_v2` contract.
- WPR106-46 selects Option A: exact replay lead domains and `1h` KNN overlay
  horizons are explicitly supported and tested.
- `ISSUE-R104-001` remains open until durable candidate-depth data, deeper
  cycles, exact sweeps, and eligibility review prove closure.

## Allowed Edit Paths

- `.github/workflows/research-validation.yml`
- `README.md`
- `START_HERE.md`
- `docs/ACTIVE_INDEX.md`
- `docs/KNOWN_ISSUES.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/stage_reports/STAGE_R106_*.md`
- `docs/work_packets/WPR106-*.md`
- `docs/work_packets/WPR106-*-progress.jsonl`
- `src/tradingbotsuite/**`
- `tests/**`

Generated empirical artifacts under `data/research/operator_runs/` are local
evidence outputs and remain ignored by git.

## Implementation Summary

- Added explicit `1h` support to `hmm_knn_local_analog_filter_v2`.
- Added replay-domain allowlist values for exact explicit specs:
  `spacing_bars=4`, low probability thresholds, negative/zero EV thresholds,
  low neighbor counts, low neighbor agreement, zero/low distance quality, and
  zero/low vote margin.
- Kept default optimizer grids conservative. Replay-domain values are allowed
  through explicit specs and preflight representability, not silent grid
  expansion.
- Fixed replay strategy accounting so `label_horizon="1h"` maps to
  `holding_window="1h"` instead of falling back to `4h`.
- Added replay-overlay spec-draft artifacts that emit one singleton
  historical-cycle spec per representable replay lead.
- Generated candidate-scoped overlays using the same `CandidateConfig` cache
  key as preflight.
- Added operator-wrapper tolerance for known discovery spec isolation metadata
  and for operator-wrapped base cycle templates used by replay spec drafts.
- Restored the missing top-level test fixture used by the full suite.

## Empirical Artifact Evidence

Local output root:
`data/research/operator_runs/wpr106_46_exact_replay_overlay_domain_and_cycle`

| Artifact or count | Value |
| --- | ---: |
| Exact replay leads checked | 48 |
| Exact replay leads representable | 48 |
| BTC overlay cycle specs emitted | 24 |
| ETH overlay cycle specs emitted | 24 |
| Historical cycle smokes run | 2 |
| Candidate-ranking rows in smokes | 4 |
| Backtest-index rows in smokes | 34 |
| Gate-report rows in smokes | 4 |
| Candidate-pack eligible rows in smokes | 0 |
| Candidate packs emitted | 0 |

Bounded cycle smoke outputs:

- BTC:
  `data/research/operator_runs/wpr106_46_exact_replay_overlay_domain_and_cycle/cycle_outputs/btcusdt/wpr106-46-exact-replay-overlay-btcusdt-btcusdt-mat-046e252f8fe9a490d8bc843782d931b2-6afe89cfb304`
- ETH:
  `data/research/operator_runs/wpr106_46_exact_replay_overlay_domain_and_cycle/cycle_outputs/ethusdt/wpr106-46-exact-replay-overlay-ethusdt-ethusdt-mat-71e8cbe20b1d1bf4bc0cf5de0f2898a7-16481138bb6d`

Both smokes produced candidate rankings, backtest indexes, candidate gate
reports, and rejection reports. Candidate-scoped overlay provenance appears in
rankings, backtest index, and gate report rows for both symbols. Both smokes
remained `research_only: true`, `observe_only: true`, `promotion_ready: false`,
with `candidate_pack_written: false` and no pack-eligible rows.

## Research Boundary

- Research outputs are not live signals.
- Research artifacts remain `research_only`, `observe_only`, and
  `promotion_ready: false`.
- This packet does not add paper/live execution, order placement, sizing,
  runtime-mode changes, live configuration writes, promotion authorization, or
  Hyperliquid execution proof.
- Candidate packs are still blocked unless the existing gate stack passes.

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

- Strategy/preflight focused suite: 284 passed.
- Research-cycle/synthetic historical suite: 80 passed.
- Research-discovery/contracts suite: 675 passed.
- High-risk backtesting/features/historical/research-artifacts/live suite:
  280 passed, 1 skipped.
- Full suite: 1528 passed, 1 skipped.
- `git diff --check`: passed with line-ending warnings only.

## Broader Research Queue

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

True OFI/depth, market making, cross-venue carry, options overlays, and
liquidation-tactics claims remain deferred until honest data and simulators
exist for those claims.

## Definition Of Done

- Exact replay lead domains and `1h` horizon support are explicit and tested.
- WPR106-31 BTC/ETH replay leads generate exact singleton overlay specs.
- Bounded BTC/ETH overlay cycle smokes run and keep overlay provenance through
  rankings, backtest index, and gate reports.
- Candidate packs remain blocked because existing gates do not pass.
- `ISSUE-R104-001` remains open.
- No live/paper/order/sizing/promotion behavior is authorized.

## Rollback Plan

Revert the WPR106-46 code, test, and documentation paths from this packet. Do
not revert unrelated WPR106-32 through WPR106-45 dirty work unless explicitly
requested.
