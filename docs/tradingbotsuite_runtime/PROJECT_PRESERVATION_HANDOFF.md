# Project Preservation Handoff

Last updated: 2026-04-17

Repository migration note: this document preserves historical local-development context. Sections about TradingView chart-export importing, dataset building, model training, and filter optimization are archived reference material, not the active workstream, unless the operator explicitly reopens that scope.

This document is the durable project handoff for the current `tradingbotsuite` repository. It exists so the system can be recovered, reviewed, or continued without relying on any chat history.

The local blueprint remains the product and safety source of truth:

- `btc_eth_hybrid_framework_verified_blueprint.txt`

This document does not replace the blueprint. It records what has actually been built, what was hardened, where the important files live, and how to validate the repo before further development.

## Current State

The repo is a BTC-first modular async Python monolith for a TradingView -> Python -> Hyperliquid trading stack.

Current phase:

- V1 paper/testnet/live-capable BTC execution and safety core exists.
- V2 BTC research/data/acceptance infrastructure is in progress.
- ETH, multi-asset expansion, and a broader tuning workbench are V3 or later.

Primary runtime paths:

- TradingView-compatible webhook ingress.
- Manual shell signal injection.
- Local browser operator console.
- Shared engine path for `shadow`, `paper`, and `live`.
- Binance USD-M futures as the reference market-data venue.
- Hyperliquid as the execution venue.
- SQLite WAL as the local state/event/research store.

Important boundary:

- V2 model output and entry-gate research are observe-only unless explicitly promoted later.
- Live gating still falls back to V1 safety and hard vetoes.
- Hyperliquid testnet full-stack features are for adapter validation, not strategy proof.

## Source Of Truth Documents

Read these in this order when rebuilding context:

1. `btc_eth_hybrid_framework_verified_blueprint.txt`
2. `README.md`
3. `docs/PROJECT_PRESERVATION_HANDOFF.md`
4. `docs/BTC_RUNTIME_RELIABILITY_GUIDE.md`
5. `docs/MICROSTRUCTURE_RELIABILITY.md`
6. `docs/MICROSTRUCTURE_SQUARE_ROOT_IMPACT_FINDINGS.md`
7. `docs/OPERATOR_GUIDE.md`
8. `docs/TESTNET_FULL_STACK_CHECKLIST.md`
9. `docs/TRADINGVIEW_V2_DATA_FRAMEWORK.md`
10. `docs/DATASET_BUILDING_GUIDE.md`
11. `docs/ENTRY_GATE_RESEARCH.md`
12. `docs/GOLDILOCKS_FILTER_RESEARCH.md`
13. `docs/V2_RESEARCH_GUIDE.md`
14. `docs/V2_STABILITY_AUDIT.md`
14. V1 audit docs:
    - `docs/V1_SCORECARD.md`
    - `docs/V1_FINDINGS.md`
    - `docs/V1_REMEDIATION_PLAN.md`

The blueprint defines the phase boundaries:

- V1: BTC execution and safety core.
- V2: BTC TradingView-to-acceptance phase, including TradingView signal history, BTC dataset building, research, acceptance scoring, and BTC-only validation.
- V3: ETH layer, cleaner operator/tuning GUI, and broader tuning instruments.

`docs/TRADINGVIEW_V2_DATA_FRAMEWORK.md` is a V2 data-workstream sub-framework. It is not the phase-definition source of truth.

## Repository Map

Core runtime:

- `src/tradingbotsuite/core/models.py`
  - canonical contracts such as signals, packets, positions, execution intents/reports, barriers, and health structures
- `src/tradingbotsuite/core/engine.py`
  - canonical decision, execution, supervision, safe-mode, reconcile, and snapshot path
- `src/tradingbotsuite/core/math.py`
  - ATR, barrier construction, Hurst, and deterministic math helpers
- `src/tradingbotsuite/core/features.py`
  - feature packet construction and runtime/research feature glue
- `src/tradingbotsuite/core/acceptance.py`
  - baseline hard-veto acceptance logic
- `src/tradingbotsuite/core/microstructure_prediction.py`
  - observe-only microstructure probability visualization logic
- `src/tradingbotsuite/core/security.py`
  - webhook authentication helpers

Adapters:

