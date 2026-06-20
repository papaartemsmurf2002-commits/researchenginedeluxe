# WPR106-116 Walk-Forward Lorentzian KNN Feature Search

Date: 2026-06-11
Owner: Codex Research Agent
Status: closed

## Goal

Run a fresh artifact-only Lorentzian/KNN search over the verified WPR106-96
BTCUSDT/ETHUSDT 15m feature context, using alternative feature packs,
neighbor aggregation, filters, horizons, and active-rate controls from the
previous KNN packets. The objective is to test whether a causal walk-forward
local-analog model can produce active, month-stable 2024-forward leads before
May 2026 is inspected.

## Scope

- Use WPR106-96 verified BTCUSDT and ETHUSDT feature frames covering
  2024-01 through 2026-05.
- Build labels from future 15m OHLC/close paths inside the runner, with
  completed-bar features and next-bar entries.
- Use only 2024-01-01 through 2026-04-30 for feature-pack choice, label
  horizon choice, lookback, neighbor count, train spacing, distance metric,
  score threshold, side mode, session/regime filter, active-rate control,
  ranking, and selection.
- Keep May 2026 fully out of all tuning and use it only as a benchmark
  holdout after fixed pre-May rows are selected.
- Test Lorentzian distance as the primary local-analog metric, with Euclidean
  controls where cheap enough.
- Use causal neighbor pools only: for a query row, every neighbor label must
  have completed before the query signal time.
- Explore feature packs with explicit logic:
  - price-path and volatility state;
  - wick/range path shape derived from OHLC;
  - trend plus pullback state;
  - price plus aggTrade-flow proxy;
  - ETH-only available flow-context variants when provider-backed columns
    exist.
- Allow active entry rates around 1 to 5 trades/day after thresholding, with
  one-position overlap, max trades/day caps, explicit costs, drawdown, monthly
  stability, and cost stress measured.
- Use vectorized/cached per-feature matrices and staged search to keep the
  experiment tractable. CUDA is out of scope for this packet unless a real
  backend is validated and truthfully reported.
- Keep all artifacts research-only, observe-only, and promotion-ready false.

## Allowed paths

- `docs/work_packets/WPR106-116-walk-forward-lorentzian-knn-feature-search.md`
- `docs/stage_reports/STAGE_R106_WALK_FORWARD_LORENTZIAN_KNN_FEATURE_SEARCH_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_116*/**`

## Out of scope

- No May 2026 tuning, source feedback, feature feedback, threshold feedback,
  filter feedback, horizon feedback, neighbor feedback, rank feedback, or cost
  feedback.
- No shared `src/tradingbotsuite` code, package registry, feature registry,
  strategy registry, backtest engine, optimizer, research-cycle, candidate-pack,
  live, runtime, config, or test changes.
- No candidate pack, paper/live artifact, order placement, position sizing,
  live runtime change, live configuration write, CUDA speedup claim, or
  promotion claim.
- No synthetic fallback data.

## Exit evidence

- A deterministic WPR106-116 runner and artifacts are written under
  `data/research/wpr106_116*/`.
- Pre-May ranking, selected rows, daily/monthly returns, trade rows, KNN
  parameter metadata, rolling block metrics, and cost-stress diagnostics are
  written separately from May benchmark artifacts.
- May 2026 benchmark artifacts are written only for fixed pre-May-selected
  rows.
- The stage report records whether any row satisfies the target of roughly
  zero to two losing months per full pre-May year, whether active 1 to 5
  trades/day candidates survive costs and overlap, and whether May confirms or
  rejects fixed pre-May selection.
- Validation baseline is run or explicitly reported if blocked:
  `python -m compileall -q src/tradingbotsuite` and
  `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`.

## Closeout

Closed 2026-06-11. The deterministic artifact-only runner was written under
`data/research/wpr106_116_walk_forward_lorentzian_knn_feature_search/scripts/`
and generated pre-May plus May benchmark artifacts under
`data/research/wpr106_116_walk_forward_lorentzian_knn_feature_search/`.

The sweep evaluated 41,472 walk-forward Lorentzian KNN feature/filter/side/
horizon rows over WPR106-96 BTCUSDT and ETHUSDT 15m feature frames. Every
feature-pack, horizon, lookback, neighbor-count, threshold, side, session,
regime, active-rate, ranking, and selection decision used only 2024-01-01
through 2026-04-30. May 2026 was benchmark-only after fixed pre-May selection.

Results:

- Positive pre-May rows: 4,219.
- Loose pre-May rows: 231.
- Strict pre-May rows: 0.
- Positive annual-target rows with no more than 2/2/1 losing months in
  2024/2025/2026 Jan-Apr: 63.
- Annual-target rows with at least 40 trades and 10 active months: 32.
- Those annual-target active-ish rows are still blocked: all 32 have fewer
  than 20 active months, 29 have fewer than 80 trades, and 14 have best-month
  concentration above 0.45.
- Selected rows: 80 loose rows across 21 symbol/feature-pack/horizon groups.
- May benchmark after fixed pre-May selection: 6 May-positive rows,
  15 May-negative rows, and 59 May-flat rows.

The top selected pre-May row is `wfknn-dd0a460e7ba2426e`, a BTCUSDT
price-path/volatility Lorentzian row with 960-bar lookback, 31 neighbors,
32-bar horizon, long-only Asia trend filter, and one trade/day cap. It returns
+0.323736 pre-May after costs with 45 trades, 17 active months, 6 losing
months, annual losses of 2024: 3, 2025: 3, and 2026 Jan-Apr: 0, max drawdown
-0.018922, full cost-stress survival, and no losing rolling blocks. It has
0 May trades.

The strongest annual-target active-ish row is `wfknn-bead0446e2412fcb`, an
ETHUSDT trend-pullback-state row with 2,880-bar lookback, 31 neighbors, and
32-bar horizon. It returns +0.304182 pre-May with 86 trades, 18 active months,
5 losing months, annual losses of 2024: 2, 2025: 2, and 2026 Jan-Apr: 1, but
fails the active-month floor. The two selected annual-target rows have
60 trades and 17 active months and record no May trades.

Best selected May return is +0.008076 from ETHUSDT trend-pullback-state rows,
but those rows have only one May trade and fail pre-May annual stability with
9 losing months. Worst selected May return is -0.033921. The large May-flat
count is caused by fixed selected filters producing no May entries, not by
positive confirmation.

Conclusion: the novel artifact-only Lorentzian KNN feature/filter search finds
more plausible annual-stability diagnostics than WPR106-115, but no strict
active, month-stable lead. No candidate pack, paper/live artifact,
order/sizing/runtime change, live config write, CUDA speedup claim, or
promotion claim exists.

Validation passed:

```powershell
python -m compileall -q data/research/wpr106_116_walk_forward_lorentzian_knn_feature_search/scripts
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

Contracts reported 460 passed.
