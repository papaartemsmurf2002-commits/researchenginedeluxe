# Orchestrator Review: Market Journal Consolidation

Date: 2026-04-29

## Task

Continue development after the GPU/journal/scaling pass by resolving the main follow-up risk: two market-journal implementations existed after the previous pass.

## Change

`src/tradingbotsuite/research/market_data.py` now keeps its existing public compatibility imports:

- `MarketJournalWriter`
- `read_market_journal`
- `MarketJournalValidationError`
- `MARKET_JOURNAL_SCHEMA_VERSION`
- `MARKET_JOURNAL_WRITER_VERSION`

Those names now route to the canonical Binance-style market journal contract in `src/tradingbotsuite/research/market_journal.py`.

The old `market_data.py` journal implementation was replaced with a thin adapter:

- legacy `receive_time_ms` input is mapped to canonical `local_receive_time_ms`
- replay reads use `read_market_journal_for_replay`
- manifests now share the canonical `journal_type`, schema version, writer version, hash, replay order, duplicate/gap diagnostics, and research-boundary metadata

## Why

Future Binance Vision, Crypto Lake, and Hyperliquid archive work needs one replay contract. Keeping two JSONL journal schemas would make feature joins, label replay, and deterministic backtests fragile.

## Validation

Focused compatibility and canonical tests:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_market_data_collection.py::test_market_journal_replay_is_deterministic_and_validates_manifest_hash tests/tradingbotsuite/test_market_journal.py -q
```

Result before final full validation: `5 passed`.

## Boundary

No live execution, sizing, Hyperliquid adapter, runtime control, Control page, or operator live-control behavior is touched by this consolidation.

## Issues

No unresolved issue was added to `HMM_MULTI_KNN_AGENT_ISSUES.md`.
