# Agent name

Data Agent

# Task received

Implement a research-only Binance USD-M historical chart-data collection instrument for BTC/ETH bars without touching live execution.

# Files read

- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_PROMPTS.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_INPUT_LOOKUP.md`
- `docs/tradingbotsuite_runtime/source_inputs/tradingbotsuite_critical_audit_orchestrator_next_agent.md`
- `docs/tradingbotsuite_runtime/source_inputs/orchestrator_btc_eth_perps_architecture_review_v3.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_data_agent_btc_dataset_point_in_time_audit.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_data_agent_next_dataset_regeneration_spec.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_data_agent_real_btc_lineage_quality.md`
- `src/tradingbotsuite/adapters/binance.py`
- `src/tradingbotsuite/research/entry_gate.py`
- `src/tradingbotsuite/main.py`
- `tests/tradingbotsuite/test_binance.py`
- `tests/tradingbotsuite/conftest.py`

# Files changed

- `src/tradingbotsuite/research/market_data.py`
- `src/tradingbotsuite/main.py`
- `tests/tradingbotsuite/test_market_data_collection.py`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_data_agent_binance_chart_collection.md`

# Commands/tests run

```powershell
Get-Content -Raw docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_PROMPTS.md
Get-Content -Raw docs/tradingbotsuite_runtime/HMM_MULTI_KNN_INPUT_LOOKUP.md
Get-Content -Raw docs/tradingbotsuite_runtime/source_inputs/tradingbotsuite_critical_audit_orchestrator_next_agent.md
Get-Content -Raw docs/tradingbotsuite_runtime/source_inputs/orchestrator_btc_eth_perps_architecture_review_v3.md
Get-Content -Raw src/tradingbotsuite/adapters/binance.py
Get-Content -Raw src/tradingbotsuite/research/entry_gate.py
Get-Content -Raw src/tradingbotsuite/main.py
Get-Content -Raw docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md
git status --short --branch
rg -n "fetch_historical_closed_bar_range|fetch_recent_closed_bars|INTERVAL_TO_MS|BinanceCandleClient" src/tradingbotsuite/adapters/binance.py tests/tradingbotsuite/test_binance.py
Get-Content -Raw tests/tradingbotsuite/test_binance.py
Get-Content -Raw tests/tradingbotsuite/conftest.py
Get-ChildItem -File docs/tradingbotsuite_runtime/agent_artifacts
Get-Content src/tradingbotsuite/adapters/binance.py | Select-Object -Skip 530 -First 115
Get-Content -Raw pyproject.toml
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_market_data_collection.py -q
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_binance.py::test_binance_historical_closed_bar_range_retries_on_429 -q
git diff -- src/tradingbotsuite/research/market_data.py src/tradingbotsuite/main.py tests/tradingbotsuite/test_market_data_collection.py
git status --short
```

Test results:

```text
tests/tradingbotsuite/test_market_data_collection.py: 4 passed in 0.44s
tests/tradingbotsuite/test_binance.py::test_binance_historical_closed_bar_range_retries_on_429: 1 passed in 1.15s
```

# Decisions made

- Added `collect_binance_usdm_bars()` as a research-only collector under `src/tradingbotsuite/research/market_data.py`.
- Reused `BinanceCandleClient.fetch_historical_closed_bar_range()` for historical USD-M klines instead of duplicating REST paging logic.
- Supported only `BTCUSDT` and `ETHUSDT`; intervals are validated against `INTERVAL_TO_MS`.
- Default output root is `data/research/market_data/binance_usdm/<symbol>/<interval>/`.
- Wrote deterministic JSONL bar files and a manifest JSON with `research_only: true`, `source: binance_usdm_klines`, row/hash/timestamp fields, collector version, gap and duplicate counts, and explicit notes that the output is not executable venue data.
- Added `collect-binance-bars` CLI plumbing in `src/tradingbotsuite/main.py`, including `--strict` for gap/duplicate failures.
- Strict mode writes the data and manifest first, then raises `MarketDataGapError` if gaps or duplicates are found so the failure remains auditable.

# Assumptions

- `start_time_ms` and `end_time_ms` are explicit millisecond bounds passed through to the existing Binance historical range method.
- Gap validation is based on adjacent returned closed-bar open times for the requested interval.
- The collector is an offline research utility. It does not call Hyperliquid, does not write model pointers, and does not alter runtime, engine, execution, sizing, or operator behavior.

# Open issues or blockers

None.

`docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md` showed no open issues when checked. No issue was appended.

# Handoff notes for other agents

- Downstream feature/dataset jobs can consume the JSONL and manifest as raw chart-bar inputs, but they must still preserve point-in-time joins and missingness rules.
- These files are Binance signal-source bars only. They are not Hyperliquid execution or fillability evidence.
- The current implementation covers historical chart bars only; funding, OI, premium, book, trade-flow, and liquidation journals remain separate future data-foundation work.
- The worktree already contained unrelated modified/untracked files outside this task scope; they were not reverted or edited.
