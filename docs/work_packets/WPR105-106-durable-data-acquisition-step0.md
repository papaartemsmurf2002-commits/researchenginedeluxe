# WPR105-106 Durable Data Acquisition Step 0

Owner: Codex Research Agent
Stage: R105 empirical candidate factory falsification matrix
Status: closed
Created: 2026-05-20

## Goal

Add a runnable operator Step 0 that collects expanded BTCUSDT/ETHUSDT durable
public-archive data, validates source checksums and fixture-pack integrity, and
wires the generated candidate-depth fixture packs into the required research
workflow before durable readiness, historical cycles, and exact discovery.

## Allowed paths

- `.gitignore`
- `docs/KNOWN_ISSUES.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/contracts/boundary_contract.md`
- `docs/stage_reports/**`
- `docs/work_packets/**`
- `src/tradingbotsuite/data/**`
- `src/tradingbotsuite/main.py`
- `src/tradingbotsuite/operator_console.py`
- `src/tradingbotsuite/research/command_registry.py`
- `src/tradingbotsuite/research/market_data.py`
- `src/tradingbotsuite/web/operator.py`
- `src/tradingbotsuite/web/templates/research.html`
- `tests/contracts/**`
- `tests/live/**`
- `tests/tradingbotsuite/**`

## Constraints

- Use Binance Vision public archive ZIPs and `.CHECKSUM` evidence for the
  default collection path.
- Preserve existing compact fixture packs; do not delete or weaken their
  screening role.
- Generated expanded packs must remain `research_only`, `observe_only`, and
  `promotion_ready: false`.
- Readiness must be derived from validated manifests and candidate-depth row
  floors, not from job success alone.
- Research jobs must not place orders, switch runtime mode, write live config,
  write candidate packs, or change sizing behavior.

## Planned implementation

1. Add a candidate-depth Binance Vision public-archive fixture builder that
   downloads/validates monthly 15m klines, 1m klines, and aggTrades, then
   writes expanded fixture packs plus active historical-cycle/discovery specs.
2. Add an operator job and optional CLI command for the collection pipeline.
3. Update readiness/progress to prefer validated generated candidate-depth
   packs and to expose Step 0 before readiness.
4. Update the Research UI required checklist with a clear Step 0 collection
   button, storage/source notes, and dynamic active spec use.
5. Add focused tests for builder behavior, route/job wiring, progress, and
   live-boundary rejection.

## Validation target

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py tests\tradingbotsuite\test_market_data_collection.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
git diff --check
```

## Implementation summary

- Added `collect-durable-data` as a research-only CLI/operator job that
  downloads Binance Vision monthly BTCUSDT/ETHUSDT 15m, 1m, and aggTrades
  archives, verifies `.CHECKSUM` sidecars, and writes generated fixture packs
  under the configured research output directory.
- Generated packs include active readiness, historical-cycle, discovery, and
  collection-summary manifests. Existing compact checked fixtures are preserved
  as screening fallbacks.
- R104/R105 readiness now prefers validated generated candidate-depth packs
  when present. Historical-cycle and exact-discovery buttons use the active
  generated specs instead of stale compact configs.
- The Research UI required checklist now starts with Step 0 `Collect Durable
  Data`, explains that it is the required unblock path, and keeps diagnostics
  separate from the required run path.
- Step 0 is documented as the default public-archive route, not the only data
  provider route. Crypto Lake/local vendor exports and registered Hyperliquid
  archive surfaces remain available through provider diagnostics until their
  outputs are converted into the same validated candidate-depth fixture/spec
  contract.
- Source reliability checks reject checksum failures, missing/gapped primary or
  lower-timeframe rows, duplicate source bars, duplicate aggTrade IDs inside a
  partition, and candidate-depth row floors before readiness can complete.

## Validation result

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_market_data_collection.py::test_collect_candidate_depth_public_archive_fixtures_writes_active_specs_with_checksum_evidence tests\tradingbotsuite\test_market_data_collection.py::test_collect_candidate_depth_public_archive_fixtures_rejects_duplicate_source_bars -q
$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py::test_operator_research_page_keeps_hmm_knn_monitoring_observe_only tests\tradingbotsuite\test_operator_ui.py::test_operator_research_progress_api_reports_r104_milestones tests\tradingbotsuite\test_operator_ui.py::test_operator_research_job_routes_default_to_r104_deep_and_exact_specs tests\tradingbotsuite\test_operator_ui.py::test_operator_research_job_blocked_in_live_mode_without_position -q
$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_market_data_collection.py tests\tradingbotsuite\test_operator_ui.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
git diff --check
```

Result: compile passed; focused data-builder tests passed; focused operator UI
and route tests passed; the full market-data/operator UI files passed with
`69 passed`; contracts passed with `427 passed`; `git diff --check` passed.
