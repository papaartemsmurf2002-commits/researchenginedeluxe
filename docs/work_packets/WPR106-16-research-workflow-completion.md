# WPR106-16 Research Workflow Completion

Status: closed

## Scope

Close the remaining R106 workflow engineering gaps without weakening the
research-only boundary. Add modern-window profile artifacts, run-to-run delta
artifacts, a frozen-entry exit-lab path with simple-runner semantics, and wire
those artifacts into the operator research autopilot and UI so a long BTC/ETH
run produces immediately useful analysis.

This packet finishes the workflow machinery. It does not claim candidate-ready
performance, does not fabricate ETH evidence, and does not promote any research
output.

## Allowed paths

- `src/tradingbotsuite/backtesting/exits.py`
- `src/tradingbotsuite/backtesting/execution_sim.py`
- `src/tradingbotsuite/data/durable_public_archive.py`
- `src/tradingbotsuite/data/historical_data_catalog.py`
- `src/tradingbotsuite/operator_console.py`
- `src/tradingbotsuite/research_discovery/analysis_report.py`
- `src/tradingbotsuite/research_discovery/frozen_entry_exit_lab.py`
- `src/tradingbotsuite/research_discovery/run_deltas.py`
- `src/tradingbotsuite/research_cycle/spec.py`
- `src/tradingbotsuite/web/operator.py`
- `src/tradingbotsuite/web/templates/research.html`
- `tests/backtesting/test_exit_policy_expansion.py`
- `tests/research_discovery/test_analysis_report.py`
- `tests/research_discovery/test_frozen_entry_exit_lab.py`
- `tests/research_discovery/test_run_deltas.py`
- `tests/tradingbotsuite/test_operator_ui.py`
- `docs/work_packets/WPR106-16-research-workflow-completion.md`
- `docs/stage_reports/STAGE_R106_RESEARCH_WORKFLOW_COMPLETION_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`

## Constraints

- Preserve `research_only`, `observe_only`, and `promotion_ready: false` on
  all new artifacts.
- Do not place orders, change live runtime mode, write live configuration, or
  import live order-placement adapters into research code.
- Reuse current catalog, cycle, discovery, analysis, and eligibility artifacts
  where present.
- Keep generated operator artifacts inside the configured research output root.
- Treat modern-window and frozen-entry outputs as analysis/falsification
  evidence, not as promotion evidence.

## Acceptance

- Modern-window profile artifacts are discoverable by operator progress and can
  describe BTC/ETH current-market slices from catalog/spec metadata.
- Run-to-run delta reports compare current analysis against prior analysis
  artifacts and record blockers, feature/KNN/exit summaries, Sortino, and pure
  ROI deltas where available.
- A frozen-entry exit-lab artifact can select top exact-discovery rows and
  compare fixed holding against `simple_runner_v1` without rewriting completed
  discovery evidence.
- The operator autopilot runs or reuses analysis, frozen-entry exit lab,
  run-to-run deltas, and eligibility in the required sequence.
- Focused tests cover the new artifact builders, simple-runner exit semantics,
  operator route/UI wiring, artifact indexing, and autopilot reuse/step
  behavior.
- Baseline validation passes:
  `python -m compileall -q src\tradingbotsuite` and
  `PYTHONPATH=src python -m pytest tests\contracts -q`.

## Exit summary

- Added catalog-generated modern-window profile manifests/spec links and
  operator indexing for those profiles.
- Added `simple_runner_v1` primary-bar exit semantics and registered the policy
  in the execution simulator and research-cycle spec allowlist.
- Added `research_analysis_delta.json`/Markdown artifacts for run-to-run
  comparison, including a baseline mode when no prior analysis exists.
- Added a bridge-compatible frozen-entry exit lab that writes
  `discovery_exit_lab_manifest.json` and canonical candidate-gate columns,
  and fails closed when existing discovery outputs do not expose frozen entry
  timestamps.
- Extended operator jobs, artifact indexing, progress milestones, Research UI
  controls, and autopilot sequencing through analysis, delta, frozen-entry exit
  lab, and eligibility.

## Validation

- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests\backtesting\test_exit_policy_expansion.py -q`
- `$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_run_deltas.py tests\research_discovery\test_frozen_entry_exit_lab.py -q`
- `$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py -q`
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`
- `$env:PYTHONPATH='src'; python -m pytest -q`
