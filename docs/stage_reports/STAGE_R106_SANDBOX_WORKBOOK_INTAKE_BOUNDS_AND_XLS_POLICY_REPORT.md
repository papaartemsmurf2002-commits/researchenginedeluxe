# Stage R106 Sandbox Workbook Intake Bounds And Xls Policy Report

Date: 2026-06-20
Packet: `WPR106-378-sandbox-workbook-intake-bounds-and-xls-policy`

## Summary

WPR106-378 closes the post-audit workbook intake M2/M9 gaps for the Rapid
Strategy Iteration Sandbox. Legacy `.xls` strategy catalogs are now recognized
as a fail-closed unsupported format instead of being advertised as clean-install
supported. Direct loads raise `unsupported_legacy_xls_strategy_catalog`, and
the strategy catalog materializer records that reason in skipped-source repair
rows.

The standard-library `.xlsx` fallback parser now bounds workbook ZIP member
count, per-member XML bytes, total parsed XML bytes, sheet count,
shared-string count, sheet row count, sheet cell count, and sheet column count.
Oversized or unsafe fallback workbooks fail closed with explicit loader errors
such as `xlsx_member_bytes_limit_exceeded` and
`xlsx_sheet_rows_limit_exceeded`; accepted workbook diagnostics record the
active fallback limits for reproducibility.

## Validation

- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -k "xlsx or xls or workbook" -q`
  - `9 passed, 186 deselected`
- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q`
  - `216 passed`
- `python -m compileall -q src\tradingbotsuite`
  - passed
- `$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q`
  - `26 passed`

## Boundary Statement

This packet changes only local sandbox strategy catalog intake guardrails and
diagnostics. It does not download provider data, mutate source catalogs,
execute sandbox sweeps, execute strict validation, write candidate packs,
create paper/live signals, define sizing, place orders, change runtime mode,
write live configuration, claim candidate evidence, or authorize promotion.
