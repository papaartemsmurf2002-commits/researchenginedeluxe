# WPR106-152 Level-Source KNN Trade Filter Search

Date: 2026-06-12
Owner: Codex Research Agent
Status: closed

## Objective

Test a scoped Lorentzian/KNN variant without returning to the rejected
WPR106-146 sparse side-veto lineage. This packet uses WPR106-151 level/retest
rows as source strategies and applies causal trade-quality KNN filters with
new level-aware feature packs.

The purpose is to check whether WPR106-151's broad loose/annual diagnostics can
be converted into month-stable, active rows by learning from earlier completed
source trades only. The target remains month-to-month stability, not one large
profitable window.

## Allowed Paths

- `docs/work_packets/WPR106-152-level-knn-trade-filter-search.md`
- `docs/stage_reports/STAGE_R106_LEVEL_SOURCE_KNN_TRADE_FILTER_SEARCH_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_152_level_knn_trade_filter_search/**`

## Inputs

- `data/research/wpr106_151_causal_multiday_level_retest_search/**`
- `data/research/wpr106_96_may_2026_portfolio_holdout_benchmark/source_context/**`

May 2026 may be loaded only after fixed pre-May KNN-filter survivors are
selected. No May data may influence source-pool choice, KNN features,
normalization, distance metric, lookback, thresholds, ranking, or selection.

## Boundaries

- Research-only, observe-only, promotion-ready false.
- No candidate pack, paper/live artifact, order placement, sizing change,
  runtime-mode change, live configuration write, or promotion claim.
- Use 2024-01-01 through 2026-04-30 for every tuning and selection decision.
- Use May 2026 only as benchmark holdout if fixed pre-May survivors exist.
- KNN history is causal: pre-May trades can use only earlier source trades
  whose exits completed before the current signal; May uses frozen pre-May
  source history only.
- This packet is artifact-only and does not change shared strategy, feature,
  KNN, backtest, live, or candidate-pack code.
- CUDA is not expected; report CPU/vectorized/cached execution truthfully.
- If a blocking correctness risk is found, update `docs/KNOWN_ISSUES.md`.

## Evidence Plan

1. Select a diverse WPR106-151 source pool using only pre-May ranking evidence:
   strict/loose rows, active annual-target diagnostics, and high-return active
   rows, then de-duplicate by candidate id.
2. Replay fixed WPR106-151 source candidates over pre-May and May with WPR106-151
   accounting, seeding May loss-throttle state from pre-May monthly returns.
3. Build level-aware KNN feature packs from completed signal bars:
   - short path plus flow and WPR106-151 score strength;
   - regime/range/chop plus level score context;
   - level reaction features using source score, flow alignment, and trend
     alignment.
4. Test Lorentzian and Euclidean distance, multiple lookbacks/neighborhoods,
   same-side versus all-side history, neighbor-return thresholds, win-rate
   thresholds, and daily caps of 1, 3, and 5.
5. Require strict or loose pre-May monthly stability before any May replay.
6. Replay May 2026 only for fixed pre-May survivors with frozen pre-May KNN
   history.
7. Record whether this level-source KNN filter is rejected or whether it
   produces a research-only follow-up lead.

## Validation

Run focused script compile, then the branch baseline:

```powershell
python -m compileall -q data/research/wpr106_152_level_knn_trade_filter_search/scripts
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

## Evidence Results

- WPR106-151 source candidate rows considered: 160.
- Source universe rows replayed: 160.
- Behavior-deduped source-pool rows with at least 60 pre-May trades: 94.
- Source-pool pre-May trades: 14,495.
- Source-pool May trades: 203.
- KNN overlay rows evaluated: 274,104.
- Positive pre-May rows: 252,394.
- Positive annual-target rows: 69,210.
- Loose pre-May rows: 16,568.
- Strict pre-May rows: 0.
- Selected rows: 100 loose rows.
- May benchmark: 0 positive rows, 100 negative rows, 0 flat rows.
- Best selected May return: -0.002536.
- Worst selected May return: -0.030063.
- Median selected May return: -0.016714.

The selected loose rows were concentrated in five ETHUSDT prior-day
breakout-follow source rows. The top selected row used `path_level`,
Lorentzian distance, 96-trade lookback, 5 neighbors, all-side history, minimum
neighbor mean -0.00010, minimum neighbor win rate 0.48, and max 1 accepted
trade/day. It had 85 pre-May trades, 25 active months, 4 losing months, annual
losses 2024: 1, 2025: 2, 2026 Jan-Apr: 1, +0.877616 pre-May net return,
-0.132155 max drawdown, 0.185848 best-month share, and 4/4 cost-stress
survival, but May lost -0.017933.

## Closeout

WPR106-152 rejects the level-source KNN trade filter as candidate-ready or as a
new promising lead. The KNN variants were effective at manufacturing many
positive and loose pre-May rows, but no strict row survived, selection was
source-concentrated, and the fixed May 2026 benchmark was unanimously negative.

The result is useful because it tests a scoped Lorentzian/KNN feature and
parameter variant on WPR106-151's level/retest family rather than on the old
side-veto lineage. It also shows that adding level-aware score/flow/regime KNN
filters does not rescue the WPR106-151 prior-day breakout/retest diagnostics.

No candidate pack, paper/live artifact, order/sizing/runtime change, live
configuration write, CUDA speedup claim, or promotion claim exists.

Validation passed:

```powershell
python -m compileall -q data/research/wpr106_152_level_knn_trade_filter_search/scripts
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

Contracts result: 460 passed.
