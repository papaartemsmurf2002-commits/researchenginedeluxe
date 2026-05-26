# WPR106-12 Final Ledger Schema Repair

Status: complete

## Scope

Investigate and fix failed job
`run-discovery-40cb1c90d0f8487a859a23e05d21e656`, which completed all BTC
exact-discovery trial records but failed while writing final Parquet ledgers:
`accepted_bar_count` contained mixed numeric and empty-string values.

## Allowed paths

- `src/tradingbotsuite/research_discovery/runner.py`
- `src/tradingbotsuite/operator_console.py`
- `tests/research_discovery/test_discovery_runner.py`
- `tests/tradingbotsuite/test_operator_ui.py`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `docs/work_packets/WPR106-12-final-ledger-schema-repair.md`

## Constraints

- Do not delete or rewrite durable trial records.
- Do not reduce the performance-first exact-discovery worker cap.
- Preserve research-only, observe-only, and `promotion_ready: false` semantics.
- Completed-run repair may rebuild ledgers/manifests from immutable trial JSONs
  but must not run discovery compute again.

## Acceptance

- Ledger Parquet writes normalize nullable numeric columns instead of mixing
  empty strings with numbers.
- Completed BTC exact-discovery run can be finalized from durable trial JSONs.
- Manifest and state agree on 570240 completed trials.
- Focused discovery runner tests pass.

## Closure

- Root cause: `_ledger_row_from_record()` used empty strings for absent values,
  so final ledger rebuild mixed integers and `""` in nullable metric columns
  such as `accepted_bar_count`. PyArrow rejected the object column during
  Parquet conversion.
- Fix: final ledger frames now normalize known integer, float, and boolean
  ledger columns to pandas nullable dtypes before writing Parquet.
- Completed-run resume now permits artifact-only repair when the manifest is
  stale, ledgers are missing, ledger row counts do not match completed state, or
  Parquet ledgers are unreadable. It still refuses clean completed-run overwrite.
- Operator progress now lets a validated repaired discovery manifest override a
  stale failed job row for the checklist milestone. The failed job remains in
  job history, but it no longer blocks the milestone after artifacts are
  repaired. Failed jobs also no longer outrank missing prerequisites, so an old
  ETH discovery failure does not block the ETH discovery step before the ETH
  cycle has completed.
- Repaired output:
  `data/research/operator_runs/discovery_runs/exact-entry-sweep-btcusdt-candidate-depth-v1`
  now has 570240 completed state IDs, 570240 completed trial hashes, 570240
  trial JSON records, and manifest counts of 22560 interesting, 547680 blocked,
  and 0 filter-blocked trials.
- Validation:
  `python -m compileall -q src\tradingbotsuite\research_discovery`
  and
  `PYTHONPATH=src python -m pytest tests\research_discovery\test_discovery_snapshots.py tests\research_discovery\test_discovery_runner.py -q`
  passed with 29 tests.
  `PYTHONPATH=src python -m pytest tests\tradingbotsuite\test_operator_ui.py::test_operator_progress_prefers_repaired_discovery_artifact_over_failed_job -q`
  passed.
  `python -m compileall -q src\tradingbotsuite` and
  `PYTHONPATH=src python -m pytest tests\contracts -q` passed with 427
  contract tests.
- Live operator progress check after restart reports BTC exact discovery
  complete, ETH exact discovery waiting on ETH cycle, and next action
  `Run ETH brute-force cycle.`
