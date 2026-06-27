# V2 Final Code Audit - Technical Agent Handoff

Date: 2026-06-27  
Repository: `papaartemsmurf2002-commits/researchenginedeluxe`  
Audience: implementation / research agents  
Scope: static code and design audit of the current v2 research stack, focused on practical result correctness, speed, validation strength, data-source usefulness, and agent handoff safety.  
Boundary: research-only. This document does not create candidate-pack, paper/live, order-placement, sizing, runtime-mode, promotion, or production-trading readiness.

## 1. Executive summary

No production/live trading blocker was found in the inspected v2 code. The research-only boundary is consistently represented in schemas and artifacts, and the architecture is generally safe for local research iteration. The important remaining work is not about broad theoretical readiness. It is about making the local engine faster, making accepted-research gates harder to fool, and avoiding ambiguous real-world math.

The most practical next changes are:

1. Add real account notional to cost/capacity math.
2. Enforce the actual project acceptance rules: at least 10 trades/month and no more than 2 losing months/year.
3. Require real walk-forward folds for accepted validation; do not allow a single `full_window` fold to prove stability.
4. Add a true array/vectorized backtest engine while keeping the current Python engine as the reference engine.
5. Stop rerunning the full simulation for cost-stress scenarios.
6. Replace Parquet `to_pylist()` filtering with Arrow/Polars predicate pushdown.
7. Move ledger and manifest appends to part-based storage instead of rewrite-on-append.
8. Expand venues only through small probe lanes first; do not let venue work distract from engine/validation fixes.

## 2. Hardware-aware conclusion

The user machine is strong enough for local research if the code uses it correctly:

- CPU: Ryzen 7 7700, 16 threads, overclocked to about 5.3 GHz.
- GPU: RTX 5070 Ti.
- RAM: 64 GiB DDR5 6400.
- Main SSD: Samsung 9100 Pro 1 TB.
- OF/archive SSD: PCIe 4.0 SSD around 7 GB/s read/write.

This means the bottleneck is not the hardware. The bottleneck is mainly Python object loops, repeated full simulations, and converting columnar data into Python dict rows. Optimize CPU/Arrow/NumPy/Polars first. GPU work is optional and should come later, after the data is already in arrays.

Suggested worker sizing on this machine:

- Strategy/backtest parameter sweeps: start with 8 to 12 process workers.
- OF archive parsing/materialization: start with 4 to 8 workers, then increase only if RAM and SSD are not saturated.
- Avoid 16 heavy Python workers unless the work is mostly I/O-bound and memory is stable.

## 3. Modules inspected

Important code paths reviewed in this pass:

- `src/tradingbotsuite/v2/backtest_engine/engine.py`
- `src/tradingbotsuite/v2/backtest_engine/artifacts.py`
- `src/tradingbotsuite/v2/backtest_engine/jobs.py`
- `src/tradingbotsuite/v2/backtest_data/service.py`
- `src/tradingbotsuite/v2/costs/models.py`
- `src/tradingbotsuite/v2/strategy_specs/compiler.py`
- `src/tradingbotsuite/v2/strategy_specs/schemas.py`
- `src/tradingbotsuite/v2/validation/jobs.py`
- `src/tradingbotsuite/v2/validation/walk_forward.py`
- `src/tradingbotsuite/v2/ledger/service.py`
- `src/tradingbotsuite/v2/ledger/schemas.py`
- `src/tradingbotsuite/v2/workers/job_store.py`
- `src/tradingbotsuite/v2/workers/runner.py`
- `src/tradingbotsuite/v2/data_sources/central_market_history.py`
- `src/tradingbotsuite/v2/data_sources/central_market_history_collection.py`
- `src/tradingbotsuite/v2/data_sources/of_style_materialization.py`
- `src/tradingbotsuite/v2/data_sources/binance_vision.py`
- `src/tradingbotsuite/v2/data_sources/bybit_okx.py`
- `src/tradingbotsuite/v2/universe/hyperliquid.py`
- `src/tradingbotsuite/v2/venues/hyperliquid/info.py`
- Current control docs and issue/audit docs that affect agent behavior.

Generated market data/evidence under `data/research/**` and the external OF archive were not inspected because they are intentionally gitignored and locally large. That is expected and is not itself a finding.

## 4. Positive findings

### 4.1 Research boundary is strong

The v2 code has consistent boundary fields such as `research_only`, `observe_only`, `promotion_ready`, `candidate_evidence`, `candidate_pack_eligible`, `live_signal`, `paper_signal`, `sizing_instruction`, `order_placement_instruction`, and `runtime_mode_change`. Important schemas call the central boundary validator, and v2 import-boundary tests exist.

