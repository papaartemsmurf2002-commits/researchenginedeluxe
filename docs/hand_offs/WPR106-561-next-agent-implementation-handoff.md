# WPR106-561 Next Agent Implementation Handoff

Date: 2026-06-29
Source roadmap:
`docs/audit/V2_AUTONOMOUS_RESEARCH_MATH_PERFORMANCE_FINAL_ROADMAP_2026_06_29.md`

## Objective

Implement the math-correctness fixes and selected performance improvements for
the v2 autonomous research path while preserving the research-only boundary.

The next agent should open a new work packet before coding. A suggested packet
name is:

`docs/work_packets/WPR106-562-v2-autonomous-research-math-policy-and-speed-implementation.md`

## Required Context Reads

Read these first:

- `AGENTS.md`
- `docs/RESEARCH_AGENT_QUICKSTART.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/PRODUCT_SCOPE.md`
- `docs/V2_DECISION_REGISTER.md`
- `docs/V2_NO_TOUCH_PATHS.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md`
- `docs/audit/V2_AUTONOMOUS_RESEARCH_MATH_PERFORMANCE_FINAL_ROADMAP_2026_06_29.md`

Then run:

```powershell
$env:PYTHONPATH='src'; py -3.11 -m tradingbotsuite.v2.cli.main autonomy agent-context --repo-root .
```

Use the agent-context output as the current boundary truth. As of this handoff,
the manager readiness context is narrow and research-only; it is not a
candidate, paper, live, signal, order, sizing, or promotion claim.

## Decisions Already Made

Implement these exactly unless a later orchestrator decision supersedes them:

- `account_notional_usd` default is USD `10,000`.
- Default spread fallback is `5` bps.
- Spread parsing is lenient but must prefer explicit units and explicit
  `spread_bps`.
- Usable months keep the existing calendar-delta semantics.
- One validation fold equals one tested calendar month, capped at four folds.
- `fold_count=1` can pass only when the tested timeline cannot produce more
  than one complete monthly fold.
- Trade frequency is the mean over usable months, with minimum `10` trades per
  usable month.
- Losing-month gate allows at most `4` losing months per year.
- Current source-family naming is intentional and should not be renamed.

## Suggested Allowed Paths

For the implementation packet, include only the paths actually edited. Likely
source paths:

- `src/tradingbotsuite/v2/costs/models.py`
- `src/tradingbotsuite/v2/backtest_engine/config.py`
- `src/tradingbotsuite/v2/backtest_engine/engine.py`
- `src/tradingbotsuite/v2/backtest_engine/artifacts.py`
- `src/tradingbotsuite/v2/validation/walk_forward.py`
- `src/tradingbotsuite/v2/validation/jobs.py`
- `src/tradingbotsuite/v2/ledger/service.py`
- `src/tradingbotsuite/v2/lead_book/service.py`
- `src/tradingbotsuite/v2/autonomy/cycle_archive.py`
- `src/tradingbotsuite/v2/strategy_specs/compiler.py`
- `src/tradingbotsuite/v2/backtest_data/service.py`
- `src/tradingbotsuite/v2/workers/job_store.py`
- focused tests under `tests/v2/**`
- docs/contracts or work-packet docs updated by the patch

Do not touch live, paper, order, sizing, promotion, candidate-pack, runtime
mode, secret, local-state, or generated evidence paths unless a new packet
explicitly allows a bounded evidence refresh.

## Implementation Order

### 1. Add Failing Tests First

Create or update focused tests for:

- USD-notional capacity participation:
  `participation_rate = abs(weight_delta) * account_notional_usd / volume_notional`.
- Default `account_notional_usd=10000.0` in cost/backtest configs and
  manifests.
- Default `spread_bps=5.0`, while explicit spread values override it.
- `0.0` funding score in the strategy compiler.
- Monthly fold expected count from tested timeline, capped at four.
- Rejection when a run has only `full_window` fold evidence despite enough
  monthly timeline.
- Lead Book minimum `10` trades per usable month.
- Lead Book fail at `5` losing months per year.
- `next_bar_open` signal causality.

### 2. Implement Cost And Spread Math

Update `CostModelConfig`, cost manifests, backtest config plumbing, and archive
cycle defaults.

Keep normalized fee/spread/slippage/impact costs as return fractions. Only the
capacity participation and nonlinear impact/capacity interpretation should
change because of account notional.

### 3. Implement Monthly Folds And Validation

Add a monthly fold generator and artifact metadata that distinguishes monthly
validation folds from `full_window` diagnostics. Update validation jobs so the
expected fold count comes from the tested timeline.

If an older fixture intentionally has only one usable month, keep one-fold
passes valid. If it has multiple complete months, require the monthly fold
count up to four.

### 4. Update Lead Book Gates

Change the gate policy to:

- `avg_trades_per_usable_month >= 10`
- `losing_months_per_year <= 4`

Prefer actual run-derived metrics over archive-cycle placeholder inputs. If a
temporary compatibility field is needed for old evidence, keep it clearly
marked as legacy-readable and do not use it for new pass/fail truth.

### 5. Fix Small Correctness Edge Cases

In `strategy_specs/compiler.py`, replace the funding score falsy fallback with
an explicit `None` check so `0.0` is preserved.

Add or update metadata/tests that document funding sign convention and
`next_bar_open` causality.

### 6. Add Speed Work After Math Is Stable

Prioritize these only after tests for math policy pass:

- PyArrow scanner/predicate pushdown in `backtest_data/service.py`.
- Rolling per-instrument state in `strategy_specs/compiler.py`.
- Stress scenario reuse in `backtest_engine/engine.py`.
- Append/index improvements in `ledger/service.py` and data manifests.
- Atomic job claiming and stale `claimed` handling in `workers/job_store.py`.

Keep the existing row-based backtest path as the reference until parity is
proven.

## Evidence Caveat

The WPR106-556 cycle currently passes narrow manager readiness, but it used one
`full_window` fold and capacity participation with normalized turnover divided
directly by USD volume. After this implementation, a WPR106-556-style rerun may
fail. That is acceptable if the failure reflects the new policy truth.

Do not tune or weaken gates to preserve the old pass.

## Validation Commands

Minimum validation after source edits:

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

Broaden to `tests\v2 -q` if artifact schemas, ledger contracts, backtest
outputs, or worker behavior change broadly.

## Stop Conditions

Stop and record a blocker instead of forcing a pass if:

- monthly folds reveal unstable month-level performance;
- USD 10,000 capacity participation breaches limits;
- explicit spread units conflict with inferred units;
- optimized paths cannot match reference outputs within a documented tolerance;
- implementation would require touching live, paper, order, sizing, promotion,
  candidate-pack, secret, local-state, or generated-evidence paths outside the
  new packet.
