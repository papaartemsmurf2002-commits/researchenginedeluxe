# Stage R106 Sandbox Numeric Timestamp Unit Normalizer Report

Date: 2026-06-19
Packet: `WPR106-290-sandbox-numeric-timestamp-unit-normalizer`
Owner: Codex Research Agent
Status: closed

## Summary

WPR106-290 fixes sandbox market-data timestamp normalization for local venue
exports that use numeric timestamp columns. Numeric aliases such as
`timestamp`, `time`, `ts`, `open_time`, and venue-specific equivalents are now
interpreted deterministically as epoch seconds, milliseconds, microseconds, or
nanoseconds by magnitude before the 2024+ sandbox filter is applied.

This prevents valid 2024+ millisecond or microsecond archives from being
misread as 1970-era timestamps and silently dropped before archive coverage,
preflight, or sweeps can use them.

## Implementation

- Added numeric epoch-unit inference for seconds, milliseconds, microseconds,
  and nanoseconds.
- Applied the inference to all timestamp aliases, not only `ts` or
  `open_time`.
- Preserved ISO/string timestamp parsing.
- Preserved compact `YYYYMMDD` values as calendar dates rather than Unix epoch
  values.
- Added regression coverage for literal `timestamp` millisecond exports,
  `time` microsecond exports, compact `YYYYMMDD` values, and archive manifest
  inclusion with numeric millisecond timestamps.

## Boundary

This packet only changes local sandbox market-data timestamp normalization. It
does not execute strict validation, write candidate packs, create paper/live
signals, define sizing, place orders, change runtime mode, write live
configuration, mutate source files, download provider data, or claim promotion
readiness.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "numeric_timestamp or numeric_time or compact_yyyymmdd"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Results:

- 4 focused timestamp tests passed.
- 134 sandbox tests passed.
- Package compileall passed.
- 11 import-boundary tests passed.
- 461 contract tests passed.
