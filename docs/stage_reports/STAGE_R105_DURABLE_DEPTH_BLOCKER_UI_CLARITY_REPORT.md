# Stage R105 Durable Depth Blocker UI Clarity Report

Date: 2026-05-20
Work packet: `docs/work_packets/WPR105-105-durable-depth-blocker-ui-clarity.md`
Status: closed

## Summary

WPR105-105 clarifies the operator UX for blocked durable data depth. The block is
intentional and is not a compute job failure. The required checklist now tells
the operator that compact fixtures cannot be promoted into candidate-depth
evidence by pressing a run button.

## Implementation Notes

- The first required checklist card now states that a data-depth block requires
  expanded BTC/ETH durable historical fixture data.
- The blocked `Durable data depth` milestone now offers `Show Data Gap`, which
  refreshes readiness and shows the required data action, instead of a disabled
  `Run` button.
- Other blocked or waiting milestone buttons are labeled `Data Required` or
  `Waiting` so they do not look like broken compute actions.
- Readiness feedback now explains the unblock path: add expanded BTC/ETH
  durable historical fixture packs and updated readiness hashes, then run
  readiness again.

## Boundary

No gates were weakened. No live execution, order placement, runtime-mode
mutation, live configuration write, promotion behavior, candidate-pack write, or
sizing behavior was added.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py::test_operator_research_page_keeps_hmm_knn_monitoring_observe_only tests\tradingbotsuite\test_operator_ui.py::test_operator_research_progress_api_reports_r104_milestones -q
```

Result: 2 focused tests passed.
