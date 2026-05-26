# WPR106-14 Operator Analysis Job And Required Workflow

Status: complete

## Scope

Wire the WPR106-13 research analysis helper into the operator workflow as a
research-only job and indexed artifact. This is the first required-workflow
slice toward the larger BTC/ETH research autopilot: completed cycle/discovery
outputs should produce a deterministic analysis artifact before candidate
eligibility review, without launching another broad search or changing live
behavior.

## Allowed paths

- `src/tradingbotsuite/operator_console.py`
- `src/tradingbotsuite/web/operator.py`
- `src/tradingbotsuite/web/templates/research.html`
- `tests/tradingbotsuite/test_operator_ui.py`
- `docs/work_packets/WPR106-14-operator-analysis-job-and-required-workflow.md`
- `docs/stage_reports/STAGE_R106_OPERATOR_ANALYSIS_JOB_REQUIRED_WORKFLOW_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`

## Constraints

- Preserve `research_only`, `observe_only`, and `promotion_ready: false`.
- Do not place orders, change live runtime mode, or write live configuration.
- Do not rerun or overwrite completed BTC/ETH cycle or exact-discovery evidence.
- Keep analysis output inside the configured research output directory.
- Treat this as evidence review and workflow sequencing, not a candidate-ready
  trading claim.

## Acceptance

- The operator API can queue a research-only analysis job from existing cycle
  and/or discovery manifest paths under the research output root.
- The job writes `research_analysis.json` and `research_analysis.md` in an
  isolated operator analysis directory.
- Research artifacts and progress diagnostics index analysis artifacts.
- The required checklist includes analysis before candidate eligibility review.
- Focused operator tests cover path allowlisting, job execution, artifact
  indexing, and progress milestone behavior.

## Closure

- Added an `analyze-research-results` operator job that validates existing
  cycle/discovery manifests under the configured research output root and writes
  isolated analysis artifacts under `operator_runs/analysis/<job_id>`.
- Indexed `research_analysis.json` in operator artifacts and required workflow
  progress, with a new Research Analysis milestone before candidate eligibility.
- Added Research UI controls for `Analyze Current Evidence` and updated
  eligibility review to wait for an indexed analysis artifact.
- Added focused tests for route path allowlisting, queued job execution,
  artifact indexing, progress milestone behavior, and UI route visibility.
- Validation:
  `python -m compileall -q src\tradingbotsuite` passed.
  `PYTHONPATH=src python -m pytest tests\research_discovery\test_analysis_report.py -q` passed with 2 tests.
  `PYTHONPATH=src python -m pytest tests\tradingbotsuite\test_operator_ui.py -q` passed with 57 tests.
  Contract validation recorded in the stage report.
