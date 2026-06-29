# V2 Final Code Audit Critical Review And Change Plan

Date: 2026-06-29
Packet: WPR106-559
Source document: `C:\Users\papaa\Downloads\V2 Final Code Audit (1).docx`
Manual review issue: https://github.com/papaartemsmurf2002-commits/researchenginedeluxe/issues/4

## Executive Verdict

The uploaded audit is directionally strong. Its core warnings about validation
strength, capacity math, fold semantics, and performance are supported by the
current repository.

No live-trading, order-placement, sizing, runtime-mode, paper/live, candidate
pack, or promotion blocker was found in the inspected v2 code. The research
boundary remains consistently represented in source schemas, artifact rows, and
manager context output.

The main problem is narrower and more practical: the repo can currently report
research-readiness and accepted-research validation without enough real
walk-forward evidence, without account-notional-aware capacity math, and with
slower-than-needed Python/list/Parquet paths. These are result-quality and
scale risks, not live-execution risks.

## What Was Inspected

- Uploaded DOCX structure: 336 nonempty paragraphs, 0 tables, 0 comments, 0
  tracked changes.
- Control docs: product scope, decision register, no-touch paths, audit index,
  known issues, repo/dependency fuse, stage ledger, research quickstart.
- Core code: boundary policy, autonomous readiness, agent context, archive and
  source materialization, backtest data service, strategy compiler, backtest
  engine, cost model, validation gate, ledger, Lead Book, workers, universe,
  and CLI surfaces.
- Evidence artifacts: WPR106-546 29-symbol 1m bar validation, WPR106-552
  OF-style materialization report, WPR106-556 autonomous-readiness cycle and
  validation artifacts.
- Binance plugin: USD-M BTCUSDT 1m kline connector sanity check succeeded on
  retry and returned current 12-field kline rows. Repo-owned manifests remain
  the authoritative evidence source.

## Confirmed Findings

### 1. Accepted Validation Can Pass With One Full-Window Fold

The current engine writes a single `fold_id=full_window` row. The validation
gate counts that as one positive fold and can pass with `fold_stability_score =
1.0`.

Observed WPR106-556 evidence:

- `validation_status=pass`
- `evidence_mode=accepted_research`
- `fold_count=1`
- `positive_fold_count=1`
- `fold_id=full_window`

Change: accepted research should require a real walk-forward fold count and a
fold generation mode. Full-window-only evidence may remain diagnostic, but it
should not satisfy accepted stability.

Manual decision: issue #4 asks whether the minimum should be 4 or 6 folds.

### 2. Capacity Math Is Dimensionally Weak

The cost model computes participation as normalized weight turnover divided by
USD bar volume. That preserves normalized return accounting, but it is not
real account capacity.

Validated example from WPR106-556:

- First BTC trade turnover: `0.025`
- Matching bar volume notional: `92,487,298.3102`
- Reported participation: `2.7030738768204313e-10`
- At default account notional USD 10,000, true notional participation would be
  `0.0000027031`
- At account notional USD 100,000,000, true notional participation would be
  `0.0270307388`

Change: add explicit `account_notional_usd` to accepted runs and compute
capacity from trade notional divided by bar notional. Keep normalized cost
returns, but do not use normalized weights as the capacity numerator.

Decision: accepted research should default `account_notional_usd` to USD 10,000
unless a run explicitly overrides it.

### 3. The Project Gate In The Uploaded Audit Is Stricter Than Current Code

Current Lead Book gates fail fewer than five average trades/month and six
losing months/year. The uploaded audit proposes at least ten trades/month and
at most two losing months/year.

WPR106-556 diagnostics:

- Trade count: `314`
- Trade months: Jan `10`, Feb `2`, Mar `50`, Apr `24`, May `76`, Jun `76`, Jul
  `76`
- Average over calendar months present: `44.8571` trades/month
- Monthly net returns: Jan `+0.000056`, Feb `+0.018079`, Mar `+0.015956`, Apr
  `-0.011019`, May `+0.004437`, Jun `-0.006582`, Jul `+0.007630`
- Losing months: `2 of 7`