No issue was found that suggests v2 is secretly placing orders, mutating live runtime, or emitting promotion/candidate artifacts.

### 4.2 Data provenance discipline is good

The archive, central market-history, backtest-data, validation, ledger, and autonomous-readiness layers are heavily manifest/hash oriented. This is the right design for research reproducibility.

The docs and code correctly avoid pretending Binance/Bybit rows are native Hyperliquid rows. This must stay true.

### 4.3 Missing/unavailable data is usually handled honestly

The code and docs generally prefer explicit blocker evidence over proxy substitution. This is important for strategies requiring event/L2/funding/OI data.

### 4.4 Venue design is conservative

The repo already has lanes for:

- Hyperliquid public info, recent candles, funding, L2 snapshots.
- Binance Vision / Data Vision bulk archives.
- Bybit public archive/API surfaces.
- OKX public API probes.

These should remain research/probe/data lanes, not trading lanes.

## 5. High-priority findings

### F-001: Capacity math needs account notional

Severity: high result-quality risk  
Files: `src/tradingbotsuite/v2/costs/models.py`, `src/tradingbotsuite/v2/backtest_engine/artifacts.py`, `src/tradingbotsuite/v2/backtest_engine/engine.py`

Current behavior:

- `turnover` is weight delta.
- `participation_rate = turnover / volume`.
- Cost components are computed as `turnover * bps / 10_000`.

This is fine for normalized return accounting, but weak for real-world liquidity/capacity. If equity is normalized to `1.0`, then a 5% rebalance divided by a large dollar-volume bar produces a near-zero participation rate, even when a real account size would matter.

Recommended fix:

```text
BacktestRunConfig.account_notional_usd: float
CostModelConfig.account_notional_usd: float | None
trade_notional_usd = abs(weight_delta) * account_notional_usd
bar_volume_notional_usd = volume_notional
participation_rate = trade_notional_usd / bar_volume_notional_usd
cost_return = trade_notional_usd * bps / account_notional_usd / 10_000
```

Acceptance tests:

- A 5% rebalance on a $1,000,000 account against a $10,000,000 bar should report 0.5% participation.
- The same weights on a $100,000,000 account should hit the participation cap if cap is 5%.
- Existing normalized-return tests should still pass when account notional is 1 or a default reference notional.

### F-002: Accepted validation is missing actual project gates

Severity: high validation risk  
Files: `src/tradingbotsuite/v2/validation/jobs.py`, `src/tradingbotsuite/v2/ledger/service.py`, `src/tradingbotsuite/v2/ledger/schemas.py`

Current validation checks include run status, earliest date, usable months, coverage, as-of universe, lockbox overlap, fold positivity, cost-stress scenarios, and cost-dependent failure.

Missing practical project gates:

- At least 10 trades/month.
- No more than 2 losing months/year.

Current ledger code sets `minimum_trade_frequency_pass` as `metrics.trade_count > 0`, which is far weaker than the stated project rule.

Recommended fix:

```text
trades_per_month = trade_count / usable_months
block if trades_per_month < 10

monthly_returns = aggregate daily/equity returns by calendar month
losing_month_count_12m = count(month_net_return < 0) over each 12-month window
block if any 12-month window has losing_month_count > 2
```

New ledger fields:

- `trades_per_month`
- `min_required_trades_per_month`
- `losing_month_count`
- `max_losing_months_allowed`
- `positive_month_share`
- `monthly_stability_pass`

### F-003: `full_window` fold can overstate stability

Severity: high validation interpretation risk  
Files: `src/tradingbotsuite/v2/backtest_engine/engine.py`, `src/tradingbotsuite/v2/validation/jobs.py`, `src/tradingbotsuite/v2/validation/walk_forward.py`

The engine writes a single `fold_metrics` row with `fold_id = full_window`. Validation then computes fold stability from available fold rows. A single positive full-window fold can become `fold_stability_score = 1.0`, which is not real walk-forward robustness.

The repo already has walk-forward split helpers with purge/embargo support. Those should be used for accepted research.

Recommended fix:

```text
accepted_research validation requires fold_count >= 4 or >= 6
full_window-only runs may remain diagnostic but cannot pass accepted stability
validation manifest records fold_generation_mode = walk_forward | full_window_only
```

### F-004: Execution timing semantics are too easy to misread

Severity: medium/high result interpretation risk  
Files: `src/tradingbotsuite/v2/backtest_engine/engine.py`, strategy spec execution schema