- `src/tradingbotsuite/adapters/binance.py`
  - Binance REST and websocket market-data layer
  - closed 15m bars
  - aggTrade signed flow
  - bookTicker top-of-book
  - diff-depth local book
  - rate limiting and passive snapshots
- `src/tradingbotsuite/adapters/execution.py`
  - shadow, paper, and Hyperliquid execution adapters
  - live/testnet preflight, order placement, cancel, trigger protection, and reconciliation support

Persistence:

- `src/tradingbotsuite/persistence/sqlite_store.py`
  - SQLite WAL schema
  - signals, decisions, trade state/events, action tickets
  - operator jobs/logs/commands
  - import batches
  - execution metrics, health events, supervision snapshots

Operator surfaces:

- `src/tradingbotsuite/web/app.py`
  - FastAPI app factory
- `src/tradingbotsuite/web/operator.py`
  - operator UI/API routes
- `src/tradingbotsuite/web/templates/*.html`
  - server-rendered UI pages
- `src/tradingbotsuite/operator_console.py`
  - operator service layer for UI commands, jobs, artifacts, snapshots, and analysis
- `src/tradingbotsuite/operator_commands.py`
  - shared command helpers used by shell and browser
- `src/tradingbotsuite/manual_cli.py`
  - terminal fallback for manual long/short, status, supervise, reconcile, and tracing

Research:

- `src/tradingbotsuite/research/tradingview_import.py`
  - versioned TradingView chart-export importer
- `src/tradingbotsuite/research/dataset.py`
  - BTC research dataset builder and triple-barrier labels
- `src/tradingbotsuite/research/modeling.py`
  - logistic regression training and calibration
- `src/tradingbotsuite/research/evaluation.py`
  - replay evaluation and metrics
- `src/tradingbotsuite/research/inference.py`
  - observe-only artifact scoring path
- `src/tradingbotsuite/research/entry_gate.py`
  - chart-export entry-gate replay, ACF/HVR/DSP filters, optimizer, preflight, and visual-analysis data
- `src/tradingbotsuite/research/workflow.py`
  - CLI workflow wrappers
- `configs/v2_btc_research.json`
  - pinned V2 BTC research plan/config

Entrypoints:

- `src/tradingbotsuite/main.py`
  - CLI commands and FastAPI module app
- `run_server.py`
  - repo-local server launcher
- `run_manual.py`
  - repo-local manual shell launcher
- `run_live_smoke.py`
  - repo-local Hyperliquid live/testnet smoke helper

Tests:

- `tests/test_engine.py`
  - engine state machine, safety, execution, supervision, reconcile, testnet flows
- `tests/test_binance.py`
  - Binance stream/cache/local-book/microstructure behavior
- `tests/test_entry_gate.py`
  - ACF/HVR/DSP math, replay simulator, optimizer, preflight
- `tests/test_tradingview_import.py`
  - TradingView chart export import and dataset entry-price integration
- `tests/test_operator_ui.py`
  - UI routes, operator API, jobs, analysis tab
- `tests/test_research.py`
  - dataset, model, calibration, replay, shadow scoring

## Major Implementation And Hardening Steps

### 1. Phase Map Realignment

The blueprint was corrected so the phase split is explicit:

- V2 includes TradingView-facing BTC work.
- V3 is ETH + cleaner GUI/operator UX + broader tuning instruments.
- TradingView does not begin in V3; V3 broadens an already-established BTC TradingView path.

This matters because all current research/import/dataset work is valid V2 work.

### 2. V1 BTC Execution And Safety Core

Implemented and hardened:

- canonical `SignalIntent`, `DecisionPacket`, `PositionState`, `ExecutionIntent`, and `ExecutionReport` contracts
- TradingView-style webhook endpoint
- manual signal injection through the same engine path
- duplicate/replay lock
- same-direction signal ignore/rejection
- close-then-flip sequencing
- paper and shadow execution paths
- Hyperliquid live/testnet adapter
- startup/reconnect reconciliation
- fail-closed behavior on stale data or ambiguous state
- SQLite WAL persistence and append-mostly event history

Operational principle:

- shell, UI, webhook, paper, shadow, and live all use the same engine decision path.

### 3. Mathematical Core

