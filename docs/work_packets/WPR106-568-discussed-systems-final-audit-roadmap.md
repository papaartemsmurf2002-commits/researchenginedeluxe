# WPR106-568 - Discussed Systems Final Audit Roadmap

Status: completed
Owner: Codex Research Agent
Date opened: 2026-06-29

## Scope

Audit whether the full set of discussed post-PR5/PR6 changes has been made
successfully, including WPR106-567's autonomous research systems layer. If
anything remains, publish one consolidated roadmap and a goal for the next
implementation agent.

This is a docs-only audit packet. It may inspect source, tests, work packets,
CLI output, and local git status, but it must not change source behavior,
tests, generated evidence, ledgers, Lead Book rows, archive data, live/runtime
files, or research outputs.

## Allowed paths

- `docs/work_packets/WPR106-568-discussed-systems-final-audit-roadmap.md`
- `docs/audit/V2_DISCUSSION_CHANGES_FINAL_AUDIT_AND_REMAINING_ROADMAP_2026_06_29.md`
- `docs/hand_offs/WPR106-568-remaining-systems-implementation-goal.md`

## No-touch review

- No live, paper, order-placement, sizing, promotion, candidate-pack,
  runtime-mode, secret, local-state, generated-evidence, ledger, Lead Book, or
  archive data paths are in scope.
- Do not revert or rewrite the uncommitted WPR106-567 implementation work.
- Do not collect data, run venue fetches, compact ledgers, or materialize OF
  features.

## Validation target

```powershell
py -3.11 -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_archive_inventory_phase80.py tests\v2\test_data_requirement_resolver_phase80.py tests\v2\test_feature_store_catalog_phase80.py tests\v2\test_collector_gap_template_phase80.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_fast_lane_audit_phase80.py tests\v2\test_backtest_benchmark_phase80.py tests\v2\test_backtest_engine_phase11.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_ledger_phase13.py tests\v2\test_of_style_materialization_phase78.py tests\v2\test_autonomy_agent_context_phase79.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\contracts -q
$env:PYTHONPATH='src'; py -3.11 -m tradingbotsuite.v2.cli.main archive-inventory --summary
git diff --check
```

The resolver CLI may be smoke-tested with a known fail-closed request; `ready=false`
with bounded `DataGapRequest` objects is an expected result for an insufficient
accepted-research window.

## Outputs

- `docs/audit/V2_DISCUSSION_CHANGES_FINAL_AUDIT_AND_REMAINING_ROADMAP_2026_06_29.md`
- `docs/hand_offs/WPR106-568-remaining-systems-implementation-goal.md`

## Completion notes

Published the final audit, single remaining roadmap, and next-agent goal.

Audit result:

- Most discussed changes are implemented and focused validation passed.
- WPR106-567 adds archive inventory, data-requirement resolver,
  `DataGapRequest`, archive-first rules, feature-store catalog, collector gap
  templates, artifact modes, fast-lane audit/replay tooling, benchmark
  scaffolding, ledger part batching, and streaming OF improvements.
- Remaining work is now systems closure rather than foundational
  implementation: end-to-end workflow smoke, realistic benchmark evidence,
  broader fast/reference parity matrix, hardening for very large non-monotonic
  OF inputs, and final review/commit hygiene for the uncommitted WPR106-567
  changes.

Validation rerun:

```powershell
py -3.11 -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_archive_inventory_phase80.py tests\v2\test_data_requirement_resolver_phase80.py tests\v2\test_feature_store_catalog_phase80.py tests\v2\test_collector_gap_template_phase80.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_fast_lane_audit_phase80.py tests\v2\test_backtest_benchmark_phase80.py tests\v2\test_backtest_engine_phase11.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_ledger_phase13.py tests\v2\test_of_style_materialization_phase78.py tests\v2\test_autonomy_agent_context_phase79.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\contracts -q
$env:PYTHONPATH='src'; py -3.11 -m tradingbotsuite.v2.cli.main archive-inventory --summary
git diff --check
```

Results: compileall passed; focused WPR106-567 suites passed with `21`, `27`,
and `26` tests respectively; contracts passed with `463` tests; archive
inventory summary returned `492` records and `8,633,194` rows with
research-only boundary flags; `git diff --check` passed with existing
LF-to-CRLF warnings only.

Additional resolver CLI smoke returned `ready=false` for an insufficient
one-month accepted-research request and emitted bounded `DataGapRequest`
objects, which is the expected fail-closed behavior.
