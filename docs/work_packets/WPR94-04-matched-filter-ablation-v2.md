# WPR94-04 Matched Filter Ablation V2

Status: closed
Owner: Codex Research Agent
Date: 2026-05-12

## Purpose

Determine whether discovery filters improve edge or only reduce sample size.
Filter defaults must require matched no-filter comparators, not unmatched wins.

## Allowed Paths

- `docs/work_packets/WPR94-04-matched-filter-ablation-v2.md`
- `docs/stage_reports/STAGE_R94_MATCHED_FILTER_ABLATION_V2_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `src/tradingbotsuite/research_discovery/ablation_matrix.py`
- `configs/discovery/perp_filter_ablation_matrix_v4.json`
- `configs/discovery/filter_ablation_matrix_v5.json`
- `tests/research_discovery/test_ablation_matrix.py`

## Scope

- Extend discovery ablation matrix rows with matched-filter labels:
  - `edge_improving`
  - `sample_reducing_only`
  - `unstable`
  - `side_specific`
  - `not_testable`
  - `harmful`
- Require matched grouping for filter comparisons:
  - same entry family
  - same feature set
  - same horizon
  - same regime mode
  - same KNN settings when present
  - same exit policy
  - same split and cost model identifiers when present
- Treat missing finite/provider-backed filter columns as `not_testable`.
- Keep filter default allowance locked unless a matched no-filter comparator is
  present and the filter is `edge_improving`.

## Non-Goals

- No new orderflow, liquidation, or depth features.
- No candidate-pack writing or promotion readiness.
- No live trading behavior, live config writes, order placement, runtime mode
  changes, or sizing logic changes.
- No multiple-testing/stability gate upgrade; that remains a later packet.

## Validation Plan

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_ablation_matrix.py -q
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
python -m compileall -q src\tradingbotsuite
git diff --check
```

## Validation Result

Passed on 2026-05-12:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_ablation_matrix.py -q
# 26 passed

$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
# 123 passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
# 372 passed

python -m compileall -q src\tradingbotsuite
# passed

git diff --check
# passed with line-ending warnings only
```

## Exit Evidence

- Added `filter_ablation_matrix_v5.json` with matched no-filter comparator
  rows for HVP/realized-vol, ATR, ER/chop, volatility shock, funding,
  basis/premium, OI, aggTrade flow, and liquidation filters.
- Added matched-filter V2 decision labels:
  `edge_improving`, `sample_reducing_only`, `unstable`, `side_specific`,
  `not_testable`, and `harmful`.
- Added required matched group-column enforcement so missing or mismatched
  comparator keys fail closed as `not_testable`.
- Missing, non-finite, or not-provider-backed required filter evidence now
  becomes `not_testable`.
- `filter_default_allowed` can only be true for V2 `edge_improving` rows.
- Legacy V4 broad ablation rows remain diagnostic and no longer unlock filter
  defaults.
