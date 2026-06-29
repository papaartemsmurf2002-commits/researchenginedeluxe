# V2 Autonomous Research Math And Performance Final Roadmap

Date: 2026-06-29
Packet: `docs/work_packets/WPR106-561-v2-autonomous-research-math-performance-roadmap.md`
Status: final roadmap for future implementation

## Boundary

This roadmap is research-only. It does not make any paper, live, trade-ready,
order-ready, sizing-ready, candidate-pack-ready, or promotion-ready claim. The
current narrow manager readiness result remains only an autonomous research
manager context claim: `autonomous_research_ready=true`,
`research_only=true`, `observe_only=true`, and `promotion_ready=false`.

No source behavior, ledgers, generated research evidence, Lead Book rows, live
configuration, order placement code, or runtime mode files were changed by this
packet.

## Current Verdict

The autonomous research path is usable as a bounded research harness, but the
math and validation policy are not yet strict enough for a stronger accepted
research claim. The most important gaps are:

- capacity participation currently mixes normalized turnover with USD volume;
- validation fold proof currently allows a single `full_window` fold where
  monthly folds should be required when the tested timeline supports them;
- Lead Book gates still encode older trade-frequency and losing-month
  thresholds;
- spread and account-notional assumptions are not explicit enough in cost
  manifests;
- several autonomous research loops are correct enough for small evidence runs
  but will become slow in broader sweeps.

The WPR106-556 readiness cycle should therefore be treated as a narrow manager
readiness pass, not as final strategy validation. Its final run reported
positive base and stress net return, but its fold artifact contained only one
`full_window` row, and a sampled trade showed the capacity unit mismatch:
`turnover=0.025` was divided directly by about `92,487,298` USD volume. With
the chosen default account notional of USD 10,000, the participation should be
`0.025 * 10000 / 92487298.3102 = 0.0000027031`, not
`0.025 / 92487298.3102`.

## User Decisions To Enforce

- Account notional default: USD `10,000`.
- Default spread fallback: `5` bps.
- Spread parsing: lenient, prefer explicit units and explicit `spread_bps`;
  convert fractional spread only when units are absent and record provenance.
- Usable-month calculation: keep the existing calendar-delta semantics.
- Fold policy: one validation fold equals one tested calendar month, capped at
  four folds. `fold_count=1` is acceptable only when the tested timeline cannot
  produce more than one complete monthly fold.
- Trade-frequency policy: use the mean average over usable months, with a
  default minimum of `10` trades per usable month.
- Losing-month policy: allow at most `4` losing months per year.
- Source-family naming: keep the current intentional source-family naming.

## Math Correctness Roadmap

### 1. Capacity And Account Notional

Affected areas:

- `src/tradingbotsuite/v2/costs/models.py`
- `src/tradingbotsuite/v2/backtest_engine/config.py`
- `src/tradingbotsuite/v2/backtest_engine/engine.py`
- `src/tradingbotsuite/v2/autonomy/cycle_archive.py`
- cost manifests and focused cost/backtest tests

Required changes:

- Add `account_notional_usd=10000.0` to cost and backtest configuration.
- Include `account_notional_usd` in cost manifests, run manifests, and any
  validation artifact that interprets capacity.
- Compute:
  - `trade_notional_usd = abs(weight_delta) * account_notional_usd`
  - `participation_rate = trade_notional_usd / volume_notional`
- Keep normalized fee, spread, slippage, impact, and funding costs as return
  fractions of account equity.
- Rework capacity tests so volume participation is checked with real USD
  notional, including a regression based on the WPR106-556 sampled trade.

Expected outcome:

- Capacity and impact gates become materially stricter for low-liquidity
  instruments while preserving comparable return-denominated cost accounting.

### 2. Monthly Fold Validation

Affected areas:

- `src/tradingbotsuite/v2/backtest_engine/engine.py`
- `src/tradingbotsuite/v2/validation/walk_forward.py`
- `src/tradingbotsuite/v2/validation/jobs.py`
- `src/tradingbotsuite/v2/ledger/service.py`
- validation and backtest-engine tests

Required changes:

- Generate monthly validation fold rows from the tested window instead of only
  a single `full_window` fold.
- Preserve `full_window` as a diagnostic row only, or mark it with a
  non-validation fold family.
- Compute the expected monthly fold count from complete tested calendar months:
  `expected = min(4, complete_test_months_available)`.
- Accept `fold_count=1` only when `expected == 1`.
- Validation must fail when enough timeline exists for more folds but the run
  provides fewer monthly folds.
