# Agent name

Data Agent

# Task received

Objective: find whether a usable local BTC Phase 1 dataset already exists.

Commands requested:

```powershell
Get-ChildItem -Recurse -File data,configs,tests -ErrorAction SilentlyContinue | Select-Object FullName,Length,LastWriteTime
rg -n "BTCUSDT|btcusdt|dataset_path|parquet|research" data configs tests docs/tradingbotsuite_runtime -S
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_research.py -q
```

Tasks:

- Identify all local BTC dataset candidates.
- Classify each as usable, maybe usable, or not usable for HMM/KNN Phase 1.
- Check whether candidate data includes label fields, missingness fields, raw context fields, and enough rows.
- Do not fetch live data.
- Note that repo instruments for Binance BTC data extraction exist, while OF-style Binance Vision / Crypto Lake extraction instruments are not present in this repo.
- Write this artifact.

# Files read

- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_PROMPTS.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md`
- `configs/v2_btc_hmm_multi_knn_research.json`
- `configs/v2_btc_research.json`
- `data/research/v2-btc-research-1/dataset_manifest.json`
- `data/research/v2-btc-research-1/btcusdt_dataset.parquet`
- `data/research/v2-btc-research-1-btcusdt-artifacts/artifact_manifest.json`
- `data/research/v2-btc-research-1-btcusdt-artifacts/train_manifest.json`
- `data/imports/tradingview_exports/BINANCE_BTCUSDT.P_15_combined_manifest.json`
- `data/imports/tradingview_exports/BINANCE_BTCUSDT.P_15_combined.csv`
- `data/imports/tradingview_exports/BINANCE_BTCUSDT.P_15_new_export_20260414.csv`
- `data/imports/tradingview_exports/BINANCE_BTCUSDT.P_15_original_before_20260414_merge.csv`
- `data/research/chart_ohlcv_cache/BTCUSDT_15m_1760450400000_1776178800000.manifest.json`
- `data/research/chart_ohlcv_cache/BTCUSDT_15m_1760450400000_1776178800000.json`
- `data/tradingbotsuite.sqlite3`
- `data/backups/tradingbotsuite-before-tv-merge-1776180274915.sqlite3`
- `data/backups/tradingbotsuite-before-manual-signal-purge-1775953749717.sqlite3`
- `tests/fixtures/btc_15m_fixture.json`
- `tests/tradingbotsuite/fixtures/btc_15m_fixture.json`
- `src/tradingbotsuite/research/dataset.py`
- `src/tradingbotsuite/research/hmm_knn.py`
- `src/tradingbotsuite/persistence/sqlite_store.py`
- `src/tradingbotsuite/research/workflow.py`

# Files changed

- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_data_agent_real_btc_dataset_inventory.md`

# Commands/tests run

```powershell
Get-Content docs\tradingbotsuite_runtime\HMM_MULTI_KNN_AGENT_PROMPTS.md
Get-Content docs\tradingbotsuite_runtime\HMM_MULTI_KNN_AGENT_ISSUES.md
Get-ChildItem -Recurse -File data,configs,tests -ErrorAction SilentlyContinue | Select-Object FullName,Length,LastWriteTime
rg -n "BTCUSDT|btcusdt|dataset_path|parquet|research" data configs tests docs/tradingbotsuite_runtime -S
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_research.py -q
Get-ChildItem -Path data,tests -Recurse -File -Include *.parquet,*.csv,*.json,*.sqlite3,*.sqlite -ErrorAction SilentlyContinue | Select-Object FullName,Length,LastWriteTime | Format-List
Get-Content data\research\v2-btc-research-1\dataset_manifest.json
Get-Content data\research\v2-btc-research-1-btcusdt-artifacts\artifact_manifest.json
Get-Content data\research\v2-btc-research-1-btcusdt-artifacts\train_manifest.json
Get-Content data\imports\tradingview_exports\BINANCE_BTCUSDT.P_15_combined_manifest.json
python - <<local parquet/csv/json/sqlite inventory script>>
$env:PYTHONPATH='src'; python - <<HMM/KNN _prepare_dataset compatibility script>>
rg -n "def build\(|list_research_signals|decision_packet|raw_payload|fetch_historical_closed_bar_range|fetch_funding_context|fetch_open_interest_context|fetch_premium_context" src\tradingbotsuite\research\dataset.py src\tradingbotsuite\persistence\sqlite_store.py src\tradingbotsuite\research\workflow.py
python - <<sqlite signal/source count script>>
Get-Content data\research\chart_ohlcv_cache\BTCUSDT_15m_1760450400000_1776178800000.manifest.json
Get-Content tests\fixtures\btc_15m_fixture.json -TotalCount 5
```

