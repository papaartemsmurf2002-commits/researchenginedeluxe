# WPR106-564 - V2 Autonomous Research Fast Engine And Storage Scale

Status: self_checked
Owner: Codex Research Agent
Date opened: 2026-06-29

## Scope

Implement the PR #5 follow-up scaling phase described by
`docs/hand_offs/WPR106-563-pr5-followup-implementation-goal.md` while keeping
WPR106-562 math and policy behavior intact.

This packet adds an optional fast array/columnar backtest lane with parity
coverage against the existing Python row engine, a columnar backtest-data slice
path, part-based ledger append storage, and accepted-research spread-unit
strictness. Chunked OF materialization and venue probe expansion remain later
lower-priority scale work unless explicitly added by a follow-up packet.

## Allowed paths

- `docs/work_packets/WPR106-564-v2-autonomous-research-fast-engine-and-storage-scale.md`
- `src/tradingbotsuite/v2/backtest_data/schemas.py`
- `src/tradingbotsuite/v2/backtest_data/service.py`
- `src/tradingbotsuite/v2/backtest_data/__init__.py`
- `src/tradingbotsuite/v2/backtest_engine/artifacts.py`
- `src/tradingbotsuite/v2/backtest_engine/engine.py`
- `src/tradingbotsuite/v2/backtest_engine/jobs.py`
- `src/tradingbotsuite/v2/backtest_engine/__init__.py`
- `src/tradingbotsuite/v2/costs/models.py`
- `src/tradingbotsuite/v2/ledger/service.py`
- `src/tradingbotsuite/v2/ledger/__init__.py`
- `tests/v2/test_backtest_data_phase9.py`
- `tests/v2/test_backtest_engine_phase11.py`
- `tests/v2/test_backtest_engine_phase12.py`
- `tests/v2/test_cost_models_phase12.py`
- `tests/v2/test_ledger_phase13.py`
- focused existing `tests/v2/**` files if directly required by changed
  contracts

## No-touch review

- Do not touch live/runtime, order-placement, sizing, promotion,
  candidate-pack truth, secret, local-state, or generated historical evidence
  paths.
- Do not rewrite WPR106-556 generated evidence, existing ledgers, Lead Book
  rows, or old outputs.
- Do not change trade-frequency policy or losing-month policy.
- Do not weaken WPR106-562 account-notional capacity math, 5 bps spread
  fallback, monthly validation folds, zero-funding handling, or `next_bar_open`
  causality.
- Keep the existing Python row engine as the correctness reference.

## Implementation plan

1. Add a `BacktestColumnarDataSlice` and service method that returns an Arrow
   table after the same manifest, coverage, universe, lockbox, projection, and
   predicate-pushdown checks as the row path.
2. Add an optional `fast_vectorized` engine lane. The lane uses columnar/table
   input, builds timestamp-by-instrument arrays for returns, target/applied
   weights, turnover, funding, volume, spread, and costs, and emits the same
   artifact contract as the reference lane.
3. Add parity tests comparing reference and fast metrics/artifacts on fixtures
   with documented numerical tolerance.
4. Move canonical ledger appends to part files plus an append log and sidecar
   index while preserving legacy compacted Parquet reads and exports.
5. Add accepted-research spread strictness so raw ambiguous `spread` values
   without units fail in strict accepted mode, while sandbox/legacy lenient
   inference and the 5 bps fallback remain compatible.

## Validation target

```powershell
py -3.11 -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_backtest_data_phase9.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_backtest_engine_phase11.py tests\v2\test_backtest_engine_phase12.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_cost_models_phase12.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_ledger_phase13.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_workers_phase7.py -q
git diff --check
```

Broaden to `tests\v2 -q` if artifact schemas or worker behavior change broadly.

## Completion notes

Implemented and self-checked:

- Added `BacktestColumnarDataSlice` and `BacktestDataService.load_panel_columnar()`.
  The existing row loader now uses the same Arrow table scanner underneath,
  preserving coverage, universe, lockbox, manifest, projection, and predicate
  checks while exposing table output for fast consumers.
- Added `EngineLane.FAST_VECTORIZED` as an opt-in lane. The existing
  `vectorized` Python row engine remains the reference path. The fast lane
  accepts Arrow table input, builds timestamp-by-instrument arrays for applied
  weights, target weights, returns, turnover, funding, spread, volume, capacity,
  and costs, and emits the same run artifact contract.
- Added parity coverage comparing fast-lane metrics and equity rows against
  the reference engine on fixture data.
- Added part-backed ledger append storage with `parts/`, `append_log.jsonl`,
  a sidecar part index, duplicate protection, part-aware reads/leaderboards,
  and `compact_ledger_parts()`. A zero-row logical Parquet placeholder preserves
  existing path-existence compatibility while new rows append to parts.
- Updated ledger workers and Lead Book source hashing to handle part-backed
  ledgers without requiring a rewritten compacted table.
- Added accepted-research strict spread-unit handling through
  `spread_observation_policy=accepted_research_strict`. Explicit `spread_bps`
  or explicit units pass; ambiguous raw `spread` blocks in strict mode; missing
  spread still uses the 5 bps configured fallback; lenient legacy behavior
  remains the default.

Deferred:

- Chunked full OF materialization and venue probe expansion remain later
  lower-priority scale packets. This packet did not collect data, expand venue
  probes, or rewrite generated evidence.

Validation completed:

```powershell
py -3.11 -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\contracts -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2 -q
git diff --check
```

Results: compileall passed; contracts passed with `463` tests; full v2 passed
with `599` tests; `git diff --check` reported no whitespace errors and emitted
the existing LF-to-CRLF working-copy warnings.
