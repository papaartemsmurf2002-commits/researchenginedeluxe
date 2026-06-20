# Stage R106 Sandbox Global Bucket Leaderboard Report

Date: 2026-06-19
Packet: WPR106-336
Owner: Codex Research Agent

## Summary

WPR106-336 adds a cross-run bucket leaderboard to sandbox global leaderboard
artifacts. `sandbox_global_leaderboard.json` now includes bounded
`top_buckets`, and global leaderboard output now writes
`sandbox_global_bucket_leaderboard.parquet`.

Bucket rows are derived from the same integrity-checked ranking rows and
descriptor-only evidence requests already loaded by the global leaderboard.
They group results by venue, symbol, venue/symbol, family, exit profile, exit
variant, filter variant, and venue/family, carrying compact counts, best
representative trial metadata, evidence-request counts, decision labels, and
explicit non-authorizing flags.

## Boundary

- The packet does not execute sandbox sweeps, replay commands, strict
  validation, provider downloads, or candidate-pack generation.
- No paper/live signal, sizing instruction, order instruction, runtime-mode
  change, live configuration write, strategy-catalog mutation, archive
  manifest/source mutation, or promotion claim was created.
- Scoring, ranking math, falsification decisions, blocker/rejection semantics,
  evidence-request selection, trial IDs, archive routing, preflight behavior,
  source-integrity behavior, replay readiness, and the 2024+ window policy are
  preserved.

## Validation

- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "global_leaderboard"`
  passed with 2 passed and 172 deselected.
- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q`
  passed with 174 passed.
- `$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite`
  passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q`
  passed with 11 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`
  passed with 461 passed.

## Result

Agents can now rank cross-run venue, symbol, family, exit, and filter clusters
from the global leaderboard command without requiring every run to have a
pre-written `analysis_summary.json`, while all outputs remain research-only,
observe-only, sandbox-only, and promotion-ready false.