- Store fold-family metadata so ledger and validation jobs can distinguish
  monthly validation folds from full-window diagnostics.

Expected outcome:

- A run that passes fold stability has actually survived month-level checks
  over the tested timeline.

### 3. Lead Book Gate Policy

Affected areas:

- `src/tradingbotsuite/v2/lead_book/service.py`
- `src/tradingbotsuite/v2/autonomy/cycle_archive.py`
- `src/tradingbotsuite/v2/ledger/service.py`
- Lead Book and autonomous archive-cycle tests

Required changes:

- Replace the current minimum-five-trades policy with:
  `avg_trades_per_usable_month >= 10`.
- Replace the current six-losing-months failure with:
  `losing_months_per_year <= 4`; fail at `5` or more.
- Compute the average over usable months, not over a hard-coded denominator.
- Bind Lead Book gate inputs to actual run artifacts where possible, rather
  than relying on archive-cycle placeholder defaults.
- Update gate names and tests while preserving any necessary legacy-readable
  aliases in old evidence paths.

Expected outcome:

- Lead Book rows reflect the user's chosen acceptance policy and do not pass
  because of placeholder gate inputs.

### 4. Spread, Funding, And Source Semantics

Affected areas:

- `src/tradingbotsuite/v2/costs/models.py`
- `src/tradingbotsuite/v2/backtest_engine/engine.py`
- `src/tradingbotsuite/v2/strategy_specs/compiler.py`
- `src/tradingbotsuite/v2/autonomy/cycle_archive.py`

Required changes:

- Set the default spread fallback to `5` bps.
- Prefer explicit `spread_bps` and explicit spread units.
- When only raw spread is present, retain lenient conversion but record whether
  the source was interpreted as a fraction or bps.
- Fix the funding metric score path in the strategy compiler so `0.0` funding
  is treated as a valid value instead of falling through because it is falsy.
- Add manifest metadata for funding interval units and sign convention. The
  current engine sign convention, `-applied_weight * funding_rate`, is correct
  when positive funding means longs pay shorts and the rate is an interval
  return.
- Add a causality regression for `next_bar_open`: a signal computed from a
  completed bar must apply to the next row's open-to-close return, not to the
  same row it just observed.

Expected outcome:

- Cost manifests become auditable enough to explain spread and funding math,
  and zero funding values no longer risk being mis-scored.

## Performance Roadmap

These are speed improvements, not permission to relax validation or boundary
rules. Each optimization needs parity tests against the existing implementation.

### 1. Columnar Panel Loading

Affected area: `src/tradingbotsuite/v2/backtest_data/service.py`

Current issue:

- Parquet files are read into Python rows with `to_pylist()`, and timestamp
  filtering is mostly performed in Python.

Plan:

- Use PyArrow dataset/scanner predicate pushdown on `ts`, `instrument_id`, and
  timeframe.
- Read only required columns for the strategy/backtest configuration.
- Stream record batches where possible.
- Keep the existing manifest and temporal-policy checks intact.

### 2. Strategy Compiler Rolling State

Affected area: `src/tradingbotsuite/v2/strategy_specs/compiler.py`

Current issue:

- `_prior_rows` scans instrument history for each row and each metric, creating
  an avoidable O(n^2) pattern for long 1m panels.

Plan:

- Maintain per-instrument rolling windows and precomputed arrays for momentum,
  volatility, ATR, funding, basis, and volume metrics.
- Reuse sorted row indexes instead of re-filtering prior rows.
- Add parity tests that compare old and new scores/targets on small fixtures.

### 3. Array-Based Backtest Core

Affected area: `src/tradingbotsuite/v2/backtest_engine/engine.py`

Current issue:

- The engine materializes `_PanelRow` objects and loops by timestamp and
  instrument. This is clear and inspectable but slow for broad sweeps.

Plan:

- Build an optional array lane using timestamp-by-instrument matrices for
  returns, target weights, applied weights, funding, turnover, and cost terms.
- Emit the same positions, trades, equity, metrics, manifests, and validation
  artifacts as the current engine.
- Keep the current row engine as the reference implementation until parity is
  proven on representative fixtures.

### 4. Stress Scenario Reuse

Affected area: `src/tradingbotsuite/v2/backtest_engine/engine.py`

Current issue:

- Cost stress scenarios rerun the simulation once per scenario.

Plan:

- Compute gross returns, turnover, funding PnL, observed spread, and base cost
  arrays once.
- Recalculate stress net returns and stress equity curves from those arrays
  when scenario changes are linear.
