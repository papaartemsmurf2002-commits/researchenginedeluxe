# WPR106-79 - Local Binance Archive Four-Bar Mapper

## Objective

Map the existing larger local BTCUSDT/ETHUSDT Binance Vision archive cache into
the WPR106-76 four-bar HMM/KNN dataset contract, without changing the
same-entry fixed four-bar labels, event-end/purge semantics, or research-only
boundary.

This packet chooses the local archive mapping phase. It does not implement a
new OKX/Bybit/Binance venue-derived feature-intake design.

## Allowed paths

- `docs/work_packets/WPR106-79-local-binance-archive-four-bar-mapper.md`
- `docs/stage_reports/STAGE_R106_LOCAL_BINANCE_ARCHIVE_FOUR_BAR_MAPPER_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `docs/NEXT_AGENT_HANDOFF_WPR106_79_LOCAL_BINANCE_ARCHIVE_FOUR_BAR_MAPPER.md`
- `docs/contracts/boundary_contract.md`
- `src/tradingbotsuite/research/knn_four_bar.py`
- `src/tradingbotsuite/research/knn_four_bar_validation.py`
- `src/tradingbotsuite/research/command_registry.py`
- `src/tradingbotsuite/main.py`
- `src/tradingbotsuite/operator_console.py`
- `src/tradingbotsuite/web/operator.py`
- `src/tradingbotsuite/web/templates/research.html`
- `tests/tradingbotsuite/test_hmm_knn.py`
- `tests/tradingbotsuite/test_operator_ui.py`
- `data/research/hmm_knn_four_bar_archive_mapping/**`
- `data/research/hmm_knn_four_bar_validation/**`

## Out of scope

- Network collection, new venue adapters, or OKX/Bybit intake.
- Candidate packs, paper/live artifacts, order placement, position sizing,
  runtime-mode changes, or promotion claims.
- Changing HMM/KNN profitability conclusions from WPR106-78.
- Rewriting checked compact fixture packs.

## Plan

1. Audit WPR106-78 artifacts and local Binance Vision cache coverage.
2. Add a research-only local archive mapper that reads existing monthly ZIPs,
   writes the same four-bar dataset schema, records archive coverage/provenance,
   and preserves explicit missingness for absent context.
3. Add CLI and operator UI job wiring so the heavier full mapping can be queued
   instead of run inline when it is too long for an agent turn.
4. Add focused tests with tiny local ZIP fixtures for archive parsing, labels,
   purge metadata, command registration, and operator job routing.
5. Run focused validation and document the result.

## Validation target

Focused validation:

```powershell
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_hmm_knn.py tests/tradingbotsuite/test_operator_ui.py -q
```

Baseline validation if time allows:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```
