# Stage R67 Repo Structure Dependency Fuse Report

Date: 2026-05-06
Work packet: `docs/work_packets/WPR67-01-repo-structure-dependency-fuse.md`

## Summary

R67 is the final structure crosscheck and dependency-fuse pass after the
research implementation work. Review found the documented research branch goals
complete outside live/promotion execution and found no open P0/P1 blockers.

The stage adds a visible branch fuse document for future agents and fixes one
minor standalone research UI boundary gap. It does not change feature math,
strategy behavior, research-cycle semantics, generated evidence, live
execution, promotion readiness, or performance claims.

## Review Findings

- The active ledger and known-issues registry allow stage closure: no open P0
  issues and no open P1 issues.
- Research/data/features/backtesting/strategies remain research-only and are
  covered by import-boundary tests.
- Existing goals are implemented for provider intake, fixture provenance,
  feature construction, strategy research, backtesting, optimizer/stability,
  candidate gates, diagnostics, and research UI/CLI surfaces.
- Live/promotion execution remains intentionally out of scope for this branch.
- One P2 issue was fixed: the standalone research UI now validates job spec
  roots, pipeline spec roots, output directories, and live-mode execution
  before queuing/executing a research experiment.

## Documentation Fuse

Added `docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md` with:

- current branch status and non-goals,
- research dataflow,
- top-level repository map,
- active package map,
- framework/dependency map,
- extension checklist,
- unsafe-to-rewrite areas,
- generated artifact warnings,
- research-only guardrails,
- validation matrix,
- future-agent quick start.

Pointers were added in `AGENTS.md`, `START_HERE.md`, `README.md`, and critical
package roots under `src/tradingbotsuite/`.

## UI Boundary Hardening

`src/tradingbotsuite/ui/research_app.py` now:

- resolves queued experiment specs to absolute paths,
- allows specs only under `configs/experiments` or the configured research
  output directory,
- requires `pipeline_spec` and allows it only under `configs/data` or the
  research output directory,
- allows optional `experiment_spec` only under the same experiment-spec roots,
- rejects `output_dir` outside the configured research output directory,
- passes the configured `AppConfig` into experiment execution instead of
  reloading environment config,
- rejects direct research execution in live runtime at both route and service
  layers.

## Validation

```powershell
python -m compileall -q src\tradingbotsuite
```

Passed.

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\integration\test_research_ui.py -q
```

Passed: 6 passed.

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Passed: 367 passed.

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\live -q
```

Passed: 40 passed.

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py tests\integration\test_research_ui.py -q
```

Passed: 12 passed.

```powershell
$env:PYTHONPATH='src'; python -m pytest -q
```

Passed: 1041 passed, 91 warnings. The warnings are existing legacy
`tradingbot` `FutureWarning` messages in `src/tradingbot/lorentz_lc.py`.

## Next Gate

No additional development is required to satisfy the current research branch
plan outside live/promotion work.

Future work should be opened as a new ledger-controlled work packet. Likely
next research-only options are checked liquidation cycle wiring or broader
provider-backed OOS/stress evidence. Any live execution or promotion path must
remain separate and explicitly scoped by the ledger.