Locked and tested:

- ATR uses standard Wilder true range on closed 15m candles.
- Barriers are frozen at entry.
- Long barriers:
  - `tp = entry + k_tp * ATR`
  - `sl = entry - k_sl * ATR`
- Short barriers are mirrored.
- Vertical barrier is stored as bars and wall-clock deadline.
- Python enforces the time barrier even when exchange TP/SL protections exist.
- Exchange-facing price/size/notional math uses `Decimal`.
- Indicator/reference calculations may use float where appropriate, with conversion boundaries.

Test coverage includes:

- ATR fixture/reference tests
- barrier symmetry
- vertical barrier handling
- MFE/MAE and exit attribution paths
- replay simulator edge cases

### 4. Hyperliquid Layer

Implemented and hardened:

- SDK-backed Hyperliquid adapter
- testnet and live endpoint configuration
- fallback loading from local `hyperliquidtestnet.txt` when explicit `TBS_HL_*` env vars are missing
- agent/master account resolution
- exchange preflight
- client-order-id based placement and cancellation
- reduce-only trigger protections
- price normalization against Hyperliquid perp rules
- user-state and order/fill stream handling
- reconciliation with exchange snapshots
- ambiguity handling and safe-mode transitions
- timeout behavior that waits the configured window instead of using an artificial sub-second cap

Important testnet-only harness:

- The operator console can place short-lived TP/SL trigger orders after a confirmed manual entry fill and auto-cancel them after `10s`.
- This exists only to validate Hyperliquid order/protection/cancel plumbing.
- For Hyperliquid testnet drift, fixed temporary trigger prices are used:
  - long validation: TP `75000`, SL `70000`
  - short validation: TP `70000`, SL `75000`
- This must be removed or redesigned before any real deployment.

### 5. Binance Market-Data Robustness

The Binance layer was treated as a reliability subsystem, not just a feature provider.

Implemented/hardened:

- routed websocket split:
  - `/market` for `kline_15m` and `aggTrade`
  - `/public` for `bookTicker` and diff-depth
- combined stream sessions to reduce connection churn
- passive read paths:
  - UI polling and snapshots do not trigger depth bootstrap
- dedicated depth worker:
  - one book owner per symbol
  - one in-flight repair/resync per symbol
  - explicit depth states: `cold`, `buffering`, `bootstrapping`, `synced`, `resync_pending`, `backoff`, `stale`
- local-book reconstruction:
  - buffer diffs
  - fetch `/fapi/v1/depth`
  - drop events older than `lastUpdateId`
  - align first replay event by official `U/u` overlap or futures `pu == lastUpdateId` fallback observed live
  - require `pu == previous u` after sync
  - schedule bounded resync on sequence break
- shared REST budget layer:
  - depth snapshots, klines, funding, premium, open interest, and context calls share the same budget
  - `429` and `418` degrade appropriately instead of causing repeated storms
- planned websocket reconnect before 24h expiry
- invalid-book checks:
  - non-empty sides
  - best bid below best ask
  - enough levels for configured L1/L5/L10 queue metrics
- queue fields fail soft:
  - queue imbalance/depletion unavailable when depth is not trustworthy
- signed taker flow and bookTicker remain usable if fresh
- `aggTrade` uses `nq` when available to stay aligned with public book liquidity
- square-root signed-notional diagnostics are now emitted beside raw signed flow, following the square-root impact research note
- flow/price alignment and impact-efficiency diagnostics are observe-only and should not be treated as live gates

Important policy:

- Queue-depth degradation alone is not a full entry-critical market-data failure when closed bars, signed flow, and bookTicker are healthy.
- Stale/missing `aggTrade`, stale/missing `bookTicker`, stale bars, wide spread, or basis dislocation can still block entries.

Relevant doc:

- `docs/MICROSTRUCTURE_RELIABILITY.md`

### 6. Runtime Safety And Attribution

Added/normalized:

- safety state summaries and reason codes
- safe-mode/degraded/blocked handling
- stale feed thresholds for bars, trades, bookTicker, depth, and basis
- spread/depth abnormality controls
- max daily loss guard
- max open-risk guard
- reconcile staleness timeout
- basis dislocation checks between Binance reference and Hyperliquid
- execution attribution:
  - signal receipt time
  - decision time
  - order submission
  - ack/fill/protection times
  - close submission/fill
  - slippage versus reference mids where available
