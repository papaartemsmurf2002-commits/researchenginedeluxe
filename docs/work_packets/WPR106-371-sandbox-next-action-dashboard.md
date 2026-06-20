# WPR106-371 - Sandbox Next-Action Dashboard

## Status

closed

## Objective

Add a first-read dashboard command for the rapid strategy sandbox that
summarizes existing artifact catalog and iteration index outputs into a compact
next-action JSON/Parquet report. The report should point agents to exact
blockers, strict-validation queues, venue-expansion requests, artifact
warnings, best hypothesis sidecars, and files to open next without recomputing
evidence.

## Dependencies

- `RAPID_STRATEGY_SANDBOX_AUDIT.md`
- `docs/RESEARCH_ENGINE_DELUXE_COMPLETION_ROADMAP.md`
- `docs/work_packets/WPR106-263-sandbox-iteration-agent-brief.md`
- `docs/work_packets/WPR106-264-sandbox-iteration-index.md`
- `docs/work_packets/WPR106-353-sandbox-artifact-catalog-agent-navigation-index.md`
- `docs/work_packets/WPR106-370-sandbox-strict-validation-descriptor-preflight.md`

## Allowed paths

- `src/tradingbotsuite/research_sandbox/next_action.py`
- `src/tradingbotsuite/research_sandbox/__init__.py`
- `src/tradingbotsuite/main.py`
- `src/tradingbotsuite/research/command_registry.py`
- `tests/research_sandbox/**`
- `tests/live/test_cli_boundary.py`
- `docs/contracts/sandbox_research_contract.md`
- `docs/contracts/boundary_contract.md`
- `docs/work_packets/WPR106-371-sandbox-next-action-dashboard.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_NEXT_ACTION_DASHBOARD_REPORT.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`

## Boundary constraints

- Summarize existing artifacts only.
- Do not run sandbox sweeps, artifact indexers, strict-validation preflight, or
  strict validation.
- Do not recompute rankings, falsification, evidence requests, or venue
  coverage.
- Do not mutate existing manifests or sidecars.
- Do not write candidate packs, paper/live artifacts, sizing, orders, runtime
  changes, live config, candidate evidence, or promotion claims.

## Acceptance criteria

- `show-rapid-strategy-sandbox-next-action` reads an explicit artifact catalog,
  explicit iteration index, or discovers existing matching JSON artifacts under
  the configured research output root.
- The command writes `sandbox_next_action_report.json` and
  `sandbox_next_action_report.parquet` under the research output root.
- The report includes current iteration status, top blockers, missing venue
  coverage, highest-priority strict-validation descriptors, highest-priority
  venue-expansion requests, artifact warnings, best-hypothesis pointers, next
  recommended packet type, and exact files to open next.
- The command preserves all sandbox boundary flags and non-authorizing fields.
- CLI input/output paths are contained under the configured research output
  root.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "next_action_dashboard"
$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
git diff --check
```

## Stop conditions

- The dashboard recomputes evidence or mutates source artifacts.
- Any path can read or write outside the configured research output root.
- Any report row can authorize strict validation, candidate packs, paper/live
  behavior, sizing, order placement, runtime-mode changes, live config writes,
  candidate evidence, or promotion readiness.

## Exit evidence

- Added `show-rapid-strategy-sandbox-next-action`, a research-only dashboard
  command that reads existing `sandbox_artifact_catalog.json` and
  `sandbox_iteration_index.json` artifacts under the configured research output
  root or discovers matching JSON artifacts under that root.
- Added `sandbox_next_action_report.json` and
  `sandbox_next_action_report.parquet` outputs with current iteration status,
  action queue counts, top blockers, missing venue coverage, descriptor-only
  strict-validation queues, venue-expansion requests, artifact warnings,
  best-hypothesis sidecar pointers, next recommended packet type, and exact
  files to open next.
- The report remains read-only and non-authorizing with explicit
  `descriptor_only`, `dashboard_only`,
  `summarizes_existing_artifacts_only`, `evidence_recomputed: false`,
  `sandbox_sweep_executed: false`, `artifact_indexer_executed: false`,
  `strict_validation_executed: false`, `strict_validation_authorized: false`,
  `candidate_pack_written: false`, and
  `candidate_pack_write_authorized: false` fields.
- Focused validation passed:
  `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "next_action_dashboard"`
  reported 2 passed / 186 deselected;
  `$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q`
  reported 25 passed;
  `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q`
  reported 202 passed;
  `python -m compileall -q src\tradingbotsuite` passed;
  `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`
  reported 461 passed;
  `git diff --check` passed with existing LF-to-CRLF warnings only.
- The dashboard does not execute sandbox sweeps, artifact indexers,
  strict-validation preflight, strict validation, provider downloads, replay
  commands, candidate-pack writes, paper/live behavior, sizing, order
  placement, runtime-mode changes, live config writes, candidate-evidence
  claims, or promotion claims.
