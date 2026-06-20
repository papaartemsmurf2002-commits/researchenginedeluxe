# Stage R106 Sandbox Artifact Catalog Global Bucket Top-Buckets Sidecar Report

Date: 2026-06-19
Packet: WPR106-338
Owner: Codex Research Agent

## Summary

WPR106-338 adds
`sandbox_artifact_catalog_global_bucket_top_buckets.parquet`, a catalog-owned
Parquet sidecar that flattens bounded `top_buckets` rows from indexed
`sandbox_global_leaderboard.json` artifacts.

The sidecar is derived only from global leaderboard JSON payloads already loaded
during catalog indexing. It exposes source leaderboard paths, companion bucket
Parquet paths, bucket identity, compact counts, decision labels, best
representative trial metadata, and non-authorizing flags. It is also registered
in the catalog sidecar index with post-write file existence, byte-size, and
SHA-256 metadata.

## Boundary

- The packet does not execute sandbox sweeps, replay commands, strict
  validation, provider downloads, or candidate-pack generation.
- No paper/live signal, sizing instruction, order instruction, runtime-mode
  change, live configuration write, strategy-catalog mutation, archive
  manifest/source mutation, or promotion claim was created.
- The catalog does not open or recompute `sandbox_global_bucket_leaderboard.parquet`.
- Scoring, ranking math, falsification decisions, blocker/rejection semantics,
  evidence-request selection, trial IDs, archive routing, preflight behavior,
  source-integrity behavior, replay readiness, and the 2024+ window policy are
  preserved.

## Validation

- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "global_leaderboard or artifact_catalog"`
  passed with 4 passed and 170 deselected.
- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q`
  passed with 174 passed.
- `$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite`
  passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q`
  passed with 11 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`
  passed with 461 passed.

## Result

Agents can now query bounded cross-run global bucket leaders directly from
artifact catalog output and its sidecar index, without opening each global
leaderboard JSON or scanning companion bucket Parquet files first.
