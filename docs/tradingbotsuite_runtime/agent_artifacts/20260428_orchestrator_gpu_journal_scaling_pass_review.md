# Orchestrator Review: GPU, Journal, Scaling, And Boundary Pass

Date: 2026-04-28

## Scope Reviewed

This pass integrated four agent lanes:

- KNN Agent: optional research-only CuPy Lorentzian backend with CPU default and fake-CuPy tests.
- Backtest Agent: bounded parallel HMM/KNN experiment runner with stable cache keys, deterministic summary ordering, runtime/cache fields, and promotion-failure aggregation.
- Data/Feature Agent: first standalone Binance-style append-only market journal and deterministic replay contract.
- Monitoring/Execution-Risk Agent: strict research-boundary metadata and validation for artifacts, monitoring reports, experiment manifests, and journal manifests.

## Boundary Check

No live execution, sizing, Hyperliquid adapter, runtime control, Control page, or operator live-control files changed in the final combined diff.

Explicit boundary diff was empty for:

- `src/tradingbotsuite/adapters/execution.py`
- `src/tradingbotsuite/core/engine.py`
- `src/tradingbotsuite/config.py`
- `src/tradingbotsuite/runtime.py`
- `src/tradingbotsuite/web/operator.py`
- `src/tradingbotsuite/web/templates/control.html`
- `src/tradingbotsuite/operator_commands.py`

All new outputs remain research-only or observe-only. Promotion remains false unless a future explicit promotion process is approved.

## Validation

Focused integration:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_market_journal.py tests/tradingbotsuite/test_hmm_knn.py tests/tradingbotsuite/test_live_readiness.py tests/tradingbotsuite/test_market_data_collection.py tests/tradingbotsuite/test_execution_journal.py tests/tradingbotsuite/test_operator_ui.py -q
```

Result: `78 passed in 21.29s`.

Full regression:

```powershell
$env:PYTHONPATH='src'; python -m pytest -q
```

Result: `452 passed in 139.60s`.

CLI smoke:

```powershell
$env:PYTHONPATH='src'; python -m tradingbotsuite.main run-hmm-knn-experiments --help
$env:PYTHONPATH='src'; python -m tradingbotsuite.main write-hmm-knn-sweep-datasets --help
```

Result: both commands parsed successfully, including `run-hmm-knn-experiments --workers`.

Whitespace:

```powershell
git diff --check
```

Result: exit code `0`; only line-ending warnings from Git.

## Orchestrator Notes

- The optional CuPy backend is correctly isolated behind `knn.distance_backend`; default config remains `cpu`.
- The experiment runner parallelism uses independent cache directories and re-sorts manifest rows by `run_order`, so summary output stays deterministic.
- The new research-boundary validator is intentionally strict. This is useful now because it forces every research payload to carry explicit non-live flags.
- There are now two market-journal implementations: the older helper inside `market_data.py` and the new dedicated `market_journal.py`. Tests pass, so this is not a blocker, but the next data-foundation pass should consolidate or clearly separate these APIs before more providers are added.

## Issues

`HMM_MULTI_KNN_AGENT_ISSUES.md` has no open issues after this pass.