Validation result:

```text
tests/tradingbotsuite/test_research.py: 13 passed in 3.16s
```

# Decisions made

- Treated this as a read-only local inventory. No live Binance data, Binance Vision data, Crypto Lake data, or external source was fetched.
- Classified candidates by whether they can be passed directly to HMM/KNN Phase 1, can serve as local source material for rebuilding a dataset, or are not usable as HMM/KNN input data.
- Used the current HMM/KNN config to check static KNN feature columns and HMM emission feature columns.
- Used `_prepare_dataset()` only as a local compatibility check for the existing Parquet; this reads local Parquet and fills HMM/KNN-derived/backfilled fields, and does not fetch data.

# Inventory summary

## Usable

### `data/research/v2-btc-research-1/btcusdt_dataset.parquet`

Classification: usable for local HMM/KNN Phase 1 artifact generation.

Observed:

- Rows: `1173`
- Columns: `105`
- Symbols: `BTCUSDT` only
- Required static KNN feature columns from `configs/v2_btc_hmm_multi_knn_research.json`: all present before WT3D generation
- Required HMM emission feature columns: all present
- Labels present in raw Parquet:
  - `label_accept`
  - `label_pnl_multiple`
  - `label_exit_reason`
- Missingness fields present:
  - `30` `missing_*` columns
  - examples include `missing_funding_rate`, `missing_open_interest`, `missing_premium_close`, `missing_premium_basis_rate`, `missing_primary_signed_imbalance_ratio`, `missing_spread_bps`
- Raw context fields present:
  - only `raw_signal_payload_json`
  - no current raw exchange-context audit fields such as `raw_funding_rate`, `raw_open_interest`, `raw_premium_close`, `raw_mark_price`, or `raw_index_price`
- HMM/KNN local prepare check:
  - `_prepare_dataset()` produced `1173` rows and `125` columns
  - no missing configured KNN/HMM columns after prepare
  - `realized_net_return_after_costs` was created
  - public label outcome fields were created/backfilled: `gross_return`, `fees_bps`, `slippage_bps`, `funding_paid_or_received`, `time_in_trade`, `max_adverse_excursion`, `max_favorable_excursion`, `barrier_hit_type`
  - walk-forward split count: `3`, with split shapes `(703, 156)`, `(867, 156)`, `(1031, 134)`

Caveat: the dataset is usable for HMM/KNN artifact generation, but it is stale relative to the newest Data Agent raw-context contract. Its manifest lacks current hardening keys such as `research_only`, `asset_scope`, `label_outcome_fields`, `raw_context_available_counts`, and `exchange_context_summary`, and the Parquet lacks current raw exchange audit fields. Treat it as schema-compatible legacy BTC data, not as a fully current Data Agent dataset artifact.

## Maybe usable

### `data/research/v2-btc-research-1/dataset_manifest.json`

Classification: maybe usable as the pointer/metadata for the usable Parquet, but stale as a current contract manifest.

Observed:

