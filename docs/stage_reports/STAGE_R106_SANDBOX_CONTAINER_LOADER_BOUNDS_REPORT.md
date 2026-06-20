# Stage R106 Sandbox Container Loader Bounds Report

Date: 2026-06-20
Packet: `WPR106-375-sandbox-container-loader-bounds`

## Summary

WPR106-375 adds bounded-read guardrails to the sandbox market-data ZIP/TAR
container loader. Selected container member counts, per-member raw bytes, total
selected raw bytes, and gzip decompression bytes are now bounded by explicit
loader limits. Oversized inputs fail closed with explicit `ValueError` reasons
such as `container_member_bytes_limit_exceeded`,
`container_selected_member_count_limit_exceeded`, and
`container_member_decompressed_bytes_limit_exceeded`.

Accepted container normalization metadata now records the active loader limits
and selected-member declared byte totals for reproducibility diagnostics. The
loader still reads members in memory and does not claim full streaming
throughput; this packet narrows the unbounded-container risk called out by the
post-audit roadmap.

## Validation

- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_market_data_container_limits.py -q`
  - `4 passed`
- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q`
  - `212 passed`
- `python -m compileall -q src\tradingbotsuite`
  - passed
- `$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q`
  - `26 passed`
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`
  - `462 passed`
- `git diff --check`
  - passed with existing LF-to-CRLF warnings only

## Boundary Statement

This packet changes local sandbox archive-loader guardrails only. It does not
download provider data, mutate archive manifests or source files, execute
sweeps, execute strict validation, write candidate packs, create paper/live
signals, define sizing, place orders, change runtime mode, write live
configuration, claim candidate evidence, or authorize promotion.
