# Data/Feature Agent Journal Replay Contracts

## Agent name

Data/Feature Agent

## Task received

Implement the first research-only append-only market journal contract and deterministic replay reader for Binance-style market events.

Scope constraints:

- Keep scope small: JSONL writer/reader plus manifest.
- Preserve event order and provide deterministic replay order.
- Validate required fields, missing source event time, duplicate hashes, sequence gaps, and symbol/source mismatch.
- Use local fixtures only.
- Do not add DB indexing.
- Do not modify live execution, operator UI, Hyperliquid, sizing, or runtime control files.

## Files read

- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_PROMPTS.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_INPUT_LOOKUP.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_REALIZATION_PLAN.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_MODEL_SPEC.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_RUNBOOK.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_SOURCE_LOG.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md`
- `docs/tradingbotsuite_runtime/source_inputs/tradingbotsuite_critical_audit_orchestrator_next_agent.md`
- `docs/tradingbotsuite_runtime/source_inputs/orchestrator_btc_eth_perps_architecture_review_v3.md`
- `configs/v2_btc_hmm_multi_knn_research.json`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_data_agent_archive_ingestion_journal.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_backtest_agent_replay_determinism_contract.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_monitoring_agent_data_quality_reports.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_feature_agent_completed_bar_alignment.md`
- `src/tradingbotsuite/research/market_data.py`
- `src/tradingbotsuite/research/replay.py`
- `tests/tradingbotsuite/test_market_data_collection.py`
- `tests/tradingbotsuite/test_replay_determinism.py`

## Files changed

- `src/tradingbotsuite/research/market_journal.py`
- `tests/tradingbotsuite/test_market_journal.py`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_data_feature_agent_journal_replay_contracts.md`

## Commands/tests run

```powershell
git branch --show-current
git rev-parse --short HEAD
git status --short
Get-Content -Raw docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md
rg -n "journal|replay|Binance|market data|append-only|data quality|feature alignment" docs/tradingbotsuite_runtime/agent_artifacts docs/tradingbotsuite_runtime/HMM_MULTI_KNN_MODEL_SPEC.md docs/tradingbotsuite_runtime/HMM_MULTI_KNN_REALIZATION_PLAN.md
rg -n "MarketJournal|read_market_journal|journal|payload_hash|source_row_index|sequence" src/tradingbotsuite/research tests/tradingbotsuite -g "*.py"
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_market_journal.py -q
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite/research/market_journal.py
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_market_journal.py tests/tradingbotsuite/test_market_data_collection.py tests/tradingbotsuite/test_replay_determinism.py -q
git diff -- src/tradingbotsuite/adapters/execution.py src/tradingbotsuite/core/engine.py src/tradingbotsuite/config.py src/tradingbotsuite/runtime.py src/tradingbotsuite/web/operator.py src/tradingbotsuite/web/templates/control.html src/tradingbotsuite/operator_commands.py
git diff --check -- src/tradingbotsuite/research/market_journal.py tests/tradingbotsuite/test_market_journal.py
git status --short
```

Results:

- Branch: `codex/hmm-knn-research-package`
- Commit at start: `9f1ad7f`
- `tests/tradingbotsuite/test_market_journal.py`: `4 passed`
- Combined focused run: `15 passed`
- `compileall`: passed
- `git diff --check` on touched files: passed
- Explicit live-boundary diff: no output

Current worktree includes other agents' tracked edits outside this task:

```text
 M configs/v2_btc_hmm_multi_knn_research.json
 M docs/tradingbotsuite_runtime/HMM_MULTI_KNN_MODEL_SPEC.md
 M src/tradingbotsuite/main.py
 M src/tradingbotsuite/research/hmm_knn.py
 M src/tradingbotsuite/research/hmm_knn_experiments.py
 M src/tradingbotsuite/research/hmm_knn_monitoring.py
 M src/tradingbotsuite/research/live_readiness.py
 M tests/tradingbotsuite/test_hmm_knn.py
 M tests/tradingbotsuite/test_live_readiness.py
?? docs/tradingbotsuite_runtime/agent_artifacts/20260428_data_feature_agent_journal_replay_contracts.md
?? src/tradingbotsuite/research/market_journal.py
?? tests/tradingbotsuite/test_market_journal.py
```

Final status also showed additional concurrent artifacts after this file was created:

```text
?? docs/tradingbotsuite_runtime/agent_artifacts/20260428_backtest_agent_experiment_scaling_validation.md
?? docs/tradingbotsuite_runtime/agent_artifacts/20260428_knn_agent_gpu_lorentzian_backend.md
```

## Decisions made

- Added a dedicated `src/tradingbotsuite/research/market_journal.py` module instead of expanding live market-data or runtime paths.
- Kept the contract research-only and file-backed:
  - append-only JSONL writer
  - raw file-order reader
  - deterministic replay reader
  - manifest builder
  - validation helpers
- Required journal event fields:
  - `raw_payload`
  - `normalized_payload`
  - `source_event_time_ms`
  - `local_receive_time_ms` nullable
  - `source_name`
  - `symbol`
  - `data_family`
  - `schema_version`
  - `payload_hash`
  - `sequence` nullable
  - `source_row_index`
- Deterministic replay order is:
  - `source_event_time_ms`
  - `sequence` when present
  - `source_row_index`
  - `payload_hash`
- The writer assigns `source_row_index` automatically when omitted, preserving append/file order.
- Validation raises on missing required event fields, invalid payload hash, symbol/source/data-family mismatch between envelope and payloads, duplicate payload hashes, and sequence gaps.
- Manifests include `research_only: true`, `observe_only: true`, `promotion_ready: false`, journal hash, manifest hash, event counts by source/symbol/family, event-time and receive-time bounds, duplicate hash diagnostics, sequence gap diagnostics, and non-promotable notes.

## Assumptions

- This contract is for Binance-style market data events and remains signal-source data only. It is not Hyperliquid execution/fillability evidence.
- `sequence` is nullable because some historical or archive-style rows have only row indexes. Sequence gap validation runs only for streams with sequences present.
- Supported symbols are `BTCUSDT` and `ETHUSDT` to keep BTC Phase 1 and ETH Phase 2 schemas compatible without adding ETH research output in this task.
- `payload_hash` is computed from raw payload, normalized payload, source event time, source name, symbol, data family, schema version, and sequence, excluding `source_row_index` so duplicate payload content can be detected.
- Existing `src/tradingbotsuite/research/market_data.py` journal helpers remain in place for prior archive-ingestion behavior; this pass adds a tighter standalone contract instead of changing collector interfaces.

## Open issues or blockers

No open issues or blockers.

`docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md` reported no open issues when checked. No issue was appended.

## Unresolved risks

- The new module is not wired into dataset building yet. Feature generation still needs a later task to consume journal outputs rather than direct collector/export rows.
- The contract does not add DB indexes, stream collectors, network ingestion, or CLI commands by design.
- Gap detection is sequence-based only. Time-interval gap validation for klines or other periodic streams remains a family-specific downstream validation layer.
- Binance source families are normalized to a small initial set; future live stream families may require explicit additions and tests.

## Handoff notes for other agents

- Import path: `tradingbotsuite.research.market_journal`.
- Focused tests: `tests/tradingbotsuite/test_market_journal.py`.
- Use `read_market_journal_events()` when file append order matters.
- Use `read_market_journal_for_replay()` for deterministic replay.
- Do not wire this journal into live execution, runtime control, operator UI, Hyperliquid adapters, sizing, or safety gates without a separate live-boundary task.