- `row_count`: `1173`
- `symbol`: `BTCUSDT`
- `dataset_path`: `data\research\v2-btc-research-1\btcusdt_dataset.parquet`
- Has `missing_feature_rates` and `planned_split_summary`
- Missing current public manifest fields:
  - `research_only`
  - `asset_scope`
  - `label_outcome_fields`
  - `raw_context_available_counts`
  - `exchange_context_summary`

### `data/tradingbotsuite.sqlite3`

Classification: maybe usable as local source material for rebuilding a BTC research dataset, not directly usable as HMM/KNN input.

Observed:

- `signals`: `1174`
- TradingView chart-export signals: `1173`
- Manual signal: `1`
- `decision_packets`: `1`
- `signal_import_batches`: `1`
- BTC-only symbol counts for signal-related tables

Caveat: `ResearchDatasetBuilder.build()` reads `list_research_signals()` and then needs historical bars plus funding/OI/premium context from its candle client. Rebuilding from this DB without live fetches would require using local source/cache paths or a local-only candle/context client. The DB alone is not enough HMM/KNN input.

### `data/backups/tradingbotsuite-before-tv-merge-1776180274915.sqlite3`

Classification: maybe usable as older local source material, not directly usable as HMM/KNN input.

Observed:

- `signals`: `1196`
- TradingView chart-export signals: `1194`
- Manual signals: `2`
- `decision_packets`: `2`
- BTC-only signal counts

Caveat: backup predates the merged current DB and would need deliberate selection before any rebuild.

### `data/backups/tradingbotsuite-before-manual-signal-purge-1775953749717.sqlite3`

Classification: maybe usable as older local source material, not directly usable as HMM/KNN input.

Observed:

- `signals`: `1355`
- TradingView chart-export signals: `1194`
- Manual signals: `160`
- `decision_packets`: `160`
- BTC-only signal counts except one system trade event

Caveat: contains manual/audit history mixed with TradingView imports; it is not the clean current Phase 1 research source without filtering.

### `data/imports/tradingview_exports/BINANCE_BTCUSDT.P_15_combined.csv`

Classification: maybe usable as local TradingView OHLC/signal source, not directly usable as HMM/KNN input.

Observed:

- Rows: `13925`
- Columns: `29`
- Manifest symbol: `BTCUSDT`
- Timeframe: `15m`
- Manifest continuity gap count: `0`
- Buy markers: `565`
- Sell markers: `608`
- Has TradingView marker columns and OHLC-style columns
- Does not have HMM/KNN labels, missingness fields, or raw exchange context fields

Caveat: useful as source for import/build workflows, but it needs dataset building and labeling before HMM/KNN.

### `data/imports/tradingview_exports/BINANCE_BTCUSDT.P_15_original_before_20260414_merge.csv`

Classification: maybe usable as older TradingView source, not directly usable as HMM/KNN input.

Observed:

- Rows: `12670`
- Columns: `29`
- No HMM/KNN labels, missingness fields, or raw exchange context fields

### `data/imports/tradingview_exports/BINANCE_BTCUSDT.P_15_new_export_20260414.csv`

Classification: maybe usable as newer TradingView source segment, not directly usable as HMM/KNN input.

Observed:

- Rows: `1238`
- Columns: `29`
- No HMM/KNN labels, missingness fields, or raw exchange context fields

### `data/research/chart_ohlcv_cache/BTCUSDT_15m_1760450400000_1776178800000.json`

Classification: maybe usable as local OHLCV source, not directly usable as HMM/KNN input.

Observed:

- Rows: `17477`
- Manifest symbol: `BTCUSDT`
- Interval: `15m`
- Source: `binance_usdm_klines`
- Sample keys: `time_ms`, `open`, `high`, `low`, `close`, `volume`

Caveat: contains OHLCV only. It has no TradingView signal rows, labels, missingness fields, raw funding/OI/premium context, or HMM/KNN feature columns by itself.

## Not usable

### `data/research/v2-btc-research-1-btcusdt-artifacts/*`

