# Stage R106 Lorentzian KNN Temporal Stability Refresh Report

Date: 2026-06-11
Work packet: `docs/work_packets/WPR106-92-lorentzian-knn-temporal-stability-refresh.md`
Owner: Codex Research Agent

## Decision

WPR106-92 is closed as a pre-May Lorentzian/KNN temporal-stability refresh.
The packet broadened the WPR106-86 KNN search rather than defending the
rejected BTC sparse side-veto lead, added a scoped archive-backed microdrift
feature pack, and ran BTCUSDT/ETHUSDT KNN matrices over the 2024-01 through
2026-04 source datasets.

May 2026 was not used for tuning, selection, ranking, generated rows, or label
endpoints. One ETHUSDT pre-May row is benchmark-worthy under the loose
month-stability rule, but the May 2026 benchmark was not run because
`ISSUE-R106-025` still records that the local May 2026 archive is unavailable.

No candidate pack, paper/live artifact, order placement, sizing change,
runtime-mode change, live configuration write, CUDA speedup claim, or
promotion-ready claim exists.

## Scope

- Source data: WPR106-85 no-RSI four-bar BTCUSDT/ETHUSDT datasets built from
  local Binance Vision archives for 2024-01 through 2026-04.
- Evaluation rows: walk-forward OOS predictions from 2025-05-25 23:00:00 UTC
  through 2026-04-30 19:00:00 UTC, with label end max
  2026-04-30 23:00:00 UTC.
- May 2026 usage: none; benchmark blocked by `ISSUE-R106-025`.
- Feature change: added `price_microdrift_flow_no_context` to the HMM/KNN
  feature-pack registry. The pack keeps completed-bar short path returns,
  slope/efficiency/volatility, wick/range compression, and observed aggTrade
  flow/impact columns while excluding unavailable book/perp context.
- Search scope: 8 BTCUSDT and 8 ETHUSDT experiments, each summarized for the
  primary KNN decision and meta-model decision.
- Active-rate policy: retain and score 1 to 5 trades per active day when cost,
  split, monthly, and concentration evidence is recorded.
- Compute: `run-hmm-knn-experiments` with 3 workers per symbol. CuPy/XGBoost
  warnings were observed, but no CUDA speedup was measured or claimed.

## Artifacts

- BTCUSDT config:
  `configs/research/wpr106_92_lorentzian_knn_temporal_stability_btcusdt_v1.json`
- ETHUSDT config:
  `configs/research/wpr106_92_lorentzian_knn_temporal_stability_ethusdt_v1.json`
- BTCUSDT matrix:
  `data/research/wpr106_92_lorentzian_knn_temporal_stability/btcusdt/experiment_manifest.json`
- ETHUSDT matrix:
  `data/research/wpr106_92_lorentzian_knn_temporal_stability/ethusdt/experiment_manifest.json`
- Relocated artifact cache:
  `data/research/wpr106_92_lorentzian_knn_temporal_stability/cache/`
- Summary JSON:
  `data/research/wpr106_92_lorentzian_knn_temporal_stability/summary/wpr106_92_knn_temporal_stability_summary.json`
- Strategy summary CSV:
  `data/research/wpr106_92_lorentzian_knn_temporal_stability/summary/wpr106_92_knn_temporal_stability_summary.csv`
- Monthly returns CSV:
  `data/research/wpr106_92_lorentzian_knn_temporal_stability/summary/wpr106_92_knn_temporal_monthly_returns.csv`

BTC runtime was 796.274592 seconds with 3 effective workers. ETH runtime was
801.31704 seconds with 3 effective workers. The initial cache path was relative
and was relocated under the packet data root; matrix summaries and artifact
manifests were rewritten and checked for resolvable artifact paths.

## Results

Summary across 16 experiments and 32 KNN/meta strategy rows:

| Metric | Value |
| --- | ---: |
| Strategy rows | 32 |
| Positive net/expectancy rows | 3 |
| Rows inside 1 to 5 trades per active day | 32 |
| Loose monthly-stability rows | 1 |
| Strict monthly-stability rows | 0 |
| Pre-May rows requiring May benchmark | 1 |
| Rows with May 2026 signal rows | 0 |
| Rows with May 2026 label-end rows | 0 |

By symbol and strategy:

| Symbol | Strategy | Rows | Positive rows | Loose hits | Strict hits | Holdout-needed rows |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| BTCUSDT | KNN | 8 | 0 | 0 | 0 | 0 |
| BTCUSDT | Meta | 8 | 2 | 0 | 0 | 0 |
| ETHUSDT | KNN | 8 | 0 | 0 | 0 | 0 |
| ETHUSDT | Meta | 8 | 1 | 1 | 0 | 1 |

Top rows:

| Symbol | Row | Strategy | Trades | Net after costs | Expectancy | Trades/active day | Active months | Positive months | Losing months | Decision |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| ETHUSDT | `eth-1h-4h-wick-flow-lorentzian-compatible-lower-meta` | Meta | 564 | +0.069117 | +0.000123 | 2.452 | 10 | 5 | 5 | benchmark blocked |
| BTCUSDT | `btc-1h-4h-microdrift-lorentzian-same-fallback-softmax-open` | Meta | 78 | +0.094839 | +0.001216 | 1.625 | 4 | 3 | 1 | rejected: sparse and split-dominant |
| BTCUSDT | `btc-1h-4h-microdrift-euclidean-same-fallback-inverse-balanced` | Meta | 34 | +0.011084 | +0.000326 | 1.214 | 4 | 3 | 1 | rejected: sparse and split-dominant |

The ETHUSDT loose row has 564 meta trades, 230 active days, 2.452 trades per
active day, 10 active months, 5 positive months, 5 losing months, 2 flat months,
profit factor 1.023903, max positive-month profit share 0.335295, and max
single split PnL share 0.366382. It is not a strict hit because the positive
month rate is only 5 of 12 OOS months, but it is the first WPR106 KNN row in
this branch to satisfy the packet's loose pre-May holdout-candidate rule.

The BTCUSDT positive meta rows remain rejected. They are profitable on aggregate
but active in only 4 months, have high monthly concentration, and have max
single split PnL share of 1.0.

## May 2026 Holdout

May 2026 remains untouched by WPR106-92. The ETHUSDT loose row should be the
first benchmark target after a scoped May 2026 archive intake/cache-refresh
packet resolves `ISSUE-R106-025`. The benchmark must not feed back into tuning,
ranking, feature selection, or parameter changes.

Until that archive dependency is resolved, this packet cannot complete the
requested May 2026 benchmark despite having one pre-May candidate.

## Validation

Passed:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_hmm_knn.py -q
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Results:

- HMM/KNN focused suite: 49 passed, with the existing CuPy CUDA-path and
  XGBoost mismatched-device warnings.
- Compileall: passed.
- Contracts: 454 passed.
