# WPR105-107 Bybit And Hyperliquid Provider Surface Audit

Owner: Codex Research Agent
Stage: R105 empirical candidate factory falsification matrix
Status: closed
Created: 2026-05-20

## Goal

Clarify provider coverage after the durable Step 0 work by registering Bybit as
a conservative archive/provider surface and documenting the current
Hyperliquid archive state.

## Allowed paths

- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/stage_reports/**`
- `docs/work_packets/**`
- `docs/contracts/**`
- `docs/tradingbotsuite_runtime/**`
- `src/tradingbotsuite/data/**`
- `src/tradingbotsuite/research/archive_sources.py`
- `src/tradingbotsuite/research/data_pipeline.py`
- `src/tradingbotsuite/web/templates/research.html`
- `tests/contracts/**`
- `tests/tradingbotsuite/**`

## Constraints

- Do not claim Bybit or Hyperliquid archive ingestion is implemented unless
  the code actually parses and validates their files.
- Keep registered-only sources diagnostic, research-only, observe-only, and
  `promotion_ready: false`.
- Do not weaken candidate-depth readiness, source-capability gates, or
  protected missingness checks.
- Do not add live execution, order placement, runtime-mode mutation, live
  configuration writes, candidate-pack writes, or sizing changes.

## Planned implementation

1. Add a registered-only Bybit archive source descriptor and provider
   capability entries for durable-relevant market-data families.
2. Keep Hyperliquid archive explicitly registered-only until local archive
   ingestion and local account-journal reconciliation are implemented.
3. Update UI/docs so Step 0 is clearly the default Binance Vision public
   archive route, while Bybit, Crypto Lake, and Hyperliquid remain provider
   surfaces with different implementation states.
4. Add focused tests for provider descriptors, not-implemented intake
   manifests, and provider capability metadata.

## Validation target

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_data_contracts.py tests\tradingbotsuite\test_archive_sources.py tests\tradingbotsuite\test_data_pipeline.py::test_archive_provider_descriptors_cover_expected_contract_sources tests\tradingbotsuite\test_data_pipeline.py::test_prepare_hmm_knn_research_data_intake_writes_provider_journal_and_quality_manifests tests\tradingbotsuite\test_operator_ui.py::test_operator_research_page_keeps_hmm_knn_monitoring_observe_only -q
git diff --check
```

## Implementation summary

- Added `bybit_archive` to archive-source descriptors and provider capability
  metadata as a registered-only diagnostic source.
- Kept `hyperliquid_archive` registered-only and explicit about local
  account-journal reconciliation requirements.
- Updated provider diagnostics UI/docs so Step 0 is the default Binance Vision
  path, while Bybit, Crypto Lake, and Hyperliquid remain visible provider
  surfaces with different implementation states.
- Added focused tests for descriptors, registered-only manifests, provider
  pipeline not-implemented manifests, and UI wording.

## Validation result

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_data_contracts.py tests\tradingbotsuite\test_archive_sources.py tests\tradingbotsuite\test_data_pipeline.py::test_archive_provider_descriptors_cover_expected_contract_sources tests\tradingbotsuite\test_data_pipeline.py::test_prepare_hmm_knn_research_data_intake_writes_provider_journal_and_quality_manifests tests\tradingbotsuite\test_operator_ui.py::test_operator_research_page_keeps_hmm_knn_monitoring_observe_only -q
git diff --check
```

Result: compile passed; focused provider and UI validation passed with
`34 passed`; `git diff --check` passed.