Classification: not usable as HMM/KNN Phase 1 input dataset.

Observed:

- These are baseline acceptance model artifacts, not dataset rows.
- `artifact_manifest.json` and `train_manifest.json` point back to `data\research\v2-btc-research-1\btcusdt_dataset.parquet`.
- Manifest total rows: `1194`, while the actual current Parquet has `1173` rows.
- Feature version: `v2-btc-acceptance-1`, while the dataset manifest is `v2-btc-acceptance-2`.
- `rejected_vs_accepted.csv` has only `60` rows and only `label_accept` / `label_exit_reason` among label fields.
- No raw context or missingness fields in these CSV outputs.

### Entry-gate research outputs under `data/research/v2-btc-entry-*`

Classification: not usable as HMM/KNN Phase 1 input dataset.

Observed examples:

- `data/research/v2-btc-entry-gates-kernel_v1/rejected_vs_accepted.csv`: `1194` rows, `11` columns
- `grid_results.csv` files: optimizer result grids, not signal feature rows
- `equity_curve.csv` files: PnL/equity summaries

Caveat: these are entry-gate simulation/optimizer outputs. They do not contain the HMM/KNN feature contract, label outcome fields, missingness fields, or raw exchange context fields required for Phase 1 dataset input.

### Small test fixtures

Paths:

- `tests/fixtures/btc_15m_fixture.json`
- `tests/tradingbotsuite/fixtures/btc_15m_fixture.json`

Classification: not usable as real HMM/KNN Phase 1 input.

Observed:

- `20` OHLCV rows each
- Keys: `time_ms`, `open`, `high`, `low`, `close`, `volume`
- No labels, no HMM/KNN feature columns, no missingness fields, no raw exchange context

Use only for unit tests.

### Smoke SQLite DBs

Paths include:

- `data/audit_shadow.sqlite3`
- `data/hyperliquid_smoke.sqlite3`
- `data/live_engine_smoke.sqlite3`
- `data/testnet_*.sqlite3`
- `data/v1_gap_close_smoke.sqlite3`

Classification: not usable as HMM/KNN Phase 1 input.

Observed:

- Signal counts are generally `0` to `2`
- Built for smoke/manual/live-adjacent checks
- Not enough rows and not dataset-shaped

# Binance extraction note

The repo contains instruments for Binance BTC data extraction through the existing Binance candle/client and dataset-building paths. I did not use them in this task because the explicit instruction was not to fetch live data.

For OF-style historical data from Binance Vision or Crypto Lake, I did not find repo-local extraction instruments. Those would require new ingestion code or external preprocessing before they can feed this dataset layer.

# Assumptions

- "Usable for HMM/KNN Phase 1" means a local artifact can be passed to the current HMM/KNN preparation/research path without live fetching and has enough rows, labels, and configured feature columns.
- "Current Data Agent contract" is stricter than "HMM/KNN can consume it"; the existing Parquet is consumable but lacks current raw-context audit columns and manifest summaries.
- Local temp synthetic datasets referenced in prior agent artifacts are not persistent repo-local BTC datasets and were not counted as current local candidates.

# Open issues or blockers

None.

`docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md` reported no open issues before this task. No new issue was appended.

# Handoff notes for other agents

- Prefer `data/research/v2-btc-research-1/btcusdt_dataset.parquet` when a local, no-fetch BTC dataset is needed for HMM/KNN artifact generation.
- Do not treat that Parquet as a fully current Data Agent raw-context artifact. It should be regenerated before audits that require `raw_context_available_counts`, `exchange_context_summary`, or raw funding/OI/premium fields.
- TradingView CSVs, SQLite stores, and the OHLCV cache are useful local rebuild ingredients, but not direct HMM/KNN input datasets.
- Any rebuild that uses repo Binance extraction tools must be treated as a separate task because this inventory intentionally performed no live fetch.
