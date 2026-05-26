# Stage R106 Research Workflow Completion Report

Date: 2026-05-26
Work packet: `docs/work_packets/WPR106-16-research-workflow-completion.md`

## Boundary

This packet is research-only. It does not place orders, change live runtime
mode, write live configuration, write candidate packs, or promote any research
artifact. New outputs remain `research_only`, `observe_only`, and
`promotion_ready: false`.

## Completed Work

- Added modern-window profile artifacts from the Historical Data Catalog. The
  catalog now records profile manifests/spec paths for a 2024+ current-market
  slice without replacing the full-window source-of-truth specs.
- Added `simple_runner_v1` to the primary-bar research exit set. The runner
  activates after a favorable close-return threshold and exits on a fixed
  favorable-return gap, while preserving deterministic close-only evidence.
- Added run-to-run delta artifacts through `research_analysis_delta.json` and
  Markdown. Missing prior analysis is recorded as a baseline blocker rather
  than failing the operator workflow.
- Added `frozen_entry_exit_lab.py`. It selects top exact-discovery leads,
  replays optional frozen entry signals against fixed holding and
  `simple_runner_v1`, writes a canonical `discovery_exit_lab_manifest.json`,
  and writes bridge-compatible candidate-gate columns. Existing BTC exact
  ledgers do not include per-entry timestamps, so the lab can truthfully write a
  blocked manifest instead of fabricating entries.
- Extended operator jobs, artifact indexing, progress milestones, Research UI
  controls, and `run-research-autopilot` sequencing through:
  research analysis -> run-to-run delta -> frozen-entry exit lab -> candidate
  eligibility.

## Runtime And Robustness

- The full exact-discovery compute path remains resumable from durable trial
  JSON records and stable run-state checkpoints from prior R106 work.
- WPR106-16 does not add another long-running compute loop. The new delta and
  frozen-entry lab are bounded artifact jobs; the lab uses top-lead selection
  with a default cap of 12 candidates and writes isolated operator outputs under
  the configured research root.
- The frozen-entry lab is fail-closed: missing interesting ledgers, missing
  frozen entry signals, missing market data, or empty market data produce a
  research-only blocked manifest with canonical gate schema.
- Eligibility receives the exit-lab manifest path from autopilot, so malformed
  or blocked exit evidence is visible as gate evidence instead of being skipped.

## Validation

- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests\backtesting\test_exit_policy_expansion.py -q`
- `$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_run_deltas.py tests\research_discovery\test_frozen_entry_exit_lab.py -q`
- `$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py -q`
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`
- `$env:PYTHONPATH='src'; python -m pytest -q` passed
  (`1439 passed, 1 skipped`).

## Remaining Evidence Work

The workflow machinery is complete for this packet, but no candidate-ready
trading claim exists. Remaining work is empirical: ETH cycle/exact discovery,
current-output analysis/delta/exit-lab/eligibility, and any future candidate
promotion gates. `ISSUE-R104-001` remains open for that evidence path.
