# WPR106-01 Central Historical Data Catalog

Owner: Codex Research Agent
Stage: R106 centralized historical data source of truth
Status: closed
Created: 2026-05-20

## Goal

Replace the one-off durable data button/workflow with a centralized historical
data catalog that records the longest validated BTCUSDT/ETHUSDT historical
data available from implemented sources, exposes one source of truth to the
operator UI and research jobs, and keeps unimplemented provider surfaces
visible without pretending they are ready.

## Allowed paths

- `configs/data/**`
- `docs/KNOWN_ISSUES.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/contracts/**`
- `docs/stage_reports/**`
- `docs/work_packets/**`
- `src/tradingbotsuite/data/**`
- `src/tradingbotsuite/main.py`
- `src/tradingbotsuite/operator_console.py`
- `src/tradingbotsuite/research/command_registry.py`
- `src/tradingbotsuite/web/operator.py`
- `src/tradingbotsuite/web/templates/research.html`
- `tests/contracts/**`
- `tests/tradingbotsuite/**`

## Constraints

- Historical data artifacts must remain `research_only`, `observe_only`, and
  `promotion_ready: false`.
- Do not claim Bybit, Hyperliquid archive, or any other provider is ingested
  unless a parser/downloader and validation contract exists.
- Preserve existing compact fixture data and generated durable data; do not
  delete prior artifacts.
- The catalog must be reproducible, hash/manifest backed, and explicit about
  source priority, coverage, gaps, row counts, and provider limitations.
- Research modules must not import live order-placement adapters, write live
  configuration, place orders, switch runtime mode, write candidate packs, or
  alter sizing behavior.

## Planned implementation

1. Add a central historical data catalog builder/resolver that uses the
   existing Binance Vision candidate-depth collector as the default implemented
   long-history source and writes a stable catalog manifest.
2. Make the catalog list all registered provider surfaces with implementation
   states: Binance Vision implemented, Crypto Lake local-export ingestion
   available, Bybit registered-only, Hyperliquid archive registered-only.
3. Add CLI/operator job/API/UI wiring for one `refresh-historical-data-catalog`
   action and make required workflow/readiness prefer the catalog over ad hoc
   durable summaries.
4. Keep `collect-durable-data` as a compatibility command/job but remove it
   from the required UI workflow.
5. Add focused tests for catalog generation, route wiring, readiness
   preference, provider limitation reporting, and UI wording.

## Validation target

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_market_data_collection.py tests\tradingbotsuite\test_operator_ui.py tests\contracts\test_data_contracts.py -q
git diff --check
```

## Validation result

Completed 2026-05-20:

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_market_data_collection.py tests\tradingbotsuite\test_operator_ui.py tests\contracts\test_data_contracts.py -q
$env:PYTHONPATH='src'; python -m pytest -q
git diff --check
```

Result: full suite passed with `1394 passed, 1 skipped`.
