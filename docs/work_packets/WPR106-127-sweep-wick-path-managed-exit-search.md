# WPR106-127 Sweep Wick Path-Managed Exit Search

Date: 2026-06-11
Owner: Codex Research Agent
Status: closed

## Objective

Test whether the WPR106-126 liquidity-sweep and wick-failure signals fail
because fixed 15m-bar holds are too crude. The packet reuses only pre-May
WPR106-126 source evidence, then applies path-managed exits with conservative
same-bar ambiguity handling.

Optimization, source selection, exit parameter choice, ranking, and selection
use only 2024-01-01 through 2026-04-30. May 2026 remains fully out of tuning
and is replayed only as a benchmark holdout after fixed pre-May strict or
loose rows exist.

## Allowed Paths

- `docs/work_packets/WPR106-127-sweep-wick-path-managed-exit-search.md`
- `docs/stage_reports/STAGE_R106_SWEEP_WICK_PATH_MANAGED_EXIT_SEARCH_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_127_sweep_wick_path_managed_exit_search/**`

## Inputs

- `data/research/wpr106_126_liquidity_sweep_wick_failure_search/pre_may/sweep_wick_ranking.parquet`
- `data/research/wpr106_126_liquidity_sweep_wick_failure_search/pre_may/selected_pre_may.parquet`
- `data/research/wpr106_126_liquidity_sweep_wick_failure_search/scripts/run_wpr106_126_liquidity_sweep_wick_failure_search.py`
- WPR106-96 BTCUSDT/ETHUSDT 2024-01 through 2026-05 bar and aggTrade-flow context loaded through the WPR106-126 feature builder.

## Boundaries

- Research-only, observe-only, promotion-ready false.
- No candidate pack, paper/live artifact, order placement, sizing change,
  runtime-mode change, or live configuration write.
- May 2026 must not influence source-row choice, exit-parameter choice,
  ranking, selection, or cost assumptions.
- Same-bar TP/SL ambiguity must be handled conservatively and documented.
- CUDA may be claimed only if a real CUDA path is executed and validated; the
  expected path is CPU vectorized/precomputed signal replay with no speedup
  claim.
- If a blocking correctness risk is found, update `docs/KNOWN_ISSUES.md`.

## Evidence Plan

1. Build a deterministic pre-May-only source pool from WPR106-126 selected
   loose rows, positive annual-target diagnostics, active positive rows, and
   top positive rows. Do not read WPR106-126 May benchmark artifacts for source
   selection.
2. Recompute each source signal causally from completed 15m bars and WPR106-126
   score/filter logic.
3. Evaluate path-managed exits with next-bar entry, no overlapping active
   position per source/overlay, stop-loss, take-profit, time-stop, optional
   break-even behavior, optional trailing stop, taker/slippage costs, monthly
   stability, drawdown, Sortino, best-month concentration, and cost stress.
4. Select strict rows first, loose rows only if strict is empty. If neither
   exists, do not benchmark May.
5. Replay May 2026 only for fixed selected overlays and report it separately as
   benchmark-only evidence.

## Validation

Run focused script compile, then the branch baseline:

```powershell
python -m compileall -q data/research/wpr106_127_sweep_wick_path_managed_exit_search/scripts
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

Completed validation:

- `python -m compileall -q data/research/wpr106_127_sweep_wick_path_managed_exit_search/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` -> 460 passed

## Closeout

The packet is rejected as candidate-ready evidence. The run selected a
deterministic pre-May-only source pool of 96 WPR106-126 rows: 10 WPR106-126
loose selected rows, 42 positive annual-target diagnostics, and 44 active
positive rows. It evaluated 18,432 path-managed overlays across max holds,
take-profit, stop-loss, break-even, and trailing settings.

The path exits improved pre-May screen breadth, with 4,025 positive rows,
2,585 positive annual-target rows, 116 loose rows, and 0 strict rows. The
annual-target rows remained too sparse, maxing at 20 trades and 14 active
months. The loose rows were active enough at 68 to 318 trades and 21 to 28
active months, but none met annual stability caps; they carried 6 to 8 losing
months.

May 2026 was benchmark-only after fixed pre-May selection. It rejected the 116
selected loose overlays with 1 May-positive row and 115 May-negative rows. Best
May return was +0.007162, worst was -0.024864, and median was -0.013164. No
candidate pack, paper/live artifact, order/sizing/runtime change, live
configuration write, CUDA speedup claim, or promotion claim was made.
