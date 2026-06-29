# V2 Development Strategy After Final Audit Decisions

Date: 2026-06-29
Packet: WPR106-560
Inputs:

- Uploaded document: `C:\Users\papaa\Downloads\V2 Final Code Audit (1).docx`
- WPR106-559 repo/code/math/performance inspection
- User policy decisions from 2026-06-29
- Manual-review issue opened during WPR106-559:
  https://github.com/papaartemsmurf2002-commits/researchenginedeluxe/issues/4

## Boundary

This strategy is for a research-only, data-first v2 perpetual research
platform. It does not create candidate-pack, paper/live, order-placement,
sizing, runtime-mode, promotion, or production-trading readiness.

The invariant remains:

```json
{
  "research_only": true,
  "observe_only": true,
  "promotion_ready": false,
  "candidate_evidence": false,
  "candidate_pack_eligible": false,
  "live_signal": false,
  "paper_signal": false,
  "sizing_instruction": false,
  "order_placement_instruction": false,
  "runtime_mode_change": false
}
```

## Current Position

The repo has a solid research boundary and reproducibility foundation:

- v2 artifacts consistently carry research-only boundary fields;
- import/boundary tests exist;
- provider/archive intake, manifests, and hash-backed reports are strong;
- missing data is generally represented as blocker evidence rather than
  silently proxied;
- WPR106-546 proves 29 project symbols have lifecycle-scoped Binance USD-M 1m
  bar coverage through 2026-05;
- WPR106-552 proves a compact OF-style feature materialization pack from the
  external WPR106-549 raw archive;
- WPR106-556 reports manager-level `autonomous_research_ready=true` with zero
  blockers, but still not candidate, paper/live, order, sizing, runtime, or
  promotion readiness.

The next stage is not a broad rewrite. It is a controlled hardening program:
make accepted validation harder to fool, make capacity math more realistic,
remove known small correctness traps, then speed up the engine and data paths.

## Decisions Now Fixed

These decisions supersede the open questions from the uploaded audit and the
WPR106-559 manual-review list.

### Trade-Frequency Gate

Use average trades per usable month.

Rule:

```text
avg_trades_per_usable_month = trade_count / usable_months
pass if avg_trades_per_usable_month >= 10
```

Do not require every individual calendar month to have 10 trades. Individual
thin months should remain visible in diagnostics, but they should not fail the
gate by themselves if the average passes.

### Losing-Month Gate

Allow up to 4 losing months per year.

Rule:

```text
pass if losing_months_per_12m <= 4
```

For tested windows shorter than 12 months, report the observed losing-month
count and the annualized interpretation separately. Do not hide the shorter
window length.

### Fold Gate

Fold count is derived from the tested timeline. One fold equals one month.
The accepted fold target is capped at 4 folds.

Rule:

```text
available_monthly_folds = number of complete monthly test folds supported by the tested timeline
required_fold_count = min(4, max(1, available_monthly_folds))
pass if fold_count >= required_fold_count and fold_stability_score passes
```

Interpretation:

- `fold_count=1` can pass only when the tested timeline genuinely supports
  only one monthly fold.
- If the run has enough data to create more folds, it must be tested up to the
  4-fold cap.
- Because accepted research already requires at least 6 usable months, normal
  accepted-research runs should usually produce 4 monthly folds.
- Existing `full_window` fold rows may remain diagnostic, but accepted
  validation should record whether fold generation was `monthly_walk_forward`
  or `full_window_only`.

### Account Notional

Use a default account notional instead of requiring every run to declare one
manually.

Default:

```text
account_notional_usd = 10,000
```

Rationale:

- it makes capacity math dimensionally real;
- it matches a small-account research default rather than institutional sizing;
- larger-account capacity pressure can still be tested by overriding the
  default in stress runs.

Runs may override the default, but manifests must record the value used.

### Spread Assumption

Prefer explicit spread units, but keep fallback behavior lenient.

Default fallback:

```text
default_spread_bps = 5
default_spread_percent = 0.05 percent
```

Rules:

- prefer `spread_bps`, `spread_fraction`, or `spread_abs` with `spread_unit`;
- when spread is absent or ambiguous, use the configured 5 bps default;
- record whether the spread was observed, converted, or defaulted;
- do not silently treat absolute price spread as bps.

### Usable-Month Semantics

Keep the existing calendar-delta interpretation.

The current engine behavior that reports Jan 1 through Jul 31, 2024 as
`usable_months=6` remains the intended baseline. Future code should document
this rather than changing semantics silently.

### Bybit Index Provider Label

`provider="bybit_inverse"` in `build_bybit_index_plan()` is intentional
source-family naming. It is not a bug unless later source-family work changes
the provider taxonomy.

Future work should document this label and add a regression test so another
agent does not "fix" it by accident.

## Validated Audit Findings

### Accepted Validation Is Too Easy To Satisfy Today

WPR106-556 passed accepted validation with:

- `fold_count=1`
- `fold_id=full_window`
- `fold_stability_score=1.0`

