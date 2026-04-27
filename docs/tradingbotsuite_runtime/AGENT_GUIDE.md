# Agent Guide For Runtime Work

Use this guide before editing `src/tradingbotsuite`.

## Workstream Boundaries

- `tradingbot` owns TradingView/Pine parity and signal-generation research.
- `tradingbotsuite` owns runtime safety, market data, execution, operator UI, and preserved runtime research tools.
- TradingView chart-export importing and dataset/model training are currently inactive. Preserve the code, but do not expand it unless the operator explicitly reopens that workstream.
- ETH, cross-asset modeling, and tuning-heavy GUI work are not part of the current runtime baseline.

## Preferred Change Order

1. Read the relevant doc in this folder and the code path being edited.
2. Add or update tests before changing runtime safety, market data, or execution behavior.
3. Keep external assumptions source-backed in docs or code comments where the behavior is non-obvious.
4. Run targeted tests for the edited subsystem.
5. Run the full suite if the change touches shared config, persistence, engine, adapters, or UI routes.

## Market-Data Rules

- Binance closed 15m bars, aggTrade, and bookTicker are entry-critical.
- Local diff-depth queue metrics are useful, but queue-depth degradation alone should not block entries.
- UI/API snapshot reads must be passive. Polling the UI must not trigger REST depth snapshot storms.
- REST rate-limit handling should degrade queue features safely rather than crash engine snapshots.

## Execution Rules

- Hyperliquid live/testnet order placement must stay behind explicit runtime mode and live-enable config.
- All mutating operator endpoints require authentication/CSRF in UI-enabled mode.
- Testnet-only TP/SL cleanup behavior is for validation only and must be clearly marked as such.
- Reconciliation ambiguity should fail closed.

## Documentation Rules

- Keep operator-facing docs factual and current.
- Do not imply observe-only research output is approved live gating.
- Do not add generated metrics, local CSVs, SQLite DBs, or screenshots unless they are sanitized fixtures with a clear test purpose.
