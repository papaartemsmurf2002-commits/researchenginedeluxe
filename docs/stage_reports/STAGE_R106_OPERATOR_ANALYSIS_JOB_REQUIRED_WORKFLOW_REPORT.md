# Stage R106 Operator Analysis Job Required Workflow Report

Date: 2026-05-26
Work packet: `docs/work_packets/WPR106-14-operator-analysis-job-and-required-workflow.md`
Branch role: research/experimentation only

## Boundary

This packet is research-only. It does not place orders, change live runtime
mode, write live configuration, create candidate packs, or make promotion-ready
claims. Analysis outputs remain `research_only`, `observe_only`, and
`promotion_ready: false`.

## Changes

- Added the `analyze-research-results` operator job.
- The job accepts existing `research_cycle_manifest.json` and/or
  `discovery_run_manifest.json` paths under the configured research output root.
- The job writes isolated `research_analysis.json` and
  `research_analysis.md` artifacts under `operator_runs/analysis/<job_id>`.
- Operator artifact indexing now includes `research_analysis`.
- Required workflow progress now includes a Research Analysis milestone before
  Candidate Eligibility Review.
- The Research UI now exposes `Analyze Current Evidence` in the required
  checklist and blocks UI-submitted eligibility review until an analysis
  artifact is indexed.

## Remaining Work

`ISSUE-R106-002` remains open. This packet wires the analysis step into the
operator workflow, but it does not implement the full one-button BTC/ETH
autopilot, modern-window profiles, run-to-run delta reports, simple-runner exit
policy, or frozen-entry exit lab.

## Validation

- `python -m compileall -q src\tradingbotsuite`
- `PYTHONPATH=src python -m pytest tests\research_discovery\test_analysis_report.py -q`
- `PYTHONPATH=src python -m pytest tests\tradingbotsuite\test_operator_ui.py -q`
- `PYTHONPATH=src python -m pytest tests\contracts -q`

