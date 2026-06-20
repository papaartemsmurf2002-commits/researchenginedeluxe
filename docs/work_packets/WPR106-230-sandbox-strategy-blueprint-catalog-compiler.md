# WPR106-230 Sandbox Strategy Blueprint Catalog Compiler

Status: closed
Owner: Codex Research Agent
Created: 2026-06-18

## Objective

Make the Rapid Strategy Iteration Sandbox ingest existing repo strategy configs
and spreadsheet-like lead catalogs without requiring precomputed signal columns.
The packet adds a sandbox-only blueprint compiler that converts those inputs
into deterministic, non-promotable strategy rows and materializes completed-bar
proxy signals inside the fast fixed-hold sweep.

This is an iteration-speed layer only. It must not change strict strategy
plugins, historical research-cycle gates, candidate-pack writers, live/paper
behavior, sizing, order placement, runtime mode, or promotion behavior.

## Scope

- Add sandbox strategy blueprints for simple completed-bar OHLCV proxy signals:
  close momentum, range reversion, and volatility breakout.
- Compile existing repo-style `configs/strategies/*.json` payloads into
  sandbox `StrategyCatalogRow` entries with deterministic signal columns and
  explicit source metadata.
- Normalize spreadsheet-like lead rows from workbooks/tables into sandbox
  proxy strategies when they do not already contain `signal_column`.
- Materialize blueprint signals only after the sandbox 2024+ market window is
  applied so pre-2024 rows cannot influence signals.
- Preserve existing direct `signal_column` catalog behavior for already
  prepared sandbox catalogs.
- Add focused tests for config compilation, spreadsheet-like lead ingestion,
  completed-bar signal materialization, and non-promotable result payloads.
- Update sandbox docs and stage closeout docs.

## Allowed Paths

- `docs/work_packets/WPR106-230-sandbox-strategy-blueprint-catalog-compiler.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_STRATEGY_BLUEPRINT_CATALOG_COMPILER_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/**`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a new blocking evidence or boundary risk is
  discovered

## Acceptance Evidence

- Existing direct sandbox catalogs with `hypothesis_id`, `family`, and
  `signal_column` still load unchanged.
- Existing repo strategy JSON configs can be passed as sandbox strategy catalogs
  and compile into deterministic sandbox rows.
- Spreadsheet-like lead/catalog rows can compile into sandbox proxy rows without
  arbitrary code execution.
- Blueprint signals are generated from completed 2024+ market rows and do not
  use pre-2024 history.
- Fast fixed-hold sweeps can screen compiled blueprint rows and produce stable
  trial IDs.
- All outputs remain `research_only`, `observe_only`, `promotion_ready: false`,
  `sandbox_only`, `candidate_evidence: false`, and
  `candidate_pack_eligible: false`.
- Validation includes focused sandbox tests, package compile, import-boundary
  coverage, and contract baseline unless a narrower failure requires diagnosis.

## Boundary

Blueprints are proxy research hypotheses, not production strategy plugins.
They may request later strict validation but cannot create candidate evidence,
candidate packs, live/paper signals, order instructions, sizing instructions,
runtime changes, live configuration writes, or promotion claims.

## Completion Notes

Implemented and closed on 2026-06-18. The packet added sandbox static blueprint
proxies, repo strategy-config compilation, spreadsheet-like lead compilation,
standard-library `.xlsx` fallback intake for environments without `openpyxl`,
and fixed-hold sweep signal materialization after the 2024+ market-window
filter.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Focused sandbox validation passed with 20 tests. Import-boundary validation
passed with 11 tests. Package compileall passed. Real-input smoke checks loaded
`configs/strategies` into 30 compiled sandbox proxy rows and loaded
`outputs/019ed9da-c03f-7a01-ba1a-8a28806bc270/repo_research_performance_correlation_audit.xlsx`
into 17 compiled rows through the no-`openpyxl` fallback path.

The full contract baseline passed once before the `.xlsx` fallback edit with
461 tests. After the fallback edit, repeated contract attempts reached 460
passed tests and failed only during asyncio event-loop fixture setup for
`test_provider_kline_fixture_pack_builder_accepts_collected_binance_context_manifest`
with Windows `WinError 10055` socket-buffer/resource exhaustion, before that
test body executed. The same setup error reproduced under the Windows selector
event-loop policy and after a delayed retry, so the final post-fallback full
contract run remains environmentally blocked rather than assertion-failed.