The run passes an average-trades interpretation and the proposed losing-month
limit, but fails a strict every-calendar-month minimum because February has
only two trades.

Change: once the policy is decided, align validation, ledger, Lead Book, and
tests to the same gate.

Manual decision: issue #4 asks whether "10 trades/month" means average,
every calendar month, or every active month.

### 4. Cost Stress Reruns The Whole Simulation

`_cost_stress_rows()` reruns `_simulate_vectorized()` for stress scenarios even
though signals, target weights, turnover, and price returns are unchanged.

The math is internally consistent: WPR106-556 base transaction cost equals
`7.85 * 12.32 bps / 10000 = 0.0096712`, and 2x/3x stress scales as expected.
The inefficiency is that the repo recomputes the full loop to get those rows.

Change: preserve base arrays/rows for returns, weights, turnover, and funding,
then recompute stressed costs directly.

### 5. Backtest Data And Ledger Paths Waste Columnar I/O

`BacktestDataService._read_panel_rows()` reads Parquet columns, calls
`to_pylist()`, and filters timestamps in Python. Ledger appends read the full
ledger, append one row, and rewrite the Parquet file.

Change: add Arrow Dataset or Polars predicate/projection pushdown for panel
loading. Move ledger/backtest-data request appends toward part-based storage
with periodic compaction.

### 6. Strategy Compiler Still Has A Funding Fallback Edge In Rank Mode

The single-instrument funding carry path already uses an explicit `None` check,
so the uploaded document's simple funding bug is stale for that path.

However, `_metric_score()` still uses:

```python
return _numeric(row.value("funding")) or _numeric(row.value("funding_rate"))
```

If `funding == 0.0` and `funding_rate` is nonzero, cross-sectional funding
rank can silently use the fallback. This is small but real.

Change: replace the rank-metric fallback with the same explicit `None` check.

### 7. Binance AggTrade Direct Row Parser Has A Short-Row Guard Bug

The newer payload parser checks `len(values) < 7`; the older
`rows_from_binance_agg_trades_zip()` checks `< 6` and then reads `values[6]`.

Change: either align the guard to `< 7` or route the direct row parser through
the already-correct payload path.

### 8. Spread Units Are Ambiguous

`_observed_spread_bps()` treats `spread <= 1.0` as a fraction and otherwise as
bps. That can misread absolute price spreads from book ticker data.

Change: accepted research should require explicit spread units or separate
fields such as `spread_abs`, `spread_bps`, and `spread_fraction`.

Manual decision: issue #4 asks whether ambiguous spread should be rejected or
only deprecated.

### 9. Worker Claim And Stale Handling Need Multi-Worker Hardening

`claim_next()` selects a queued row and then upserts the claimed record without
an explicit conditional update or `BEGIN IMMEDIATE` style claim guard.
`mark_stale_jobs()` only considers `RUNNING`, so a worker that dies after
`CLAIMED` but before `RUNNING` can leave a stuck job.

Change: add an atomic claim-next transaction, stale claimed-job handling, and a
multi-worker claim-race regression.

### 10. Universe And Month Semantics Need Tightening

Universe rows can be built with aggregate coverage inputs, so accepted-evidence
eligibility depends on the caller passing correct per-instrument coverage
truth. `select_asof_universe()` chooses `max(snapshot_id)` for latest-date
ties, which is lexicographic over hashes.

The engine reports Jan 1 through Jul 31, 2024 as `usable_months=6`, although it
spans seven calendar months. This may be intentional calendar-delta behavior,
but accepted validation should define it explicitly.

Change: require per-instrument coverage joins for accepted universe evidence,
select latest snapshots by meaningful timestamp/manifest order, and specify
exact usable-month semantics.

Manual decision: issue #4 records the usable-month and universe policy choices.

## Stale Or Overstated Items In The Uploaded Audit

- The single-instrument `funding == 0.0` fallback was already fixed; the
  remaining issue is only in rank-mode metric scoring.
- "Add true vectorized engine" is valid, but the current engine is still useful
  as a reference engine. It should not be removed or rewritten first.
- Venue expansion should stay behind validation and engine hardening. More
  venues will not fix weak validation semantics.
- The external OF archive being large and gitignored is correct. It is not a
  defect.

