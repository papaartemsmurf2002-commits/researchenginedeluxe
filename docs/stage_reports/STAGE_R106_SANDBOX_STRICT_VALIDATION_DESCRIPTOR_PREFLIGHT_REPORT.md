# Stage R106 Sandbox Strict Validation Descriptor Preflight Report

Date: 2026-06-20
Packet: `WPR106-370-sandbox-strict-validation-descriptor-preflight`

## Summary

WPR106-370 adds a read-only strict-validation descriptor preflight for the
rapid strategy sandbox. The new
`preflight-rapid-strategy-sandbox-validation-requests` command imports an
existing descriptor-only strict-validation request bundle and writes compact
JSON/Parquet planning reports with accepted and blocked descriptor rows.

Accepted rows mean only `accepted_for_strict_validation_planning`. Blocked rows
carry concrete repair reasons, including missing source context, missing
archive identity, proxy-only strategy, missing validation requirements,
pre-2024 windows, and candidate-pack or promotion flags.

## Validation

- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "strict_validation_descriptor_preflight or cli_command_preflights_strict_validation_bundle"`
  - `4 passed, 182 deselected`
- `$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q`
  - `24 passed`
- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q`
  - `200 passed`
- `python -m compileall -q src\tradingbotsuite`
  - passed
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`
  - `461 passed`
- `git diff --check`
  - passed with existing LF-to-CRLF warnings only

## Boundary Statement

The preflight is descriptor-only and planning-only. It does not execute strict
validation, write historical-cycle specs, write candidate packs, create
paper/live behavior, define sizing, place orders, change runtime mode, write
live configuration, claim candidate evidence, or claim promotion readiness.
