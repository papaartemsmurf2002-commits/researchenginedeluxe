# WPR106-554 - V2 autonomous readiness with uploaded test strategies

## Status

Blocked for `autonomous_research_ready` claim.

## Objective

Use `C:\Users\papaa\Downloads\test strategies.txt` as the strategy input for the
next autonomous-readiness pass and move the repository as close as truthfully
possible to `autonomous_research_ready`.

The strategy file contains:

- `S54` cross-sectional mean reversion: bar/panel strategy that fades short-term
  relative under/overperformance inside a liquid perpetual universe.
- `S59` reversal after aggressive sweeps: order-flow strategy requiring trades,
  L2 book state, sweep detection, stall confirmation, spread/depth replenishment,
  and impact checks.

User-supplied research cost assumptions for this packet:

- Taker commission per trade: `0.0432%` (`0.000432` decimal).
- Maker commission per trade: `0.0144%` (`0.000144` decimal).
- Constant slippage: `0.2%` (`0.002` decimal), hardcoded as the highest
  expected research slippage assumption after user correction.

## Scope

Allowed paths for this packet:

- `docs/work_packets/WPR106-554-v2-autonomous-readiness-test-strategies.md`
- `docs/KNOWN_ISSUES.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/ACTIVE_INDEX.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `docs/V2_DATA_CATALOG_AND_AGENTIC_RESEARCH_POINTERS.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/contracts/**`
- `README.md`
- `START_HERE.md`
- `configs/strategies/wpr106_554/**`
- `data/research/wpr106_554_autonomous_readiness/**`
- `src/tradingbotsuite/v2/autonomy/**`
- `src/tradingbotsuite/v2/backtest_data/**`
- `src/tradingbotsuite/v2/backtest_engine/**`
- `src/tradingbotsuite/v2/collectors/**`
- `src/tradingbotsuite/v2/strategy_specs/**`
- `src/tradingbotsuite/v2/validation/**`
- `src/tradingbotsuite/v2/research_ledger/**`
- `tests/v2/**`
- `tests/contracts/**`

No-touch paths remain unchanged unless a later work packet explicitly changes
the boundary. This packet must not touch live order placement, runtime mode,
paper/live readiness, sizing, or promotion paths.

## Plan

1. Parse the uploaded strategies into research-only strategy specs or queue
   entries.
2. Confirm whether existing autonomous cycle tooling can execute the strategy
   family with accepted archive/reference data and the required cost model.
3. Fix minor gaps in declarative strategy or autonomous-cycle plumbing if the
   change is local and research-only.
4. If a strategy needs unsupported data semantics, record the blocker instead of
   substituting a weaker strategy.
5. Run the readiness evidence/audit path and baseline validation.
6. If the repository passes the autonomous-readiness contract truthfully, write
   the readiness packet. If not, write exact manual blockers and next fixes.

## Research boundary

- All outputs remain `research_only`, `observe_only`, and
  `promotion_ready: false`.
- Strategy artifacts must not imply paper-ready, live-ready, trade-ready,
  order-ready, sizing-ready, signal-ready, candidate-pack-ready, or
  promotion-ready status.
- Performance claims require reproducible manifests and validation evidence.

## Initial risk notes

- `S54` requires a multi-instrument, point-in-time panel and inverted
  cross-sectional rank semantics: long bottom-ranked underperformers and short
  top-ranked outperformers.
- `S59` requires trade/L2 replay and sweep/replenishment features. If the
  current accepted archive slice does not contain the needed data, it is not an
  autonomous-ready strategy for this packet.
- The autonomous-readiness contract includes clean/pushed baseline evidence.
  Existing unrelated worktree changes must be preserved; readiness cannot be
  truthfully claimed if the baseline remains uncommitted/unpushed.

## Outcome

Implemented and validated the local plumbing needed for the uploaded S54 test:

- `cross_sectional_rank` now supports `rank_direction: reversion`.
- Backtest data requests, manifests, and archive-ref cycle specs now support
  deterministic multi-instrument panels through `instrument_ids`.
- Existing-ref universe/archive checks verify the full requested instrument
  list.
- Archive-cycle cost assumptions now carry the user-supplied model:
  taker `4.32` bps, maker reference `1.44` bps, and constant slippage
  `20` bps.

Generated research-only evidence:

- Accepted S54 spec:
  `configs/strategies/wpr106_554/accepted/s54_cross_sectional_reversion.json`
- Deferred S59 note:
  `configs/strategies/wpr106_554/deferred/s59_aggressive_sweep_reversal.md`
- Jan-Aug 2024 materialized archive:
  `data/research/wpr106_554_autonomous_readiness/materialization_report_2024_01_08.json`
- S54 bounded cycle:
  `data/research/wpr106_554_autonomous_readiness/cycle_s54_cross_reversion_2024_01_08_slip20_accepted_summary.json`

The final 20 bps bounded cycle executed all planned jobs but finished
`completed_with_blockers` with:

- `validation_status_fail`
- `fold_stability_below_min_share`

The backtest run succeeded technically and had `usable_months=6`, but net
return was negative after the supplied `20` bps slippage model:
`net_return=-0.5482526540714943` with `trade_count=6242`. The run manifest's
internal validation status is `pass`, but the post-backtest validation gate is
`fail` because `fold_stability_score=0.0` and no fold is positive. This is not
a minor repo issue; it is a strategy/cost validation blocker.

Earlier WPR106-554 cycle artifacts that used the prior `100` bps slippage
assumption are superseded by the `slip20_accepted` evidence path above.

`S59` remains deferred because it requires accepted trade/L2 replay,
sweep/replenishment features, and queue/fill assumptions. No bar-only proxy was
used.

## Validation

Python 3.11 validation on 2026-06-27:

```text
py -3.11 -m compileall -q src\tradingbotsuite: passed
PYTHONPATH=src; py -3.11 -m pytest tests\v2\test_strategy_specs_phase10.py tests\v2\test_backtest_data_phase9.py tests\v2\test_autopilot_archive_cycle_phase75.py -q: 26 passed, 1 warning
PYTHONPATH=src; py -3.11 -m pytest tests\contracts -q: 463 passed, 1 warning
PYTHONPATH=src; py -3.11 -m pytest tests\v2 -q: 578 passed, 1 warning
PYTHONPATH=src; py -3.11 -m pytest tests -q: 2485 passed, 2 skipped, 6 warnings
git diff --check: passed with existing LF-to-CRLF warnings only
```

Warnings were existing deprecation warnings; no assertion failures or Windows
socket setup failures were observed.
