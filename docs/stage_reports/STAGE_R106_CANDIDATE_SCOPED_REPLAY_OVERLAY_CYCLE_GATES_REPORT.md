# Stage R106 Candidate-Scoped Replay Overlay Cycle Gates Report

Work packet:
`docs/work_packets/WPR106-42-candidate-scoped-replay-overlay-cycle-gates.md`

Date: 2026-05-31

## Summary

WPR106-42 adds candidate-scoped materialized prediction overlay support to the
historical research-cycle runner. This closes the contract gap that prevented
the 24 BTCUSDT and 24 ETHUSDT WPR106-31 replayed KNN prediction artifacts from
being routed through one normal historical-cycle ranking and gate run with
per-candidate prediction frames.

Existing feature-set/global overlay behavior remains supported. Candidate-
scoped overlays are opt-in through `features.materialized_prediction_overlays`
with `scope: "candidate"` and must match a generated `candidate_id` or
`candidate_cache_key`.

## Code Changes

Updated:

- `src/tradingbotsuite/research_cycle/spec.py`
- `src/tradingbotsuite/research_cycle/runner.py`
- `tests/contracts/test_research_cycle_contract.py`
- `tests/historical/test_full_cycle_synthetic.py`

The spec parser now:

- accepts `scope`, `candidate_id`, `candidate_cache_key`, and
  `materialized_candidate_id` on materialized prediction overlays;
- keeps `feature_set` as the default overlay scope;
- requires candidate-scoped overlays to declare a generated candidate key and a
  manifest path;
- rejects duplicate candidate overlays;
- rejects mixed feature-set and candidate scopes for the same feature-set/kind;
- rejects unknown overlay keys.

The runner now:

- applies feature-set/global overlays first, preserving existing behavior;
- generates the candidate space before resolving candidate-scoped overlays;
- builds candidate-specific feature frames and feature records only for matched
  candidate overlays;
- fails closed for unmatched candidate keys, feature-set mismatch, missing
  prediction files, unsafe split evidence, row-count mismatch, non-research
  manifests, or promotion-ready manifests;
- routes aggregate, split, and cost-stress backtests for a matched candidate
  through the same candidate-scoped frame;
- records overlay provenance in rankings, backtest index, and candidate gate
  report.

## Research Boundary

No live, paper, runtime, order-placement, promotion, strategy, execution-price,
cost, fill, split, or candidate-gate behavior was changed. Candidate packs are
still written only when the existing research candidate gate passes.

This packet did not run WPR106-31 artifacts through the new route and did not
write generated research-cycle outputs. It only adds the fail-closed contract
needed for that empirical packet.

## Validation

Passed:

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_research_cycle_contract.py tests\historical\test_full_cycle_synthetic.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
$env:PYTHONPATH='src'; python -m pytest tests\research_artifacts\test_candidate_pack.py -q
```

Observed:

- focused research-cycle/historical tests: 80 passed;
- contracts: 440 passed;
- candidate-pack tests: 37 passed.

## Candidate Status

No candidate-ready claim exists. No candidate pack was produced. Zero eligible
candidates remains valid evidence.

## Next Work

Open a separate empirical packet to generate BTCUSDT and ETHUSDT
historical-cycle replay-overlay specs from WPR106-31 artifacts, run a small
reference sample first, then run the full 24-candidate overlay/ranking/gate path
only if the sample validates. That packet should write progress to JSONL and
preserve rejection rows even when all candidates fail.
