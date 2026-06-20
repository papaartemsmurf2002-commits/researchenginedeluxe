# Stage R106 Sandbox Analysis Bucket Rollups Report

Date: 2026-06-19
Packet: WPR106-334
Owner: Codex Research Agent

## Summary

WPR106-334 adds bounded bucket rollups to `analysis_summary.json` for sandbox
run analysis. The rollups group existing ranking rows by venue, family, exit
profile, exit variant, filter variant, and venue/family so agents can identify
promising or failing run clusters without scanning every ranking row.

Each rollup includes sandbox boundary flags, result and status counts,
positive-net counts, descriptor-only evidence-request counts, best
representative trial metadata, and explicit non-authorizing flags. The rollups
are derived only from integrity-checked rankings and evidence-request source
trial IDs.

## Boundary

- No sandbox sweep, replay command, strict validation, provider download, or
  candidate-pack generation was executed by this packet.
- No paper/live signal, sizing instruction, order instruction, runtime-mode
  change, live configuration write, or promotion claim was created.
- Scoring, ranking math, falsification decisions, blocker/rejection semantics,
  evidence-request selection, trial IDs, archive routing, preflight behavior,
  source-integrity behavior, replay readiness, strict-validation descriptor
  queues, artifact catalog sidecars, and the 2024+ window policy are preserved.

## Validation

- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "sandbox_analysis_summarizes_compact_artifacts"`
  passed with 1 passed and 173 deselected.
- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q`
  passed with 174 passed.
- `$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite`
  passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q`
  passed with 11 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`
  passed with 461 passed.

## Result

The sandbox analysis surface is more agent-ready for rapid iteration:
`analysis_summary.json` now exposes compact, bounded bucket leaderboards over
the rows agents already trust, while remaining research-only, observe-only,
sandbox-only, and promotion-ready false.