The engine applies the previous target weight to the current bar return, then computes current target and turnover. That can be a legitimate no-lookahead approach, but the name `next_bar_open` is not enough to make the timing clear. Costs are also recorded at the same timestamp as the target change, so readers can interpret it as close execution, next-open execution, or mixed timing.

Recommended fix:

Add explicit manifest fields:

```text
signal_observation = close_t
execution = next_bar_open
pnl_interval = next_bar_open_to_next_bar_close
cost_application_ts = execution_ts
```

Add a 3-bar fixture test where the expected signal, turnover, cost, and PnL timing are unambiguous.

### F-005: Spread units are ambiguous

Severity: medium/high cost math risk  
Files: `src/tradingbotsuite/v2/backtest_engine/engine.py`, OF materialization outputs

`_observed_spread_bps()` treats `spread <= 1.0` as a fraction and multiplies by 10,000; otherwise it treats the value as bps. This can be wrong if `spread` is an absolute price difference from book ticker data.

Recommended fix:

Use separate fields:

```text
spread_abs
spread_bps
spread_fraction
```

Reject ambiguous `spread` in accepted research unless a `spread_unit` field is present.

### F-006: Backtest data loading wastes columnar I/O

Severity: high performance risk  
Files: `src/tradingbotsuite/v2/backtest_data/service.py`

Current path reads Parquet columns into memory, calls `to_pylist()`, then filters timestamps in Python. This defeats predicate pushdown and wastes the fast SSD/RAM setup.

Recommended fix:

Use `pyarrow.dataset` or Polars lazy scans:

```text
columns = requested_fields
filter = ts >= load_start and ts < end_ts and instrument_id in instrument_ids
return Arrow Table / Polars DataFrame / NumPy arrays to fast engine
```

Keep dict-row output only for the reference engine and small artifacts.

### F-007: Backtest engine is not truly vectorized

Severity: high performance risk  
Files: `src/tradingbotsuite/v2/backtest_engine/engine.py`, `src/tradingbotsuite/v2/strategy_specs/compiler.py`

The core simulation is Python object/dict loop based. The signal compiler repeatedly scans history via `_prior_rows()`, which filters full instrument history for each row.

Recommended architecture:

```text
Current engine: reference_engine_python
New engine: fast_vectorized_engine

panel arrays: time x instrument x field
signals: time x instrument
weights: time x instrument
returns: time x instrument
turnover: abs(weight_t - weight_t-1)
costs: vectorized from turnover, spread, volume, funding
```

Add fixture parity tests between the reference engine and fast engine.

### F-008: Cost stress reruns full simulation

Severity: medium/high performance risk  
Files: `src/tradingbotsuite/v2/backtest_engine/engine.py`

The cost-stress matrix reruns `_simulate_vectorized()` for stress scenarios. Signals, weights, returns, and turnover should not require recomputation.

Recommended fix:

After base simulation, keep turnover/position/return arrays and recompute stressed costs directly.

Expected gain: approximately 2x to 3x for runs requiring base, stress_2x, and stress_3x.

### F-009: Ledger and manifest appends rewrite full Parquet files

Severity: medium scaling risk  
Files: `src/tradingbotsuite/v2/ledger/service.py`, `src/tradingbotsuite/v2/backtest_data/service.py`

Ledger append reads existing rows, adds one row, and rewrites the Parquet file. Backtest-data request append uses the same pattern. This becomes O(n^2) as agent-generated trials grow.

Recommended storage layout:

```text
ledger/
  parts/ledger_part_000001.parquet
  parts/ledger_part_000002.parquet
  append_log.jsonl
  compacted/current.parquet
```

Build leaderboard from a dataset scan or compact periodically.

### F-010: Central market-history and OF materialization are still memory-heavy

Severity: medium/high scaling risk  
Files: `src/tradingbotsuite/v2/data_sources/central_market_history.py`, `src/tradingbotsuite/v2/data_sources/central_market_history_collection.py`, `src/tradingbotsuite/v2/data_sources/of_style_materialization.py`

Fast writers exist, but still often materialize whole batches into Python tuples/lists, dedupe in memory, and write `pa.Table.from_pylist`. OF materialization loops source files sequentially and writes JSONL feature rows.

Recommended fix:

- Partition by provider / family / symbol / timeframe / month.
- Use chunked `ParquetWriter` / `RecordBatch` writes.
- Dedupe inside partition only.
- Materialize OF features with process workers.
- Write OF feature outputs as Parquet for downstream strategy loading; keep JSONL only for small debug output.

