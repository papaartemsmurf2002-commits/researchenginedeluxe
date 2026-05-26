# Stage R106 Operator Research Autopilot Sequencer Report

Date: 2026-05-26
Work packet: `docs/work_packets/WPR106-15-operator-research-autopilot-sequencer.md`
Branch role: research/experimentation only

## Boundary

This packet is research-only. It does not place orders, change live runtime
mode, write live configuration, create candidate packs, or make promotion-ready
claims. Autopilot manifests remain `research_only`, `observe_only`, and
`promotion_ready: false`.

## Changes

- Added the `run-research-autopilot` operator job.
- Added the `/api/operator/research/jobs/run-research-autopilot` route with
  bounded BTC/ETH-only inputs.
- The autopilot calls existing isolated catalog, historical-cycle, discovery,
  research-analysis, and candidate-eligibility helpers directly. It does not
  queue child jobs, so it cannot deadlock behind the single operator worker.
- Existing current artifacts are skipped rather than rerun.
- The job writes
  `operator_runs/research_autopilot/<job_id>/research_autopilot_manifest.json`
  with executed, skipped, failed, and blocked step records.
- Operator artifact indexing now includes `research_autopilot`.
- The Research UI now exposes a primary `Run Research Autopilot` action.

## Remaining Work

`ISSUE-R106-002` remains open. This packet implements the bounded sequencer,
but it does not generate modern-window specs, write run-to-run deltas, implement
simple-runner exits, or simulate frozen-entry alternative exit policies.

## Validation

- `python -m compileall -q src\tradingbotsuite`
- `PYTHONPATH=src python -m pytest tests\tradingbotsuite\test_operator_ui.py -q`
- `PYTHONPATH=src python -m pytest tests\research_discovery\test_analysis_report.py -q`
- `PYTHONPATH=src python -m pytest tests\contracts -q`