## Self-Critique Of Current Agent-Written Code

The code is strong on boundary metadata and manifest discipline, but too much
of the math is still "research-platform normalized" rather than real-world
notional-aware. That is acceptable for early fixtures and smoke cycles, but it
is not enough for capacity claims.

The current validation gate is also too literal: it checks that fold rows exist
and are positive, but it does not ask whether the fold construction actually
proves robustness. Letting `full_window` count as accepted fold stability is
the clearest example.

Performance-wise, the repo overuses Python object loops and row dictionaries in
places where the data is already columnar. This was pragmatic for correctness,
but it is now the bottleneck on the user's hardware.

## Change Plan

### WPR-AUD-FIX-001: Accepted-Validation Hardening

Implement real fold-count requirements, fold generation mode, stricter trade
frequency/monthly stability gates after policy decision, and ledger fields for
the new diagnostics.

Primary paths:

- `src/tradingbotsuite/v2/validation/jobs.py`
- `src/tradingbotsuite/v2/ledger/service.py`
- `src/tradingbotsuite/v2/ledger/schemas.py`
- `src/tradingbotsuite/v2/backtest_engine/engine.py`
- `tests/v2/**`

### WPR-AUD-FIX-002: Cost And Capacity Realism

Add `account_notional_usd`, notional-aware participation, explicit spread
units, and funding sign metadata.

Primary paths:

- `src/tradingbotsuite/v2/costs/models.py`
- `src/tradingbotsuite/v2/backtest_engine/artifacts.py`
- `src/tradingbotsuite/v2/backtest_engine/engine.py`
- `docs/contracts/cost_model_contract.md`

### WPR-AUD-FIX-003: Fast Reference-Compatible Backtest Path

Keep the current Python loop as the reference engine and add an array-based
engine with parity tests. Reuse base turnover/position arrays for cost stress.

Primary paths:

- `src/tradingbotsuite/v2/backtest_engine/**`
- `src/tradingbotsuite/v2/strategy_specs/**`
- `tests/v2/test_backtest_engine_phase11.py`
- new benchmark/parity tests

### WPR-AUD-FIX-004: Backtest-Data I/O Fast Path

Use Arrow Dataset or Polars lazy scans for timestamp/instrument filtering and
column projection. Keep dict-row output only for small/reference surfaces.

Primary path:

- `src/tradingbotsuite/v2/backtest_data/service.py`

### WPR-AUD-FIX-005: Append Storage And Archive Materialization Scaling

Move ledgers and request manifests toward append parts plus compaction. Add
chunked Parquet writers and partition-local dedupe for central market history.
Parallelize OF-style feature materialization and write Parquet feature outputs
for downstream strategy loading.

Primary paths:

- `src/tradingbotsuite/v2/ledger/service.py`
- `src/tradingbotsuite/v2/backtest_data/service.py`
- `src/tradingbotsuite/v2/data_sources/central_market_history.py`
- `src/tradingbotsuite/v2/data_sources/of_style_materialization.py`

### WPR-AUD-FIX-006: Worker Concurrency Hardening

Add atomic claim-next behavior, claimed-job stale recovery, and multi-process
claim-race tests.

Primary path:

- `src/tradingbotsuite/v2/workers/job_store.py`

### WPR-AUD-FIX-007: Small Parser And Label Fixes

Fix cross-sectional funding fallback, aggTrade row length guard, Bybit provider
label decision, and exact usable-month semantics.

Primary paths:

- `src/tradingbotsuite/v2/strategy_specs/compiler.py`
- `src/tradingbotsuite/v2/data_sources/central_market_history_collection.py`
- `src/tradingbotsuite/v2/universe/hyperliquid.py`
- `src/tradingbotsuite/v2/backtest_engine/engine.py`

## Known-Issues Decision

No `docs/KNOWN_ISSUES.md` entry was added in this packet because the findings
are either manual policy choices or scoped hardening work, and no live/order/
sizing/runtime/promotion boundary breach was found. If the orchestrator wants
accepted-research validation semantics to be treated as currently blocking,
the fold-count and account-notional issues should be promoted to a P1 known
issue before advancing a new readiness stage.
