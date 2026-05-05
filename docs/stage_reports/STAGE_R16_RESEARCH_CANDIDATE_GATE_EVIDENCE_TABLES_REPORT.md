# Stage R16 Research Candidate Gate Evidence Tables Report

Date: 2026-05-04

## Scope

Closed `WPR16-01-research-candidate-gate-evidence-tables`.

The packet replaced placeholder side/regime evidence with candidate-tied research evidence and made research candidate pack eligibility possible only when the complete non-synthetic fixture-backed gate passes. Passing the gate still produces research-only, observe-only, non-promotable artifacts.

## Implemented

- `metrics_by_side.parquet` is now built from actual candidate trades and carries side-specific trade count, expectancy, net return, hit rate, backtest manifest path, trades path, and trades SHA.
- `metrics_by_regime.parquet` is now built from backtest `split_by_regime` metrics rather than duplicated ranking labels.
- `backtest_index.parquet` now records candidate trades paths and hashes for aggregate, split, and cost-stress runs.
- Ranking rows now include side evidence, regime evidence, cost-stress scenario coverage, split dominance, stability region decision, and research gate reason counts.
- Hard-coded universal candidate rejection was removed. Candidates can become `research_gate_passed` only when non-synthetic fixture provenance, comparator coverage, side/regime evidence, split evidence, cost stress, stability, trade floor, and split-dominance gates all pass.
- Candidate-pack durable evidence checks now reject placeholder side/regime rows, incomplete split rows, and base-only cost-stress rows.
- A complete local fixture test writes a research candidate pack while verifying `research_only: true`, `observe_only: true`, `promotion_ready: false`, and no live/order flags.
- Existing local fixture and synthetic cycles remain fail-closed when evidence is incomplete or synthetic.

## Validation

```powershell
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
$env:PYTHONPATH='src'; python -m pytest tests/historical -q
$env:PYTHONPATH='src'; python -m pytest tests/research_artifacts -q
$env:PYTHONPATH='src'; python -m pytest tests/live/test_preflight.py -q
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite -q
git diff --check
```

Results:

- `compileall`: passed.
- `tests/contracts`: 59 passed.
- `tests/historical`: 10 passed.
- `tests/research_artifacts`: 21 passed.
- `tests/live/test_preflight.py`: 24 passed.
- `tests/tradingbotsuite`: 273 passed.
- `git diff --check`: passed with existing LF-to-CRLF warnings only.

## Boundary

No live, paper, shadow, testnet, canary, promotion, order-placement, or capital-allocation work was added. Research candidate packs remain evidence archives and are still rejected as live inputs by preflight/live validation.
