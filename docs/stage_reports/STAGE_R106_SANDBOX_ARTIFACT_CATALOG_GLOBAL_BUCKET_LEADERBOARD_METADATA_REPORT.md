# Stage R106 Sandbox Artifact Catalog Global Bucket Leaderboard Metadata Report

Date: 2026-06-19
Packet: WPR106-337
Owner: Codex Research Agent

## Summary

WPR106-337 makes sandbox artifact catalog rows surface the companion global
bucket leaderboard metadata already present in `sandbox_global_leaderboard.json`.
For `global_leaderboard` artifacts, catalog JSON and Parquet rows now include
the bucket count, bounded top-bucket count/types, bucket decision-count map, and
`sandbox_global_bucket_leaderboard.parquet` path.

The catalog still reads only the already-loaded leaderboard JSON payload. It
does not open the companion bucket Parquet, recompute bucket rows, or change any
leaderboard scoring/ranking/evidence-request behavior.

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

Agents can now discover and route to cross-run global bucket leaderboard
Parquet output from the sandbox artifact catalog itself, without manually
opening every global leaderboard JSON first or scanning companion Parquet files.
