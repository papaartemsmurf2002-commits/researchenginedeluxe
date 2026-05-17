# WPR104-05 Discovery Search Feature Crosscheck

Owner: Codex Research Agent
Stage: R104 candidate validation on durable evidence
Status: closed
Created: 2026-05-17

## Goal

Perform a complete logic crosscheck of the R104 durable discovery search path:
the exact combination space, KNN payload wiring, feature-column-set usage,
pre-baked feature settings, and test coverage. Add focused regressions for any
gap found and record final review evidence.

## Allowed paths

- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `docs/work_packets/**`
- `docs/stage_reports/**`
- `configs/discovery/**`
- `src/tradingbotsuite/research_discovery/**`
- `tests/contracts/**`
- `tests/features/**`
- `tests/research_discovery/**`
- `tests/tradingbotsuite/test_operator_ui.py`

## Constraints

- Keep all artifacts and configs research-only, observe-only, and
  `promotion_ready: false`.
- Do not add live execution, runtime-mode changes, order placement, live config
  writes, promotion behavior, or sizing behavior.
- Do not fabricate candidate evidence or weaken fail-closed feature/KNN
  preflight behavior.
- Keep exact-sweep profiles deterministic and bounded.

## Planned implementation

1. Crosscheck exact sweep dimensions against generated templates and prove
   uniqueness/exhaustiveness on the configured space.
2. Crosscheck KNN payload fields are actually consumed by the real trial
   evaluator and artifacts.
3. Crosscheck feature-column-set manifests, feature preflight, and compact
   durable fixture behavior.
4. Add focused regression tests if coverage is missing.
5. Run broad validation for discovery, feature, and contract behavior.
6. Record final code-review findings and completion notes.

## Validation target

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
$env:PYTHONPATH='src'; python -m pytest tests\features -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
git diff --check
```

## Exit evidence

- Exact BTC/ETH durable configs are covered by focused tests proving 570240
  exhaustive planned combinations, correct dimension counts, valid KNN
  neighbor-pair expansion, and miniature exhaustive/sparse generation
  uniqueness.
- Discovery specs now reject duplicate search-dimension and
  feature-column-set values before generation.
- Generated real-discovery candidate IDs are stable by parameter identity
  instead of shuffled trial order.
- Runner tests prove trial KNN payload fields reach `KnnStudySpec`, failed real
  trial records preserve the search payload, and compact durable feature
  evaluation records configured versus effective feature columns.
- The real-discovery score policy version now blocks resume across the
  effective-feature-column semantic change.
- Compact durable feature tests prove BTCUSDT/ETHUSDT exact configs materialize
  the selected feature sets and use only finite-variant effective columns.
- KNN tests prove each acceptance threshold produces its distinct rejection
  reason.
- The removed-source boundary suite passes after removing a literal legacy
  token from the operator UI test fixture.
- Report:
  `docs/stage_reports/STAGE_R104_DISCOVERY_SEARCH_FEATURE_CROSSCHECK_REPORT.md`
- Validation passed:
  `python -m compileall -q src\tradingbotsuite`;
  `$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q`;
  `$env:PYTHONPATH='src'; python -m pytest tests\features -q`;
  `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`;
  `$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py -q`;
  `$env:PYTHONPATH='src'; python -m pytest -q` (1366 passed, 1 skipped);
  `git diff --check`.