- supervision attribution:
  - exit reason
  - first barrier touched
  - MFE/MAE
  - holding time in bars and milliseconds
  - basis at entry/during/exit

Persistence surfaces:

- `execution_metrics`
- `health_events`
- `supervision_snapshots`

### 7. Operator Console

Built as a thin browser layer over the same engine, not a separate trading system.

Architecture:

- FastAPI + Jinja templates + lightweight polling
- mounted under `/ui`
- localhost-only by default
- disabled unless `TBS_OPERATOR_UI_ENABLED=true`
- requires `TBS_OPERATOR_UI_SECRET`
- signed session cookie
- CSRF protection for mutating routes
- same-origin checks
- no config editing in this version

Pages:

- `Overview`
  - runtime state, health, position, market data, microstructure, supervision, attribution
- `Control`
  - manual long/short, supervise, reconcile, refresh health, smoke/testnet actions, mode switching
- `Timeline`
  - typed event feed instead of raw terminal spam
- `Research`
  - dataset/train/calibrate/replay job controls and artifact summaries
- `Analysis`
  - chart-export upload/selection, candlestick chart, crosshair, entry-gate replay, optimizer controls
- `Predictions`
  - observe-only microstructure probability visualization
- `Guides`
  - embedded repo docs and rule-based operator recommendations

Important principle:

- Strategy logic must stay in backend engine/research code.
- UI must remain presentation + command dispatch.

### 8. TradingView Chart Export Pipeline

Implemented:

- versioned chart-export import CLI:
  - `python -m tradingbotsuite.main import-tv-chart-export --path "BINANCE_BTCUSDT.P, 15 (2).csv" --symbol BTCUSDT --strategy-version kernel_v1`
- source mode:
  - `chart_export`
- source:
  - `tradingview_chart_export`
- `strategy_version` required
- batch id:
  - `tv-chart:<symbol>:<strategy_version>:<file_hash_prefix>`
- signal id:
  - `<batch_id>:<tv_bar_time_ms>:<direction>`
- import lineage table:
  - `signal_import_batches`
- candidate signals stored in existing `signals` table
- `replace-batch` mode for deterministic re-import of the same batch

Parsing rules:

- Use `time`, `open`, `high`, `low`, `close`, `Buy`, `Sell`.
- Ignore `StopBuy`, `StopSell`, `Shapes`, and `Chars`.
- Non-empty `Buy` means long candidate.
- Non-empty `Sell` means short candidate.
- Rows with both Buy and Sell are skipped.
- Last-row signals without next bar are skipped.

Entry normalization:

- Historical entry is next 15m bar open plus slippage.
- Long:
  - `next_open * (1 + entry_slippage_bps / 10000)`
- Short:
  - `next_open * (1 - entry_slippage_bps / 10000)`
- Marker price is lineage/audit metadata only.

### 9. Current Combined TradingView Data Artifact

The active project CSV is:

- `BINANCE_BTCUSDT.P, 15 (2).csv`

It is now a combined artifact, not a raw single TradingView export.

Merge manifest:

- `data/imports/tradingview_exports/BINANCE_BTCUSDT.P_15_combined_manifest.json`

Archived sources:

- `data/imports/tradingview_exports/BINANCE_BTCUSDT.P_15_original_before_20260414_merge.csv`
- `data/imports/tradingview_exports/BINANCE_BTCUSDT.P_15_new_export_20260414.csv`

Combined stats at merge time:

- rows: `13,925`
- first bar: `2025-11-20T14:00:00+00:00`
- last bar: `2026-04-14T15:00:00+00:00`
- Binance warmup rows: `1,000`
- original TradingView rows kept: `11,687`
- newer TradingView rows kept: `1,238`
- overlap rows: `983`
- overlap signal conflicts: `143`
- combined buys: `565`
- combined sells: `608`
- ambiguous buy+sell rows: `0`
- continuity gaps: `0`

Merge policy:

