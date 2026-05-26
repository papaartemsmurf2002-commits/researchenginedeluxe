# WPR106-15 Operator Research Autopilot Sequencer

Status: complete

## Scope

Add a bounded operator master research job that sequences the existing required
R106 workflow instead of asking the operator to queue every step manually. The
job should reuse completed catalog/cycle/discovery/analysis/eligibility
artifacts, run missing required steps through the existing isolated job helpers,
write a research-only autopilot manifest, and stop at the first blocked step
with a clear recovery reason.

This is the next incremental slice toward the handoff's one-button research
machine. Frozen-entry exit-lab execution, modern-window spec generation, and
run-to-run deltas remain out of scope unless they can be wired without changing
backtest math.

## Allowed paths

- `src/tradingbotsuite/operator_console.py`
- `src/tradingbotsuite/web/operator.py`
- `src/tradingbotsuite/web/templates/research.html`
- `tests/tradingbotsuite/test_operator_ui.py`
- `docs/work_packets/WPR106-15-operator-research-autopilot-sequencer.md`
- `docs/stage_reports/STAGE_R106_OPERATOR_RESEARCH_AUTOPILOT_SEQUENCER_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`

## Constraints

- Preserve `research_only`, `observe_only`, and `promotion_ready: false`.
- Do not place orders, change live runtime mode, or write live configuration.
- Do not overwrite completed BTC/ETH evidence; reuse it when current and valid.
- Keep generated autopilot artifacts inside the configured research output
  directory.
- Use existing catalog, cycle, discovery, analysis, and eligibility helpers
  rather than inventing parallel data or scoring paths.

## Acceptance

- The operator API can queue a `run-research-autopilot` job.
- The Research UI exposes a primary `Run Research Autopilot` action.
- The autopilot writes a research-only manifest that records executed, skipped,
  and blocked steps.
- Existing completed artifacts are skipped rather than rerun.
- Missing required steps are run through existing isolated helper functions.
- Focused tests cover route visibility, job execution with monkeypatched
  helpers, artifact indexing, and blocked prerequisite reporting.

## Closure

- Added `run-research-autopilot` as a master operator job.
- The job reuses current completed catalog, BTC/ETH cycle, exact discovery,
  analysis, and eligibility artifacts where available.
- Missing required steps are executed through the existing isolated helper
  functions rather than queued as child jobs, avoiding operator job-loop
  deadlock.
- The job writes
  `operator_runs/research_autopilot/<job_id>/research_autopilot_manifest.json`
  with executed, skipped, failed, and blocked step records.
- The Research UI now exposes a primary `Run Research Autopilot` button and
  indexes `research_autopilot` artifacts.
- Frozen-entry alternative-exit simulation, modern-window spec generation, and
  run-to-run delta reports remain deferred under `ISSUE-R106-002`.
- Validation:
  `python -m compileall -q src\tradingbotsuite` passed.
  `PYTHONPATH=src python -m pytest tests\tradingbotsuite\test_operator_ui.py -q`
  passed with 60 tests.
