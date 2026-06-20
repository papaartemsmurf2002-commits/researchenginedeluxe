# WPR106-78 - Four-Bar Larger Validation Run And Handoff

## Purpose

Run the WPR106-77 four-bar KNN larger-validation command locally with an
extended timeout after the operator/short command path did not work for the
user, then write a next-agent handoff and goal prompt that preserve the
research-only boundary.

## Scope

Allowed edit paths:

- `docs/work_packets/WPR106-78-four-bar-larger-validation-run-and-handoff.md`
- `docs/stage_reports/STAGE_R106_FOUR_BAR_LARGER_VALIDATION_RUN_AND_HANDOFF_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `docs/NEXT_AGENT_HANDOFF_WPR106_78_FOUR_BAR_KNN_LARGER_VALIDATION.md`

Allowed generated research-output paths:

- `data/research/hmm_knn_four_bar_validation/wpr106_78_full_run/**`

Read-only reference paths:

- `AGENTS.md`
- `docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md`
- `docs/work_packets/WPR106-76-four-bar-lead-discovery-bridge.md`
- `docs/work_packets/WPR106-77-four-bar-knn-larger-validation-runner.md`
- `docs/stage_reports/STAGE_R106_FOUR_BAR_LEAD_DISCOVERY_BRIDGE_REPORT.md`
- `docs/stage_reports/STAGE_R106_FOUR_BAR_KNN_LARGER_VALIDATION_RUNNER_REPORT.md`
- `src/tradingbotsuite/research/knn_four_bar_validation.py`
- `data/research/hmm_knn_four_bar_validation/wpr106_77_cli_smoke/**`

Out of scope:

- Code changes unless the run exposes a concrete blocker that cannot be
  documented precisely.
- Candidate-pack creation, paper/live artifacts, promotion artifacts, or
  promotion-ready claims.
- Live, paper, order-placement, sizing, runtime-mode, or live-configuration
  behavior.
- Venue intake implementation.

## Plan

1. Run `run-four-bar-knn-larger-validation` from the repo root with a large
   local timeout and output under
   `data/research/hmm_knn_four_bar_validation/wpr106_78_full_run/`.
2. Inspect the validation manifest and summary if the command completes; if it
   fails, record the exact command, timeout, output directory, and failure.
3. Write a next-agent handoff file with the current state, command, artifact
   paths, and explicit next direction.
4. Include a next `/goal` prompt that references the official OpenAI developer
   portal for general Codex/developer guidance while keeping repo work governed
   by `AGENTS.md`, the ledger, and the fuse.

## Research Boundary

All outputs are research-only, observe-only, and promotion-disabled. Larger
validation evidence is not a live signal, not a candidate pack, not paper/live
readiness, and not promotion evidence.

## Exit Evidence

Status: closed on 2026-06-09.

The local command was run with a 10,800,000 ms timeout:

```powershell
$env:PYTHONPATH='src'; python -m tradingbotsuite.main run-four-bar-knn-larger-validation --output-dir hmm_knn_four_bar_validation\wpr106_78_full_run --sample-rows-per-interval 8000 --workers 1 --skip-monitor
```

The process completed and wrote
`data/research/hmm_knn_four_bar_validation/wpr106_78_full_run/`, but both
matrices failed because the current BTC/ETH fixture roots are compact contract
fixtures. Each generated dataset contains only 64 rows per symbol, so selected
15m->1h rows failed with `ValueError: No objects to concatenate` and selected
1h->4h rows failed with
`ValueError: dataset is too small for HMM/KNN walk-forward research`.

Next-agent handoff:
`docs/NEXT_AGENT_HANDOFF_WPR106_78_FOUR_BAR_KNN_LARGER_VALIDATION.md`

Stage report:
`docs/stage_reports/STAGE_R106_FOUR_BAR_LARGER_VALIDATION_RUN_AND_HANDOFF_REPORT.md`

Known issue opened:
`ISSUE-R106-023`