### F-011: Worker claim/stale handling should be hardened for multi-worker use

Severity: medium concurrency risk  
Files: `src/tradingbotsuite/v2/workers/job_store.py`, `src/tradingbotsuite/v2/workers/runner.py`

SQLite WAL is a good choice. However, `claim_next()` performs a select and then writes the claimed record. With multiple worker processes, this should be guarded by an atomic conditional update or `BEGIN IMMEDIATE` transaction.

Also, stale detection only handles `RUNNING` jobs. A worker that dies after `CLAIMED` and before `RUNNING` can leave a job stuck.

Recommended fix:

```sql
BEGIN IMMEDIATE;
SELECT job_id FROM worker_jobs
WHERE kind=? AND status='queued'
ORDER BY queued_at, job_id
LIMIT 1;
UPDATE worker_jobs
SET status='claimed', ...
WHERE job_id=? AND status='queued';
COMMIT;
```

Also mark stale `CLAIMED` jobs using `claimed_at`.

### F-012: Universe accepted-evidence flag depends on passed aggregate coverage inputs

Severity: medium misuse risk  
Files: `src/tradingbotsuite/v2/universe/hyperliquid.py`

Universe eligibility is built from parameters such as `coverage_ratio` and `usable_months`. If callers pass blanket values, a whole snapshot can be marked as evidence-allowed without per-instrument coverage joining inside the function.

Recommended fix:

For accepted evidence, require a per-instrument coverage manifest join before `accepted_research_evidence_allowed=true`.

Also, `select_asof_universe()` chooses `max(snapshot_id)` for the latest date. Snapshot IDs are hashes, so lexicographic max is not semantically meaningful. Prefer created_at/run timestamp or explicit latest marker.

## 6. Concrete small bugs / cleanup items

### B-001: Funding `0.0` fallback bug

File: `src/tradingbotsuite/v2/strategy_specs/compiler.py`

Current pattern:

```python
return _numeric(row.value("funding")) or _numeric(row.value("funding_rate"))
```

If `funding == 0.0`, Python treats it as false and falls back to `funding_rate`.

Fix:

```python
funding = _numeric(row.value("funding"))
return funding if funding is not None else _numeric(row.value("funding_rate"))
```

### B-002: Binance aggTrades row parser length check

File: `src/tradingbotsuite/v2/data_sources/central_market_history_collection.py`

The older `rows_from_binance_agg_trades_zip()` checks `len(values) < 6` but later reads `values[6]`. The payload parser correctly checks `< 7`. Align the older row parser to `< 7` or route all paths through the payload parser.

### B-003: Verify Bybit index provider label

File: `src/tradingbotsuite/v2/data_sources/central_market_history_collection.py`

`build_bybit_index_plan()` returns provider `bybit_inverse`. Confirm whether this is intended for the indexed/futures symbol universe. If it is only a source-family label, document it. If not, use `bybit_linear` or a neutral provider key.

### B-004: Usable months should be exact

File: `src/tradingbotsuite/v2/backtest_engine/engine.py`

`_usable_months()` counts calendar month delta only. Accepted validation should define whether it needs full months or duration days. If it needs full months, enforce full completed calendar months.

## 7. Venue/data-source audit

### 7.1 Hyperliquid

Use Hyperliquid public API for current metadata, recent candle diagnostics, funding, and L2 snapshots. Do not rely on public `candleSnapshot` for old 2024 intraday candles; official docs state only the most recent 5000 candles are available. Time-range endpoints return 500 elements or blocks and need pagination.

Recommended status:

- Metadata: useful.
- Funding history: useful with pagination.
- Candle snapshot: recent-window only.
- L2 book: snapshot/recent only.
- Native historical official data: do not chase if outside strict-free/operator-approved scope.

### 7.2 Binance

Binance remains the strongest free bulk source. The repo already has Binance Vision/Data Vision source-plan builders for monthly klines, daily aggTrades, trades, bookDepth, and bookTicker.

REST klines are useful for spot checks, but bulk research should prefer archives. Binance REST kline limit is small relative to archive scale. Binance open-interest-history REST is limited to recent history, so use it as a current/context probe unless an archive source is available.

### 7.3 Bybit

Bybit is a good secondary venue. The repo already has Bybit public archive and API scaffolding. Bybit klines support date windows and limit up to 1000. Bybit open interest supports interval, start/end, limit up to 200, and cursor pagination.

Recommended next work:

- Implement or prove full Bybit OI/funding pagination before treating it as coverage-ready.
- Keep recent trades/orderbook endpoints labeled as recent/snapshot only.