- Newer TradingView export is authoritative where it overlaps the original export.
- Older TradingView export is retained before the newer export begins.
- Binance historical bars were downloaded before the original export window as OHLC-only warmup.
- Binance warmup rows have blank TradingView signal/indicator columns.
- Warmup rows must never be treated as invented TradingView entries.

Important research warning:

- Because overlap had `143` signal differences, the combined artifact may mix slightly different TradingView indicator versions if the model was edited/optimized between exports.
- For clean future research, use a new `strategy_version` for every materially changed TradingView model/export.

### 10. Current Active Research DB State

Default DB:

- `data/tradingbotsuite.sqlite3`

Before replacing the active research signals, a backup was made:

- `data/backups/tradingbotsuite-before-tv-merge-1776180274915.sqlite3`

The old BTC chart-export and manual test research signals were removed from the active DB before importing the combined artifact.

Current active BTC research import:

- batch id: `tv-chart:BTCUSDT:kernel_v1:5adb66ab2313`
- source: `tradingview_chart_export`
- source mode: `chart_export`
- strategy version: `kernel_v1`
- source sha256: `5adb66ab23135001dcb7725d45515e85899d08a6b8531fc00da47fc559503ce1`
- imported count: `1173`
- buys: `565`
- sells: `608`
- skipped: `0`
- duplicates: `0`

Import manifest:

- `data/imports/tv-chart_BTCUSDT_kernel_v1_5adb66ab2313.json`

Current dataset build after the merge:

- path: `data/research/v2-btc-research-1/btcusdt_dataset.parquet`
- manifest: `data/research/v2-btc-research-1/dataset_manifest.json`
- rows: `1173`
- source counts:
  - `tradingview_chart_export`: `1173`
- source mode counts:
  - `chart_export`: `1173`
- strategy version counts:
  - `kernel_v1`: `1173`
- label balance at last build:
  - label accept 0: `791`
  - label accept 1: `382`
  - positive rate: `0.3256606990622336`

Known missingness at last dataset build:

- core closed-bar features were present.
- live-only microstructure fields are missing for historical chart-export rows unless captured live or reconstructed separately.
- premium/basis fields can be missing depending on historical endpoint availability.
- open interest missingness was high in the last build because historical OI context was only available for part of the window.

### 11. V2 Acceptance Baseline

Implemented:

- replayable dataset builder
- triple-barrier labels using shared barrier semantics
- logistic regression baseline
- isotonic calibration with Platt fallback
- replay evaluation
- manifest/versioned artifacts
- shadow-only scoring path through `TBS_RESEARCH_ARTIFACT_MANIFEST_PATH`

Current operational stance:

- No artifact loaded means scoring is skipped with explicit reason.
- Artifact/schema mismatch means scoring is skipped safely.
- Scoring is observe-only.
- Live gating is not approved.

### 12. Entry-Gate Research

Current active chart-export entry-gate research stack:

- ACF lag-1 autocorrelation
- HVR historical volatility ratio
- DSP cycle detector using causal SciPy Butterworth SOS bandpass

What it is trying to solve:

- reduce entries during tight corridor/chop regimes
- avoid cutting strong high-volatility trend entries
- remain closed-bar only
- avoid one-tick microstructure veto behavior

Important implementation details:

- ACF/HVR/DSP are causal and closed-bar only.
- DSP uses `scipy.signal.butter(..., output="sos")` and `scipy.signal.sosfilt`.
- It does not use `filtfilt` because that would look ahead.
- Gate rejection is based on regime/cycle state, not microstructure ticks.
- The optimizer uses stepped ranges.
- Default optimizer cap is `10,000` candidates.
- `--workers 15` is expected to be practical on the current workstation.
- Full all-component grid can be much larger; use `--uncapped` only intentionally.

Simulator rules:

- fixed position size: `0.01 BTC`
- default capital: `1000 USDT`
- entry: next bar open plus slippage
- reverse signal closes and reopens on next bar open
- fixed profile:
  - fixed TP/SL
- runner profile:
  - initial stop
  - activation after favorable movement
  - trailing stop with profit floor

Optimizer output now includes:

- `top5_results.csv`
  - constraint-ranked candidates
- `top5_by_return_results.csv`
- `top5_by_profit_factor_results.csv`
- `top5_by_winrate_results.csv`

This matters because manually tweaked settings may improve raw return or winrate while failing the strict retention/split-stability constraints.

