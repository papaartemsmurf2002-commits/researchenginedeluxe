# WPR106-157 Broad Artifact Component Exposure Selector

Status: closed
Date: 2026-06-12
Stage: R106 strategy research

## Objective

Broaden the 2024-forward research search beyond the recent WPR106-151 through
WPR106-156 source set by using all local WPR106 packet artifacts that provide
selected pre-May trade details and May 2026 benchmark trade details. The packet
tests whether stricter pre-May-only rolling stability plus packet/family/source
component exposure caps can find robust research-only rows without relying on
one repeated component family.

Optimization and selection use 2024-01-01 through 2026-04-30 only. May 2026 is
fully excluded from artifact discovery scores, behavior de-duplication,
rolling diagnostics, exposure caps, ranking, and selection. May 2026 is used
only as a fixed benchmark holdout for selected pre-May rows.

## Allowed Paths

- `docs/work_packets/WPR106-157-broad-artifact-component-exposure-selector.md`
- `docs/stage_reports/STAGE_R106_BROAD_ARTIFACT_COMPONENT_EXPOSURE_SELECTOR_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_157_broad_artifact_component_exposure_selector/**`

## Inputs

- Read-only local WPR106 packet artifacts under `data/research/wpr106_*` that
  contain:
  - `pre_may/selected_pre_may_replay_metrics.parquet` or
    `pre_may/selected_pre_may.parquet`;
  - `pre_may/selected_pre_may_trades.parquet`;
  - `may_benchmark/selected_may_benchmark_trades.parquet`.

## Method

- Discover reusable packet artifacts without recursively scanning unrelated
  large cache trees.
- Normalize candidate identity columns such as `candidate_id`, `overlay_id`,
  `portfolio_id`, and `source_ref` into a stable source UID.
- Recompute pre-May metrics directly from selected pre-May trade details so
  rows from different packets use the same trade accounting diagnostics.
- Behavior-de-duplicate rows by pre-May accepted trade path.
- Compute anchored rolling pre-May holdout diagnostics using only months before
  May 2026.
- Select research rows with explicit exposure caps across source packet,
  family, symbol, and exact behavior hash; allow active rows in the 1-to-5
  trades/day range when costs, overlap, drawdown, and monthly stability pass.
- Replay fixed selected rows on May 2026 only after pre-May selection.
- Keep outputs research-only, observe-only, and `promotion_ready: false`.

## Validation

- `python -m compileall -q data/research/wpr106_157_broad_artifact_component_exposure_selector/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`

## Exit Criteria

- Write discovered-source inventory, behavior-deduped source ranking, rolling
  diagnostics, selected pre-May replay, May benchmark, summary, and stage
  report artifacts.
- Update the stage ledger with the packet decision.
- Do not write a candidate pack or make paper/live/promotion claims.

## Result

Closed as rejected candidate-ready evidence. The run included 43 local WPR106
packet directories, loaded 2,925 metric rows, 591,571 pre-May trade rows, and
21,216 May benchmark trade rows, then behavior-de-duplicated to 1,915 source
rows. It found 408 strict pre-May rows and selected 100 exposure-capped rows,
but May 2026 rejected the broad selected set with 23 positive, 75 negative, and
2 flat rows; the May median was -0.014546 and the May mean was -0.018373.

The packet records WPR106-146 cross-symbol relative-strength trade-veto rows,
WPR106-128 anchored VWAP rows, and smaller BTCUSDT trend/volatility and
cross-symbol intrabar pockets as research-only follow-up hypotheses. No
candidate pack, paper/live artifact, order/sizing/runtime change, live
configuration write, CUDA speedup claim, or promotion claim was made.