### 7.4 OKX

OKX probe scaffolding exists. Keep it as a probe lane until historical pagination and endpoint-specific caveats are proven in focused tests. Do not over-invest until Bybit/Binance paths are fully useful.

### 7.5 Bitget

Bitget is worth adding as a low-cost probe/secondary comparison lane. Official docs show history candle API with 90-day max range and max 200 rows per response.

Suggested initial endpoints:

- `bitget_mix_history_candles`
- `bitget_mix_mark_price_history_candles`
- `bitget_mix_index_price_history_candles`
- later: funding/OI probes if cleanly available.

### 7.6 MEXC / Gate

MEXC and Gate are possible later probe lanes. Do not make them primary until the backtest engine and validation gates are hardened. Start with candle/funding/OI availability probes only.

## 8. Recommended work packets

### WPR-AUD-FIX-001: Accepted-validation hardening

Paths:

- `src/tradingbotsuite/v2/validation/jobs.py`
- `src/tradingbotsuite/v2/ledger/service.py`
- `src/tradingbotsuite/v2/ledger/schemas.py`
- focused tests under `tests/v2/`

Implement:

- `trades_per_month >= 10`
- `losing_months_per_12m <= 2`
- `fold_count >= required_min_folds`
- block `full_window_only` for accepted research

### WPR-AUD-FIX-002: Cost/capacity realism

Paths:

- `src/tradingbotsuite/v2/costs/models.py`
- `src/tradingbotsuite/v2/backtest_engine/artifacts.py`
- `src/tradingbotsuite/v2/backtest_engine/engine.py`
- focused tests under `tests/v2/`

Implement:

- `account_notional_usd`
- notional-aware capacity checks
- explicit spread units
- funding sign convention metadata

### WPR-AUD-FIX-003: Fast backtest path

Paths:

- `src/tradingbotsuite/v2/backtest_engine/**`
- `src/tradingbotsuite/v2/strategy_specs/**`
- tests comparing reference vs fast engine

Implement:

- array/NumPy/Arrow-based engine
- rolling-window signal compiler
- stress-cost reuse, no full rerun
- benchmark fixture with timing output

### WPR-AUD-FIX-004: Backtest-data I/O fast path

Paths:

- `src/tradingbotsuite/v2/backtest_data/service.py`
- relevant backtest-data tests

Implement:

- Arrow dataset / Polars filtering
- projection pushdown
- avoid `to_pylist()` before filtering
- return columnar panel to fast engine

### WPR-AUD-FIX-005: Archive writer scaling

Paths:

- `src/tradingbotsuite/v2/data_sources/central_market_history.py`
- `src/tradingbotsuite/v2/data_sources/central_market_history_collection.py`
- `src/tradingbotsuite/v2/data_sources/of_style_materialization.py`

Implement:

- chunked ParquetWriter
- partition-aware dedupe
- process-pool OF materialization
- Parquet feature output

### WPR-AUD-FIX-006: Worker concurrency hardening

Paths:

- `src/tradingbotsuite/v2/workers/job_store.py`
- `tests/v2/test_workers_phase7.py` or new focused worker tests

Implement:

- atomic claim-next transaction
- stale claimed-job handling
- multi-worker claim race regression

### WPR-AUD-FIX-007: Venue probe expansion

Paths:

- `src/tradingbotsuite/v2/data_sources/**`
- source registry config samples
- tests/v2 focused probe tests

Priority:

1. Bitget history candles.
2. Bybit OI/funding pagination proof.
3. OKX pagination confirmation.
4. MEXC/Gate availability probes.

## 9. Non-findings

Do not spend time on these unless new evidence appears:

- The 700 GB evidence/archive store being gitignored is normal and correct.
- Earlier docs saying “not ready” are normal historical stage progression, not contradictions.
- Missing native Hyperliquid official/requester-pays history is not a blocker for the strict-free/free-venue lane, as long as provenance is kept honest.
- Lack of an OI/funding/L2 profitable strategy is not a repo-readiness blocker. It is a research target.
- Do not rewrite old audit history just because newer packets superseded it.

## 10. Final priority order

1. Validation hardening: trades/month, losing months, real fold count.
2. Cost/capacity realism: account notional and explicit units.
3. Fast backtest engine and no-rerun cost stress.
4. Arrow/Polars backtest-data loading.
5. Part-based ledger/manifests.
6. Chunked archive/OF materialization.
7. Worker claim/stale hardening.
8. Venue probes.

This order improves research quality and speed fastest while preserving the existing research-only boundary.