Output directories include:

- strategy version
- exit profile
- selected components
- candidate cap

This prevents `runner` and `fixed` optimizer runs from overwriting each other.

### 13. Microstructure Predictions

The `Predictions` UI tab is observe-only.

It visualizes heuristic short-horizon microstructure pressure using:

- signed taker flow
- bookTicker top-of-book pressure
- synced queue imbalance if available
- depth-depletion bias if available
- feature coverage/confidence

It is not:

- calibrated
- a live entry gate
- a model promotion signal

Use it to understand what the microstructure layer is seeing, not to prove profitability.

## Environment And Configuration

Install:

```powershell
python -m pip install -e .
```

If not installed:

```powershell
$env:PYTHONPATH="src"
```

Paper mode:

```powershell
$env:TBS_RUNTIME_MODE="paper"
python run_manual.py
```

Operator UI:

```powershell
$env:TBS_OPERATOR_UI_ENABLED="true"
$env:TBS_OPERATOR_UI_SECRET="change-this-local-secret"
python run_server.py
```

Open:

```text
http://127.0.0.1:8000/ui
```

Hyperliquid testnet live-mode example:

```powershell
$env:TBS_RUNTIME_MODE="live"
$env:TBS_HL_ENABLE_LIVE="true"
$env:TBS_HL_BASE_URL="https://api.hyperliquid-testnet.xyz"
$env:TBS_HL_PRIVATE_KEY="0x..."
$env:TBS_HL_ACCOUNT_ADDRESS="0x..."
python run_server.py
```

Fallback testnet credentials:

- if explicit `TBS_HL_*` env vars are absent, the app checks for `hyperliquidtestnet.txt` in the repo root
- this fallback is for local testnet convenience
- do not commit real mainnet secrets

Important environment variables:

- `TBS_RUNTIME_MODE`
  - `shadow`, `paper`, or `live`
- `TBS_DB_PATH`
  - defaults to `data/tradingbotsuite.sqlite3`
- `TBS_OPERATOR_UI_ENABLED`
- `TBS_OPERATOR_UI_SECRET`
- `TBS_WEBHOOK_SECRET`
- `TBS_RESEARCH_ARTIFACT_MANIFEST_PATH`
- `TBS_HL_ENABLE_LIVE`
- `TBS_HL_BASE_URL`
- `TBS_HL_PRIVATE_KEY`
- `TBS_HL_ACCOUNT_ADDRESS`
- `TBS_HL_MAX_BASIS_BPS`
- Binance controls:
  - `TBS_BINANCE_DEPTH_UPDATE_SPEED_MS`
  - `TBS_BINANCE_DEPTH_SNAPSHOT_LIMIT`
  - `TBS_BINANCE_DEPTH_MAX_BUFFER_EVENTS`
  - `TBS_BINANCE_REST_WEIGHT_BUDGET_PCT`
  - `TBS_BINANCE_WS_PLANNED_RECONNECT_MS`

## Operational Commands

Run API server:

```powershell
python -m tradingbotsuite.main serve
```

Run manual shell:

```powershell
python -m tradingbotsuite.main manual
```

Run Hyperliquid live/testnet smoke:

```powershell
python -m tradingbotsuite.main smoke-live
```

Import TradingView chart export:

```powershell
python -m tradingbotsuite.main import-tv-chart-export --path "BINANCE_BTCUSDT.P, 15 (2).csv" --symbol BTCUSDT --strategy-version kernel_v1
```

Build dataset:

```powershell
python -m tradingbotsuite.main build-dataset
```

Train/calibrate/replay:

```powershell
python -m tradingbotsuite.main train-model --dataset data/research/v2-btc-research-1/btcusdt_dataset.parquet
python -m tradingbotsuite.main calibrate-model --train-manifest data/research/v2-btc-research-1-btcusdt-artifacts/train_manifest.json
python -m tradingbotsuite.main replay-eval --artifact-manifest data/research/v2-btc-research-1-btcusdt-artifacts/artifact_manifest.json
```

Entry-gate research:

```powershell
python -m tradingbotsuite.main research-entry-gates --path "BINANCE_BTCUSDT.P, 15 (2).csv" --symbol BTCUSDT --strategy-version kernel_v1
```