Under the new policy, that accepted run should be rerun or revalidated with
monthly folds because the tested timeline has enough data to support more than
one fold.

### Capacity Math Needs Account Notional

The current participation formula uses normalized weight turnover divided by
USD volume. That is mathematically weak for real capacity.

Observed WPR106-556 example:

- turnover: `0.025`
- bar volume notional: `92,487,298.3102`
- current reported participation: `2.7030738768204313e-10`
- with default `account_notional_usd=10,000`, participation would be
  `0.0000027031`
- with `account_notional_usd=100,000,000`, participation would be
  `0.0270307388`

The new default account notional fixes the unit mismatch while keeping the
return series normalized.

### Current Lead Book And Validation Gates Are Misaligned With Desired Gates

Current Lead Book gates use five average trades/month and six losing
months/year. New desired gates are:

- average trades per usable month >= 10;
- losing months per 12 months <= 4.

Validation, ledger, Lead Book, and readiness summaries should all report the
same fields so agents cannot pass one surface and fail another silently.

### Spread Handling Needs Explicit Provenance

Current spread logic can treat `spread <= 1.0` as a fraction and larger values
as bps. That is unsafe when data could contain an absolute price spread.

The new policy is lenient but explicit: prefer unit-tagged spread fields and
fall back to 5 bps when no reliable unit is available.

### Cost Stress Is Mathematically Fine But Too Slow

Base, 2x, and 3x cost stress values scale correctly in the inspected run. The
performance problem is that stress scenarios rerun the whole simulation. The
engine should reuse base signals, weights, returns, and turnover, then
recompute stressed costs.

### Backtest Data Loading And Ledger Appends Need Columnar Scaling

The current loader reads Parquet columns then uses `to_pylist()` and Python
timestamp filtering. Ledger append reads and rewrites the full Parquet file.

This is safe but not scalable. It should move to Arrow Dataset or Polars
predicate/projection pushdown and part-based append storage.

### Small Correctness Fixes Remain

Confirmed small items:

- cross-sectional funding rank still has a `0.0` fallback edge;
- direct Binance aggTrade row parser checks `< 6` but reads index `6`;
- accepted fold generation needs mode metadata;
- month/fold diagnostics need clear calendar-delta labeling.

Stale or resolved items:

- single-instrument funding carry already uses an explicit `None` check;
- Bybit index provider label is intentional;
- large external OF archive being gitignored is correct.

## Development Strategy

### Phase 1: Codify Policy In Contracts And Tests

Goal: make the new decisions machine-readable before changing behavior.

Work:

- update validation, ledger, Lead Book, and cost contracts;
- add tests that encode:
  - `avg_trades_per_usable_month >= 10`;
  - `losing_months_per_12m <= 4`;
  - monthly fold requirement capped at 4;
  - default `account_notional_usd=10,000`;
  - default spread fallback of 5 bps;
  - existing calendar-delta usable-month semantics;
  - `bybit_inverse` as intentional source-family naming.

Expected result:

- no runtime behavior changes until the policy tests clearly define expected
  behavior;
- future agents cannot reinterpret the decisions.

### Phase 2: Accepted-Validation Hardening

Goal: stop accepted research from passing on one `full_window` fold when the
timeline supports more.

Work:

- generate monthly fold metrics from the tested timeline;
- record `fold_generation_mode`;
- calculate `required_fold_count` from available monthly folds, capped at 4;
- fail accepted validation when enough folds exist but are missing;
- compute monthly returns and losing-month diagnostics from equity curves;
- compute average trades per usable month using existing calendar-delta
  usable months.

Primary paths:

- `src/tradingbotsuite/v2/backtest_engine/engine.py`
- `src/tradingbotsuite/v2/validation/jobs.py`
- `src/tradingbotsuite/v2/ledger/service.py`
- `src/tradingbotsuite/v2/ledger/schemas.py`
- `src/tradingbotsuite/v2/lead_book/service.py`

### Phase 3: Cost And Capacity Realism

Goal: make cost/capacity math dimensionally meaningful without changing the
research-only boundary.

Work:

- add `account_notional_usd` to cost/backtest config and manifests;
- compute `trade_notional_usd = abs(weight_delta) * account_notional_usd`;
- compute `participation_rate = trade_notional_usd / bar_volume_notional_usd`;
- preserve normalized return costs:

```text
cost_return = trade_notional_usd * bps / account_notional_usd / 10000
```

- add explicit spread source fields:
  - `spread_bps`;
  - `spread_fraction`;
  - `spread_abs`;
  - `spread_unit`;
  - `spread_source = observed | converted | defaulted`;
- default to 5 bps when no safe observed spread is available.

Primary paths:

- `src/tradingbotsuite/v2/costs/models.py`
- `src/tradingbotsuite/v2/backtest_engine/artifacts.py`
- `src/tradingbotsuite/v2/backtest_engine/engine.py`
- `docs/contracts/cost_model_contract.md`

### Phase 4: Small Correctness Fixes

