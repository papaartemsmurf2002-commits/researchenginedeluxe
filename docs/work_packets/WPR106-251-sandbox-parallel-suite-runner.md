# WPR106-251 Sandbox Parallel Suite Runner

Status: closed
Owner: Codex Research Agent
Created: 2026-06-18

## Objective

Improve Rapid Strategy Iteration Sandbox agent workflow speed by allowing
independent sandbox suite cases to run concurrently while preserving
deterministic suite indexes, compact artifacts, descriptor-only evidence
requests, and all sandbox research boundaries.

## Scope

- Add an explicit `max_workers` option to `run_sandbox_suite()` with serial
  behavior as the default.
- Run independent suite cases concurrently when `max_workers > 1`.
- Preserve deterministic output order by writing suite case indexes and
  aggregated evidence requests in suite spec order.
- Keep per-case output directories isolated under the existing suite directory
  layout.
- Preserve preflight gating, blocked-case behavior, archive sweep routing,
  analysis, evidence-request aggregation, and suite manifests.
- Expose the same option on the `run-rapid-strategy-sandbox-suite` CLI command.
- Add focused tests proving parallel execution preserves deterministic output
  order and boundary fields.
- Update sandbox contract and stage closeout docs.

## Allowed Paths

- `docs/work_packets/WPR106-251-sandbox-parallel-suite-runner.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_PARALLEL_SUITE_RUNNER_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/suite.py`
- `src/tradingbotsuite/main.py`
- `tests/research_sandbox/**`
- `tests/live/test_cli_boundary.py` only if CLI boundary coverage must change
- `docs/KNOWN_ISSUES.md` only if a new blocking evidence or boundary risk is
  discovered

## Acceptance Evidence

- Serial suite execution remains the default and existing suite outputs remain
  compatible.
- Parallel suite execution with `max_workers > 1` completes independent cases
  and writes suite index rows in suite spec order.
- Aggregated evidence-request descriptors remain descriptor-only,
  research-only, observe-only, non-promotable, and candidate-pack ineligible.
- Blocked-by-preflight cases still skip sweeps and downstream artifacts.
- The CLI accepts `--max-workers` without introducing live/paper/order/sizing
  behavior.
- Validation includes focused sandbox tests, import-boundary tests, package
  compile, and the contract baseline when the local validation environment
  allows pytest-asyncio socket setup.

## Boundary

This packet changes local sandbox suite orchestration throughput only. It does
not alter strategy math, scoring formulas, strict validation, candidate-pack
gates, live/paper signals, sizing, order placement, runtime mode, live
configuration, provider downloads, descriptor archive loading, or promotion
readiness.

## Completion Notes

Implemented and closed on 2026-06-18. `run_sandbox_suite()` now accepts
`max_workers`, defaults to serial execution, and uses a thread pool for
independent case execution when `max_workers > 1`. Each case still writes to
its existing isolated preflight and run directories. Suite case payloads,
index rows, case results, and aggregated evidence-request descriptors are
sorted back into suite spec order before final artifacts are written.

The `run-rapid-strategy-sandbox-suite` CLI now accepts `--max-workers`, returns
the selected value, and records it in the suite manifest. The option does not
change trial identity, strategy math, archive loading, strict validation,
candidate-pack behavior, live/paper signals, sizing, orders, runtime mode, or
promotion readiness.

Focused coverage proves a two-case suite run with `max_workers=2` preserves
case order in JSON index rows, Parquet index rows, returned case results, and
aggregated evidence requests. Existing suite tests continue to cover serial
behavior and preflight-blocked cases.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q
```

Final results: 76 sandbox tests passed, 11 import-boundary tests passed,
package compileall passed, 19 live CLI boundary tests passed, and the full
contract baseline passed with 461 tests. The first full-contract attempt
reached 460 passed tests before the known local Windows pytest-asyncio
`WinError 10055` socket setup failure; an immediate rerun passed cleanly.