- Rerun the full simulation only when capacity or nonlinear impact policy can
  change trade blocking or target application.

### 5. Ledger And Manifest Writes

Affected areas:

- `src/tradingbotsuite/v2/ledger/service.py`
- `src/tradingbotsuite/v2/backtest_data/service.py`

Current issue:

- Some append paths read and rewrite whole Parquet ledgers/manifests.

Plan:

- Move high-churn append paths to partitioned append files or a small SQLite
  index plus periodic Parquet compaction.
- Use DuckDB or Arrow scans for leaderboard and fold summary queries.
- Preserve deterministic IDs, auditability, and append-only semantics.

### 6. Worker Concurrency And Claiming

Affected area: `src/tradingbotsuite/v2/workers/job_store.py`

Current issue:

- Job claiming is effectively select-then-update, and stale handling focuses
  on running jobs.

Plan:

- Use an atomic claim operation, for example `UPDATE ... WHERE status='queued'
  RETURNING ...` inside a transaction where supported.
- Mark stale `claimed` jobs as well as stale `running` jobs.
- Add tests for two worker connections racing to claim the same job.

### 7. Strategy Queue Caching

Affected area: `src/tradingbotsuite/v2/autonomy/strategy_queue.py`

Current issue:

- Queue discovery can re-read and re-validate every strategy file on each pass.

Plan:

- Cache parsed strategy metadata by file path, size, mtime, and content hash.
- Re-validate only changed files.
- Keep the existing max-file cap and research-boundary validation.

## Suggested Implementation Phases

### Phase 0 - Tests First

Add focused failing tests for:

- account notional participation math;
- `account_notional_usd=10000.0` default propagation;
- `5` bps spread fallback and explicit-unit preference;
- `0.0` funding as a valid compiler score;
- monthly fold count policy;
- Lead Book `10` trades per usable month and max `4` losing months per year;
- `next_bar_open` causality semantics.

### Phase 1 - Cost And Spread Math

Implement account-notional capacity math, cost-manifest metadata, and the 5 bps
spread fallback. Keep return-denominated transaction cost outputs comparable to
existing metrics.

### Phase 2 - Fold And Gate Policy

Implement monthly fold artifacts and validation requirements. Then update Lead
Book gates and archive-cycle gate inputs so validation and Lead Book agree.

### Phase 3 - Reference-Preserving Speed Work

Optimize panel loading, strategy compilation, and cost stress computation with
parity tests against current fixtures. Keep the current row-oriented backtest
path available as a reference until array parity is proven.

### Phase 4 - Storage And Worker Throughput

Improve ledger/manifests and worker claiming after math policy is stable. These
changes are important for large autonomous sweeps but should not be mixed with
the first math-correctness patch unless the patch is small and well tested.

### Phase 5 - Evidence Refresh

Rerun the bounded archive-readiness flow only after the source changes and
tests pass. If WPR106-556-style evidence fails under stricter folds, capacity,
or Lead Book gates, record the blocker truthfully. Do not tune around the new
rules just to preserve a previous pass.

## Validation Expectations For The Implementation Agent

Minimum source-change validation:

```powershell
py -3.11 -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_cost_models_phase12.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_backtest_engine_phase12.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_validation_phase14.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_validation_worker_phase32.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_lead_book_phase15.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_autopilot_archive_cycle_phase75.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_workers_phase7.py -q
git diff --check
```

Broaden to `tests\v2 -q` when shared contracts, artifact schemas, or ledger
interfaces change.

## Manual Review Points

- If monthly folds cause a previously passing run to fail, preserve the failure
  and review the actual month-level returns before deciding whether the
  strategy remains useful.
- If USD 10,000 capacity participation causes low-liquidity symbols to fail,
  keep the capacity blocker unless the data source volume units are proven
  wrong.
- If spread fields disagree across source families, prefer explicit source
  units and record the conversion in the manifest.
- If optimized engines produce tiny numerical differences, require a written
  tolerance policy before accepting parity.

## Self-Critique Of The Current Code Path

The current implementation favors traceability over scale. That was a sensible
early research choice, but it also allowed several policy assumptions to live
as implicit defaults instead of explicit artifact fields. The most serious math
issue is not the return-cost formula; it is the dimension mismatch in capacity
participation. The most serious validation issue is allowing a single
full-window fold to stand in for monthly fold evidence when the tested timeline
can support more folds. The most serious performance issue is repeated Python
row materialization and prior-row scanning over large panels.

The next implementation should therefore improve the math first, then optimize
only with parity tests and unchanged research-boundary semantics.
