# WPR104-03 Operator Console Usability Hardening

Owner: Codex Research Agent
Stage: R104 candidate validation on durable evidence
Status: closed
Created: 2026-05-17

## Goal

Make the operator Research console easier to operate during durable candidate
validation. The page should clearly show the R104 run order, progress,
completion state, recommended next action, settings, and secondary diagnostics
without adding research computation to the UI layer.

## Allowed paths

- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/work_packets/**`
- `docs/stage_reports/**`
- `src/tradingbotsuite/operator_console.py`
- `src/tradingbotsuite/persistence/sqlite_store.py`
- `src/tradingbotsuite/web/operator.py`
- `src/tradingbotsuite/web/templates/research.html`
- `src/tradingbotsuite/web/templates/timeline.html`
- `tests/tradingbotsuite/test_operator_ui.py`
- `tests/contracts/**`

## Constraints

- The UI remains a thin operator layer over existing research commands and
  indexed artifacts.
- Do not add live execution, runtime-mode changes, order placement, sizing, or
  promotion behavior.
- Keep all research surfaces `research_only`, `observe_only`, and
  `promotion_ready: false`.
- Preserve path allowlists, isolated operator output directories, and
  live-mode research-job rejection.
- Keep secondary diagnostics available but visually below the durable R104 path.

## Planned implementation

1. Add a progress/operation diagnostics API that summarizes R104 readiness,
   job state, artifact completion, next action, and workflow milestones from
   existing jobs and artifacts.
2. Rework the Research page into clearer function blocks: primary R104 command
   center, recommended settings, operation table, secondary diagnostics, status,
   jobs, and artifacts.
3. Add visible progress bars and completion badges for readiness, BTC/ETH
   cycles, BTC/ETH discovery, and candidate eligibility.
4. Improve the timeline job rendering so operator jobs show status, timing, and
   result/error state clearly.
5. Cover the API and template expectations with focused operator UI tests.

## Validation target

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

## Exit evidence

- Added `/api/operator/research/progress` as a backend-derived R104 progress
  contract for durable readiness, BTC/ETH cycles, BTC/ETH discovery, and
  candidate eligibility review.
- Scoped command-center active-run detection to primary R104 jobs so stale
  secondary jobs do not override the recommended next action.
- Kept discovery milestones waiting until matching historical-cycle artifacts
  exist, so the visual progress path follows real evidence state.
- Reworked the Research console into a command center with progress meter,
  function blocks, recommended run order, recommended defaults, maturity
  labels, and secondary diagnostics below the primary R104 path.
- Improved timeline/job rendering and backend operator-feed symbols for ETH
  durable jobs.
- Hardened shadow diagnostics and artifact refresh ordering so command-center
  progress remains usable when secondary artifact or legacy signal-history
  reads fail.
- Verified desktop and mobile Research page layout with Playwright; page-level
  horizontal overflow is `0` at `1440x1000` and `390x900`.
- Validation:
  - `python -m compileall -q src/tradingbotsuite`
  - `$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_operator_ui.py::test_operator_research_progress_api_reports_r104_milestones tests/tradingbotsuite/test_operator_ui.py::test_operator_feed_derives_job_symbol_from_request_spec_path tests/tradingbotsuite/test_operator_ui.py::test_operator_research_page_keeps_hmm_knn_monitoring_observe_only tests/tradingbotsuite/test_operator_ui.py::test_operator_timeline_page_renders_job_status_detail -q`
  - `$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_operator_ui.py -q`
  - `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`
  - `git diff --check`