Entry-gate preflight:

```powershell
python -m tradingbotsuite.main preflight-entry-gates --path "BINANCE_BTCUSDT.P, 15 (2).csv" --symbol BTCUSDT --strategy-version kernel_v1_preflight
```

Heavy optimizer:

```powershell
python -m tradingbotsuite.main optimize-entry-gates --path "BINANCE_BTCUSDT.P, 15 (2).csv" --symbol BTCUSDT --strategy-version kernel_v1_heavy --exit-profile runner --workers 15
```

Deeper but still capped optimizer:

```powershell
python -m tradingbotsuite.main optimize-entry-gates --path "BINANCE_BTCUSDT.P, 15 (2).csv" --symbol BTCUSDT --strategy-version kernel_v1_deeper --max-gate-candidates 50000 --exit-profile runner --workers 15
```

## Verification Commands

Full test suite:

```powershell
python -m pytest -q
```

Focused tests:

```powershell
python -m pytest tests\test_binance.py -q
python -m pytest tests\test_engine.py -q
python -m pytest tests\test_operator_ui.py -q
python -m pytest tests\test_tradingview_import.py -q
python -m pytest tests\test_entry_gate.py -q
python -m pytest tests\test_research.py -q
```

Syntax/compile check:

```powershell
python -m compileall src
```

Dataset smoke:

```powershell
python -m tradingbotsuite.main build-dataset
```

Expected current dataset row count:

- `1173`

Current last known full verification before this document:

- `python -m pytest -q`
- result: `146 passed`

After editing code, rerun the full suite before treating the repo as stable.

## Recovery Procedures

### Recover From A Bad DB State

Default DB:

- `data/tradingbotsuite.sqlite3`

Backups:

- `data/backups/*.sqlite3`

Restore example:

```powershell
Copy-Item -LiteralPath "data\backups\<backup-file>.sqlite3" -Destination "data\tradingbotsuite.sqlite3" -Force
```

Then verify:

```powershell
python -m pytest tests\test_research.py tests\test_tradingview_import.py -q
python -m tradingbotsuite.main build-dataset
```

### Rebuild Current TradingView Import

Use this if the DB was lost but the combined CSV still exists:

```powershell
python -m tradingbotsuite.main import-tv-chart-export --path "BINANCE_BTCUSDT.P, 15 (2).csv" --symbol BTCUSDT --strategy-version kernel_v1 --notes "rebuild from combined artifact"
python -m tradingbotsuite.main build-dataset
```

Expected import:

- candidates: `1173`
- buys: `565`
- sells: `608`

Expected dataset:

- rows: `1173`

### Rebuild Combined CSV From Source Archives

Source archives:

- `data/imports/tradingview_exports/BINANCE_BTCUSDT.P_15_original_before_20260414_merge.csv`
- `data/imports/tradingview_exports/BINANCE_BTCUSDT.P_15_new_export_20260414.csv`

Current merge policy:

- new export replaces original on same `time`
- original kept before new export begins
- Binance OHLC-only warmup before original first bar
- warmup rows have blank signal columns

If rebuilding manually, validate:

- sorted by `time`
- no duplicate times
- every adjacent delta is `900` seconds
- no row has both `Buy` and `Sell`
- expected current counts:
  - bars: `13925`
  - buys: `565`
  - sells: `608`

### Recover From Binance Depth Degradation

Depth degradation alone is not necessarily fatal.

Check:

- `entry_ready`
- trade stream freshness
- bookTicker freshness
- closed-bar freshness
- depth sync state
- backoff ETA
- rate-limit count

Operator action:

- wait for repair if only queue depth is degraded
- do not force entries if bars/trades/bookTicker are stale
- if degradation persists with rate-limit climb, restart the app and inspect Binance connectivity

### Recover From Hyperliquid Safe Mode

Common causes:

- `heartbeat_loss`
- `reconciliation_stale`
- `reconciliation_mismatch`
- `basis_dislocation`
- `order_timeout`

Operator action:

- run Reconcile from Control page
- verify user stream health
- inspect current exchange position
- do not force new entries until local and exchange state agree

## Known Temporary Or Observe-Only Features

Do not confuse these with approved production strategy logic:

- V2 model scoring:
  - observe-only
  - no live gating
- ACF/HVR/DSP entry gates:
  - research-only
  - chart-export replay only unless promoted later
- Microstructure Predictions tab:
  - visualization only
  - not calibrated
- Hyperliquid testnet fixed TP/SL validation harness:
  - testnet-only
  - uses fixed trigger prices due to testnet/real-market drift
  - remove before real deployment
- Alpha-decay:
  - hooks exist but disabled because training/promotion evidence is not complete
- Adverse-selection:
  - runtime plumbing exists behind safe flags
  - not promoted to live by default
- True multi-level OFI:
  - transport groundwork exists
  - full OFI feature is deferred
- HMM:
  - not implemented as active gate
  - optional later overlay only after simpler filters prove value

## Design Principles To Preserve

1. Keep the engine path canonical.
   - UI, shell, webhook, paper, shadow, and live should call the same decision/execution logic.

2. Keep reads passive.
   - UI polling must not trigger Binance depth snapshots or repair storms.

3. Fail closed on ambiguity.
   - stale data, unresolved reconcile, ambiguous order state, or basis dislocation should block new entries.

4. Do not turn research into live behavior accidentally.
   - model scores, entry gates, and prediction panels remain observe-only until explicit promotion criteria pass.

5. Preserve lineage.
   - every chart export, model version, artifact, and dataset should have manifests/hashes.

6. Avoid one-tick gates for multi-hour trades.
   - microstructure is useful, but hard entry filters should be stable relative to the holding horizon.

7. Use TradingView as candidate signal source, not canonical label source.
   - labels come from this framework's frozen-ATR triple-barrier logic.

8. Keep BTC stable before ETH.
   - ETH and cross-asset features are V3 work.

## Next Development Priorities

Recommended order:

1. Validate current combined TradingView dataset with repeated entry-gate and model research runs.
2. Inspect whether the merged export is internally consistent enough for strategy conclusions, given the 143 overlap signal conflicts.
3. If TradingView model changes again, create a new `strategy_version` and rebuild from scratch instead of mixing versions silently.
4. Continue entry-gate research with retention and split-stability constraints.
5. Only after stable out-of-sample evidence, consider wiring an observe-only gate into live decision packets.
6. Improve historical market-context coverage if missingness materially harms research:
   - historical OI
   - historical basis/premium
   - optional reconstructed microstructure if feasible
7. Keep Hyperliquid testnet validation separate from strategy profitability research.
8. Defer ETH until BTC V2 is stable.

## What Not To Do

- Do not enable live model gating just because a single replay looks better.
- Do not optimize exits and filters together without strict out-of-sample controls.
- Do not treat Hyperliquid testnet fills as market-realistic price behavior.
- Do not use manual test signals as training truth.
- Do not scrape TradingView unofficially as the default architecture.
- Do not make the UI a second strategy implementation.
- Do not remove safe-mode blocks to make testing easier.
- Do not run uncapped optimizers as default UI behavior.
- Do not mix new TradingView model exports into the same `strategy_version`.

## Current Health Checklist Before Continuing

Run:

```powershell
python -m pytest -q
python -m tradingbotsuite.main build-dataset
```

Then inspect:

- `data/research/v2-btc-research-1/dataset_manifest.json`
- row count is `1173`
- source mode is `chart_export`
- strategy version is `kernel_v1`
- label classes both exist
- core closed-bar missingness is zero or understood
- live-only microstructure missingness is not treated as fatal for historical chart-export rows

If starting the UI:

```powershell
$env:TBS_OPERATOR_UI_ENABLED="true"
$env:TBS_OPERATOR_UI_SECRET="change-this-local-secret"
python run_server.py
```

Then inspect:

- Overview health
- Market Data and Microstructure cards
- Research artifact list
- Analysis page default CSV path
- Guides page

## Final Preservation Notes

The repo has been made robust primarily by separating concerns:

- TradingView provides candidate entries.
- Binance provides market context.
- Hyperliquid executes.
- Python owns safety, state, labels, and supervision.
- SQLite preserves state and research lineage.
- The UI observes and dispatches commands without becoming strategy logic.

If future work preserves those boundaries, the project remains understandable and recoverable.
