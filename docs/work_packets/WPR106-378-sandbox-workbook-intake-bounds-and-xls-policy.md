# WPR106-378 - Sandbox Workbook Intake Bounds And Xls Policy

## Status

closed

## Objective

Close the remaining post-audit workbook intake safety gaps by making legacy
`.xls` strategy catalogs explicitly unsupported in clean sandbox installs and
adding bounded-read guardrails to the standard-library `.xlsx` fallback parser.

## Dependencies

- `RAPID_STRATEGY_SANDBOX_AUDIT.md`
- `docs/RESEARCH_ENGINE_DELUXE_COMPLETION_ROADMAP.md`
- `docs/work_packets/WPR106-375-sandbox-container-loader-bounds.md`
- `docs/work_packets/WPR106-377-sandbox-publication-coherence.md`

## Allowed paths

- `src/tradingbotsuite/research_sandbox/intake.py`
- `src/tradingbotsuite/research_sandbox/strategy_catalog_materializer.py`
- `tests/research_sandbox/test_sandbox_foundation.py`
- `docs/contracts/sandbox_research_contract.md`
- `docs/work_packets/WPR106-378-sandbox-workbook-intake-bounds-and-xls-policy.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_WORKBOOK_INTAKE_BOUNDS_AND_XLS_POLICY_REPORT.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`

## Boundary constraints

- Preserve local strategy catalog intake only; do not add provider downloads,
  network access, autonomous execution, or source catalog mutation.
- Preserve accepted `.xlsx`, CSV, TSV, JSON, and Parquet strategy catalog
  semantics.
- Oversized, malformed, or legacy workbook inputs must produce explicit loader
  or repair-queue blockers instead of silent truncation or fabricated rows.
- Do not execute sandbox sweeps, strict validation, replay commands,
  candidate-pack writes, paper/live behavior, sizing, order placement, runtime
  mode changes, live config writes, candidate-evidence claims, or promotion
  claims.

## Acceptance criteria

- `.xls` files are reported as explicitly unsupported unless a later packet
  adds a declared dependency and tests.
- The `.xlsx` fallback bounds workbook ZIP member count, per-member XML bytes,
  total XML bytes, sheet count, shared-string count, row count, cell count, and
  column count.
- Bounds failures raise explicit `ValueError` messages that direct loaders and
  the catalog materializer surface as blocker/repair reasons.
- Accepted workbook diagnostics record the active fallback limits for
  reproducibility.
- Focused sandbox workbook tests, full sandbox tests, compile, live CLI
  boundary tests, and diff hygiene pass.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -k "xlsx or xls or workbook" -q
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q
git diff --check
git diff --cached --check
```

Exit evidence:

- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -k "xlsx or xls or workbook" -q`
  - `9 passed, 186 deselected`
- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q`
  - `216 passed`
- `python -m compileall -q src\tradingbotsuite`
  - passed
- `$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q`
  - `26 passed`

## Stop conditions

- Accepted small `.xlsx` workbook catalogs change strategy rows or sheet
  provenance.
- Materializer repair rows hide load errors or drop workbook blockers.
- Any sandbox output can be interpreted as strict validation evidence,
  candidate evidence, candidate-pack eligibility, paper/live signal, sizing, or
  promotion-ready output.
