# WPR106-562 - V2 Autonomous Research Math Policy And Speed Implementation

Status: self_checked
Owner: Codex Research Agent
Date opened: 2026-06-29

## Scope

Implement the WPR106-561 autonomous research math-correctness roadmap and
selected reference-preserving speed improvements while preserving the v2
research-only boundary.

Priority order:

1. Add failing policy tests first.
2. Correct USD-notional capacity math and propagate `account_notional_usd`.
3. Add the 5 bps spread fallback and explicit spread-unit metadata.
4. Generate and validate monthly folds.
5. Update Lead Book trade-frequency and losing-month gates.
6. Fix zero funding handling and `next_bar_open` causality coverage.
7. Add speed improvements only after math policy is stable.

This packet must not create candidate-ready, paper-ready, live-ready,
trade-ready, order-ready, sizing-ready, runtime-mode, candidate-pack, or
promotion-ready implications.

## Allowed paths

- `docs/work_packets/WPR106-562-v2-autonomous-research-math-policy-and-speed-implementation.md`
- `src/tradingbotsuite/v2/costs/models.py`
- `src/tradingbotsuite/v2/backtest_engine/config.py`
- `src/tradingbotsuite/v2/backtest_engine/engine.py`
- `src/tradingbotsuite/v2/backtest_engine/artifacts.py`
- `src/tradingbotsuite/v2/backtest_data/service.py`
- `src/tradingbotsuite/v2/cli/main.py`
- `src/tradingbotsuite/v2/validation/walk_forward.py`
- `src/tradingbotsuite/v2/validation/jobs.py`
- `src/tradingbotsuite/v2/ledger/service.py`
- `src/tradingbotsuite/v2/lead_book/service.py`
- `src/tradingbotsuite/v2/autonomy/cycle_archive.py`
- `src/tradingbotsuite/v2/autonomy/strategy_queue.py`
- `src/tradingbotsuite/v2/strategy_specs/compiler.py`
- `src/tradingbotsuite/v2/workers/job_store.py`
- `tests/v2/test_cost_models_phase12.py`
- `tests/v2/test_backtest_engine_phase12.py`
- `tests/v2/test_validation_phase14.py`
- `tests/v2/test_validation_worker_phase32.py`
- `tests/v2/test_lead_book_phase15.py`
- `tests/v2/test_autopilot_archive_cycle_phase75.py`
- `tests/v2/test_workers_phase7.py`
- focused existing `tests/v2/**` files if needed to keep directly affected
  contracts coherent

## No-touch review

- No live/runtime, order-placement, sizing, promotion, candidate-pack truth,
  secret, local-state, or generated-evidence paths are in scope.
- Generated WPR106-556 evidence may be inspected but must not be rewritten by
  this packet.
- If stricter monthly folds, USD 10,000 capacity, or Lead Book gates make old
  evidence fail, the failure must be preserved and documented truthfully.
- Current source-family naming is intentional and must not be renamed.

## Implementation notes

- `account_notional_usd` default is `10000.0`.
- Capacity participation is
  `abs(weight_delta) * account_notional_usd / volume_notional`.
- Default spread fallback is `5.0` bps.
- Spread parsing prefers explicit `spread_bps` and explicit unit metadata.
- Usable-month calculation keeps existing calendar-delta semantics.
- Validation folds are monthly validation folds, capped at four tested calendar
  months. A single fold only passes when only one complete monthly fold is
  available.
- Lead Book trade frequency uses average trades over usable months, minimum
  `10`.
- Lead Book losing-month gate allows at most `4` losing months per year.

## Validation target

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

Broaden to `tests\v2 -q` if artifact schemas, ledger interfaces, or worker
behavior change broadly.

## Completion notes

Implemented and self-checked.

Math and policy changes:

- Added `account_notional_usd=10000.0` to cost/backtest configuration and run
  manifests.
- Changed capacity participation to
  `abs(weight_delta) * account_notional_usd / volume_notional`.
- Changed the default spread fallback to `5.0` bps and added spread/funding
  metadata to cost manifests.
- Added explicit spread-unit parsing that prefers `spread_bps` and explicit
  units before lenient raw-spread inference.
- Generated monthly validation folds from complete tested calendar months,
  capped at four, while preserving `full_window` as diagnostic fold metadata.
- Updated validation jobs and ledger fold summaries to count monthly validation
  folds rather than diagnostic full-window rows.
- Updated Lead Book gates to require at least `10` average trades per usable
  month and fail at more than `4` losing months per year.
- Fixed strategy compiler funding-rank scoring so `0.0` funding is a valid
  score.
- Added `next_bar_open` causality coverage.

Speed changes:

- Added PyArrow dataset scanner predicate pushdown for backtest panel loading,
  with fallback to the prior Parquet read path.
- Replaced repeated strategy compiler prior-row scans with per-row history
  indexes.
- Recomputed linear cost-stress scenarios from the base equity curve instead
  of re-running the simulation for each stress scenario.
- Added sidecar indexes for the canonical experiment ledger and backtest data
  request manifest, so duplicate checks can avoid full rewrites and ledger
  appends can concatenate Arrow tables on trusted indexed files.
- Made worker job claiming transaction-locked and added stale `claimed` job
  handling.
- Added strategy queue metadata caching for unchanged spec files.

No generated WPR106-556 evidence, Lead Book rows, ledgers, live/runtime,
order-placement, sizing, promotion, candidate-pack, secret, or local-state
paths were rewritten.

Validation completed:

```powershell
py -3.11 -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_cost_models_phase12.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_backtest_engine_phase12.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_validation_phase14.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_validation_worker_phase32.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_lead_book_phase15.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_autopilot_archive_cycle_phase75.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_workers_phase7.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_ledger_phase13.py tests\v2\test_backtest_data_phase9.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_strategy_specs_phase10.py tests\v2\test_autopilot_fixture_cycle_phase28.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2 -q
git diff --check
```

Results: compileall passed; focused requested tests passed; the added
strategy/fixture-cycle regressions passed; full `tests\v2 -q` passed with
`593` tests and one pre-existing FastAPI/Starlette warning; `git diff --check`
reported no whitespace errors and emitted existing CRLF line-ending warnings.