Goal: remove localized traps before optimizing.

Work:

- fix cross-sectional funding rank fallback to preserve `0.0`;
- fix Binance aggTrade row length guard or route direct row parsing through the
  correct payload parser;
- document/test Bybit index source-family naming;
- document/test existing calendar-delta usable-month semantics.

Primary paths:

- `src/tradingbotsuite/v2/strategy_specs/compiler.py`
- `src/tradingbotsuite/v2/data_sources/central_market_history_collection.py`
- `src/tradingbotsuite/v2/backtest_engine/engine.py`
- `src/tradingbotsuite/v2/universe/hyperliquid.py`

### Phase 5: Fast Backtest And Cost-Stress Path

Goal: keep the current Python engine as reference and add a faster
reference-compatible lane.

Work:

- preserve current engine as `reference_engine_python`;
- add an array-based engine using time x instrument x field panels;
- add parity tests between reference and fast lanes;
- reuse base simulation arrays for stress-cost recomputation;
- record benchmark timing artifacts but do not make GPU speed claims yet.

Primary paths:

- `src/tradingbotsuite/v2/backtest_engine/**`
- `src/tradingbotsuite/v2/strategy_specs/**`
- `tests/v2/test_backtest_engine_phase11.py`

### Phase 6: Backtest-Data And Ledger I/O Scaling

Goal: stop turning columnar data into Python objects before filtering.

Work:

- use Arrow Dataset or Polars scans for timestamp/instrument filters;
- push down requested columns;
- return columnar panels to the fast engine;
- keep dict rows only for reference/small surfaces;
- move ledger/request appends to part-based storage plus compaction.

Primary paths:

- `src/tradingbotsuite/v2/backtest_data/service.py`
- `src/tradingbotsuite/v2/ledger/service.py`

### Phase 7: Worker Concurrency Hardening

Goal: make durable jobs safe under multiple local workers.

Work:

- make claim-next atomic with an explicit transaction or conditional update;
- mark stale `CLAIMED` jobs, not only stale `RUNNING` jobs;
- add multi-worker claim-race regression tests.

Primary path:

- `src/tradingbotsuite/v2/workers/job_store.py`

### Phase 8: Archive And OF-Feature Scaling

Goal: let the strong local SSD/RAM hardware matter.

Work:

- use chunked Parquet writers and partition-local dedupe;
- parallelize OF-style source materialization with bounded process workers;
- write Parquet feature outputs for strategy loading;
- keep JSONL only for debug or compact proof outputs.

Primary paths:

- `src/tradingbotsuite/v2/data_sources/central_market_history.py`
- `src/tradingbotsuite/v2/data_sources/of_style_materialization.py`

### Phase 9: Venue Probe Expansion

Goal: expand useful comparison data only after math and validation are harder
to fool.

Priority:

- Bitget candle/mark/index history probes;
- Bybit OI/funding pagination proof;
- OKX pagination confirmation;
- MEXC/Gate availability probes.

Rules:

- venue probes are data lanes, not trading lanes;
- preserve provider provenance;
- do not relabel Binance, Bybit, Bitget, OKX, MEXC, or Gate as
  Hyperliquid-native;
- do not use venue expansion to compensate for missing validation strength.

## What Not To Do

- Do not turn manager research readiness into candidate, paper, live, sizing,
  order, runtime, or promotion readiness.
- Do not chase requester-pays Hyperliquid official history unless the operator
  explicitly opens a paid/gated packet.
- Do not rewrite old generated evidence to make it pass new gates.
- Do not remove the current Python engine before the fast engine has parity
  evidence.
- Do not expand venues before validation and cost math are hardened.

## Main Things I Will Do

1. Convert these decisions into contract language and focused tests.
2. Harden accepted validation around average trades per usable month, losing
   months, and timeline-derived monthly folds capped at 4.
3. Add USD 10,000 default account-notional capacity math and 5 bps default
   spread handling with provenance.
4. Fix the small rank-funding and aggTrade parser issues.
5. Preserve the current engine as reference while adding a faster array-based
   lane and no-rerun cost stress.
6. Replace Python-row Parquet filtering and whole-file append patterns with
   columnar scans and part-based storage.
7. Harden worker claim/stale behavior for multi-worker runs.
8. Scale OF-style materialization only after the validation/cost semantics are
   locked.
9. Add venue probes last, as comparison data only.

## Success Criteria

The development strategy is successful when:

- accepted research cannot pass with `full_window_only` if monthly folds are
  available;
- every accepted result reports average trades per usable month and losing
  months under the agreed gates;
- capacity metrics are account-notional-aware;
- spread assumptions are explicit or defaulted to 5 bps with provenance;
- fast engine results match the reference engine on fixtures;
- cost stress no longer reruns full simulation;
- backtest-data loading uses columnar predicate/projection pushdown;
- ledgers and request manifests can grow without O(n squared) rewrite cost;
- worker claims are race-safe;
- all artifacts remain research-only and non-promotable.
