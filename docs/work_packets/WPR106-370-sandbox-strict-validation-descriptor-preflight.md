# WPR106-370 - Sandbox Strict Validation Descriptor Preflight

## Status

closed

## Objective

Add a schema-backed, read-only preflight for sandbox strict-validation request
bundles. The preflight should import descriptor-only bundles, classify each
descriptor as accepted for strict-validation planning or blocked with concrete
reasons, and write compact JSON/Parquet reports without executing strict
validation or writing candidate artifacts.

## Dependencies

- `RAPID_STRATEGY_SANDBOX_AUDIT.md`
- `docs/RESEARCH_ENGINE_DELUXE_COMPLETION_ROADMAP.md`
- `docs/work_packets/WPR106-236-sandbox-strict-validation-request-bundle.md`
- `docs/work_packets/WPR106-259-sandbox-strict-request-source-context.md`
- `docs/work_packets/WPR106-369-sandbox-end-to-end-venue-expansion-fixture-smoke.md`

## Allowed paths

- `src/tradingbotsuite/research_sandbox/strict_validation_preflight.py`
- `src/tradingbotsuite/research_sandbox/__init__.py`
- `src/tradingbotsuite/main.py`
- `src/tradingbotsuite/research/command_registry.py`
- `tests/research_sandbox/**`
- `tests/live/test_cli_boundary.py`
- `docs/contracts/sandbox_research_contract.md`
- `docs/contracts/boundary_contract.md`
- `docs/work_packets/WPR106-370-sandbox-strict-validation-descriptor-preflight.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_STRICT_VALIDATION_DESCRIPTOR_PREFLIGHT_REPORT.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`

## Boundary constraints

- Descriptor import/preflight only.
- No strict-validation execution.
- No candidate-pack writes.
- No promotion, candidate-evidence, paper/live signal, sizing, order-placement,
  runtime-mode-change, or live-config-write behavior.
- Accepted rows mean `accepted_for_strict_validation_planning` only.
- Pre-2024 windows, proxy-only strategies, missing source context, missing
  archive identity, missing validation requirements, and unsafe boundary flags
  must block deterministically.

## Acceptance criteria

- A bundle preflight command reads an existing
  `strict_validation_request_bundle.json` or
  `suite_strict_validation_request_bundle.json` under the configured research
  output root.
- The preflight writes `strict_validation_descriptor_preflight.json` and
  `strict_validation_descriptor_preflight.parquet`.
- Every row carries sandbox boundary flags and non-authorizing status fields.
- Accepted rows preserve source context, archive identity, trial IDs, metrics,
  exit/filter/cost/fill assumptions, and validation requirements.
- Blocked rows report explicit blocker reasons without raising on ordinary
  descriptor repair issues.
- Boundary violations fail closed before any output is written.
- CLI paths are contained under the research output root and live-mode
  rejection covers the new command.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "strict_validation_descriptor_preflight or cli_command_preflights_strict_validation_bundle"
$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
git diff --check
```

## Stop conditions

- Any path allows output outside the configured research root.
- Any preflight row can claim candidate evidence, promotion readiness,
  candidate-pack eligibility, paper/live behavior, sizing, order placement,
  runtime-mode change, or live config writes.
- The preflight executes strict validation or writes candidate-pack artifacts.

## Exit evidence

- Added `preflight-rapid-strategy-sandbox-validation-requests`, a research
  command that reads descriptor-only sandbox strict-validation request bundles
  under the configured research output root and writes
  `strict_validation_descriptor_preflight.json` plus
  `strict_validation_descriptor_preflight.parquet`.
- Added row-level strict-validation planning statuses:
  `accepted_for_strict_validation_planning` and blocked rows with explicit
  reasons for missing source context, missing archive identity, proxy-only
  strategies, missing validation requirements, pre-2024 windows, and candidate
  pack or promotion flags.
- Boundary-unsafe bundles fail closed before report files are written.
- Focused validation passed:
  `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "strict_validation_descriptor_preflight or cli_command_preflights_strict_validation_bundle"`
  reported 4 passed / 182 deselected;
  `$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q`
  reported 24 passed;
  `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q`
  reported 200 passed;
  `python -m compileall -q src\tradingbotsuite` passed;
  `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`
  reported 461 passed;
  `git diff --check` passed with existing LF-to-CRLF warnings only.
- The bridge remains descriptor-only and planning-only. It does not execute
  strict validation, write historical-cycle specs, write candidate packs,
  create paper/live behavior, define sizing, place orders, change runtime mode,
  write live configuration, claim candidate evidence, or claim promotion
  readiness.
