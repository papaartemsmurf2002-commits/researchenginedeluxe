# TradingBotSuite Runtime Preservation Map

This folder preserves the BTC runtime and reliability work that was developed locally before this repository became the shared workspace.

## Active Scope

- BTC-only runtime safety and execution supervision.
- Binance USD-M market-data reliability, including closed bars, aggTrade flow, bookTicker, and local diff-depth book health.
- Hyperliquid execution/testnet validation.
- Localhost operator console for visibility and guarded manual commands.
- Runtime attribution, health snapshots, and operator-facing documentation.

## Preserved But Not Active

The `src/tradingbotsuite/research/` package includes chart-export import, dataset, optimizer, and filter-research code. It is preserved so prior work is not lost, but TradingView data importing, dataset-building, model training, and live model promotion are out of the active workstream until explicitly reapproved.

## Critical Runtime Entry Points

- `src/tradingbotsuite/core/engine.py`: canonical decision, supervision, reconciliation, and snapshot path.
- `src/tradingbotsuite/adapters/binance.py`: Binance market-data and local-book subsystem.
- `src/tradingbotsuite/adapters/execution.py`: Hyperliquid execution adapter and testnet support.
- `src/tradingbotsuite/operator_console.py`: service layer shared by UI/API command routes.
- `src/tradingbotsuite/web/operator.py`: localhost operator API/UI router.
- `src/tradingbotsuite/main.py`: CLI surface for runtime and preserved research commands.

## Safety Rules

- Never commit real credentials. `hyperliquidtestnet.txt`, `.env`, SQLite DBs, and `data/` are gitignored.
- Do not let UI routes bypass engine safety. Shell, API, UI, paper, and live paths should see the same accept/reject reason.
- Queue-depth degradation is warning/diagnostic unless signed trade flow or top-of-book health is also unsafe.
- Hyperliquid testnet is execution-validation infrastructure; Binance remains the current market-data authority.
- Any TradingView/export/training changes must be isolated as research until a separate approval pass.

## Verification Commands

```powershell
$env:PYTHONPATH="src"
python -m pytest tests\tradingbotsuite -q
python -m compileall -q src\tradingbotsuite
```

Run the full workspace suite before pushing broad changes:

```powershell
$env:PYTHONPATH="src"
python -m pytest -q
```
