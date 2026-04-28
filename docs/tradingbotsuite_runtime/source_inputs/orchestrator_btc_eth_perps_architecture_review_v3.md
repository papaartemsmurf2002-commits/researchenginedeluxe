# Orchestrator Brief v3: BTC/ETH Perp Automated Trading Architecture Review

**Date:** 2026-04-28
**Role:** Advisor / advanced evaluator / critical architecture curator
**Target:** fully automated BTC/ETH perpetual futures system
**Signal data source:** Binance USD-M futures, with identical historical/replay schema where possible
**Execution venue:** Hyperliquid perpetuals
**Holding window:** minimum 1 hour, maximum roughly 1 week
**Primary research thread:** HMM-derived regimes + multi-KNN / Lorentzian-distance KNN + WT3D-derived features
**Core objective:** real, production-survivable edge; not a pile of clever indicators.

---

## 0. Truth status: GitHub access and audit boundary

The user states that GitHub was connected as an app. That should be the right access path. However, in this chat session the accessible tool surface did **not** expose a GitHub repository connector or file-search connector that can enumerate the repo. Public/unauthenticated routes also failed.

### 0.1 Access attempts made

```text
Repo requested:
  https://github.com/papaartemsmurf2002-commits/tradingbotsuite/tree/main

Container attempt:
  git clone --no-single-branch https://github.com/papaartemsmurf2002-commits/tradingbotsuite.git /mnt/data/tradingbotsuite
  result: Could not resolve host: github.com

Web/browser attempt:
  open GitHub tree URL
  result: UnexpectedStatusCode / failed fetch

Search attempts:
  site:github.com/papaartemsmurf2002-commits/tradingbotsuite tradingbotsuite
  github papaartemsmurf2002-commits tradingbotsuite branches
  papaartemsmurf2002-commits tradingbotsuite
  result: no usable indexed repo content

GitHub API direct URL attempt:
  https://api.github.com/repos/papaartemsmurf2002-commits/tradingbotsuite/branches
  result: blocked by browser safety rule because URL was not surfaced as a prior result

Personal context check:
  confirms GitHub app connection exists at account/environment-note level;
  does not expose branch list, commits, file contents, or repository blobs.
```

### 0.2 Audit boundary

**Verified branch/file findings from the repo: none.**

This document therefore remains an **orchestrator-ready architecture review and audit runbook**, not a completed branch-by-branch code audit. No agent should claim that `main`, feature branches, execution code, model code, or tests were inspected until the GitHub connector is actually usable inside the agent environment or the repository is provided as a clone/bundle/zip.

### 0.3 Required GitHub-App recovery procedure

The orchestrator should use the connected GitHub App directly. The GitHub REST branch endpoint is compatible with GitHub App user/installation tokens when the token has repository **Contents: read** permission. The orchestrator must prove access before making repo-specific claims.

Required first proof:

```bash
# With a GitHub App installation/user token available to the orchestrator.
# Do not print the token.
OWNER="papaartemsmurf2002-commits"
REPO="tradingbotsuite"

curl -fsSL \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "X-GitHub-Api-Version: 2026-03-10" \
  "https://api.github.com/repos/$OWNER/$REPO" \
  > audit_out/repo_meta.json

curl -fsSL \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "X-GitHub-Api-Version: 2026-03-10" \
  "https://api.github.com/repos/$OWNER/$REPO/branches?per_page=100" \
  > audit_out/branches.json
```

If the orchestrator cannot obtain `repo_meta.json` and `branches.json`, the repo is not accessible and no code audit should proceed.

---

## 1. Executive verdict

The architecture should **not** converge toward a single KNN, WaveTrend, WT3D, or Lorentzian-classifier strategy. The production architecture with the best chance of surviving BTC/ETH perpetuals is:

```text
Binance USD-M data backbone
→ immutable event log and replay
→ feature store with timestamp/availability guarantees
→ HMM / regime posterior router
→ strategy-candidate layer
→ regime-local KNN similarity diagnostics where useful
→ perp microstructure and cross-asset feature stack
→ calibrated meta-decision layer
→ state-aware exits
→ risk governor
→ Hyperliquid execution adapter
→ reconciliation, monitoring, drift, and TCA
```

The probable edge is **regime-conditioned market structure plus strict execution/risk discipline**, not KNN alone.

Priority ranking:

1. **P0:** data correctness, replay, CUSUM/triple-barrier labels, fee/slippage/funding model, purged walk-forward validation.
2. **P0:** Binance perp microstructure features: funding, OI, premium/basis, taker imbalance, book imbalance, liquidation snapshots, volatility expansion/compression.
3. **P0:** Hyperliquid execution safety: venue-basis guards, BBO/book checks, client order IDs, reduce-only exits, dead-man cancel, state reconciliation.
4. **P1:** HMM router using posterior probabilities, entropy, and dwell-time gates.
5. **P1:** Lorentzian KNN as regime-local diagnostic/feature generator.
6. **P1:** WT3D as a feature family for pullbacks/exhaustion, not as a standalone trading rule.
7. **P2:** news/sentiment, on-chain, deep sequence models, or RL only after the core system is stable.

---

## 2. Non-negotiable architecture principles

### 2.1 Event-driven, not indicator-driven

Every live decision must be reproducible from a historical event log. If a strategy cannot be replayed exactly, it is not production-ready.

Required objects:

```text
MarketEvent
TradeEvent
BookEvent
FundingEvent
OpenInterestEvent
LiquidationEvent
BarEvent
FeatureVector
RegimeState
SignalCandidate
TradeDecision
OrderIntent
OrderAck
FillEvent
PositionState
RiskState
ExitDecision
```

### 2.2 Binance signal is not Hyperliquid execution

Signal generation is Binance-driven, but execution is Hyperliquid. Therefore, every trade must pass both:

```text
Signal validity on Binance-derived state
Execution feasibility on Hyperliquid book/state
```

Mandatory cross-venue fields:

```text
binance_mid
hyperliquid_mid
venue_basis_bps = 10_000 * (hyperliquid_mid - binance_mid) / binance_mid
venue_basis_z
hyperliquid_spread_bps
hyperliquid_depth_10bps_usd
hyperliquid_depth_25bps_usd
execution_feasibility_score
```

Reject entries when:

```text
abs(venue_basis_z) > threshold
HL spread exceeds symbol threshold
required order size > 25% of depth available within 10 bps
Hyperliquid user/order stream is stale
Binance signal feed has sequence gaps or stale OI/funding
```

### 2.3 Research and live trading must be separated

Suggested repository layout:

```text
/research          notebooks, experiments, ablations
/src/data          collectors, normalizers, replay
/src/features      feature generation only
/src/labels        CUSUM/triple-barrier/event labels
/src/models        HMM, KNN, meta-models, calibrators
/src/strategy      decision policies, candidate routing
/src/execution     Hyperliquid adapter and order state machine
/src/risk          exposure, drawdown, kill-switches
/src/backtest      replay engine and cost model
/src/monitoring    logs, metrics, alerts, drift
/config            versioned strategy/risk/model configs
/tests             unit, integration, replay regression
```

No live order placement may occur outside `/src/execution` and `/src/risk`.

---

## 3. Branch audit instructions for the orchestrator

The orchestrator must produce file/line evidence. Do not accept summaries like “branch X has HMM work” without citations to files and commits.

### 3.1 Branch inventory via GitHub App

```bash
mkdir -p audit_out/branches audit_out/trees audit_out/blobs audit_out/grep
OWNER="papaartemsmurf2002-commits"
REPO="tradingbotsuite"

python - <<'PY'
import json, os, pathlib, urllib.request

owner = os.environ.get("OWNER", "papaartemsmurf2002-commits")
repo = os.environ.get("REPO", "tradingbotsuite")
token = os.environ["GITHUB_TOKEN"]
base = f"https://api.github.com/repos/{owner}/{repo}"
headers = {
    "Accept": "application/vnd.github+json",
    "Authorization": f"Bearer {token}",
    "X-GitHub-Api-Version": "2026-03-10",
}

def get(url):
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())

out = pathlib.Path("audit_out")
out.mkdir(exist_ok=True)
branches = get(f"{base}/branches?per_page=100")
(out / "branches.json").write_text(json.dumps(branches, indent=2), encoding="utf-8")

rows = []
for b in branches:
    name = b["name"]
    sha = b["commit"]["sha"]
    rows.append(f'{name},{sha},{b.get("protected", False)}')
(out / "branch_inventory.csv").write_text("branch,sha,protected\n" + "\n".join(rows), encoding="utf-8")
print(f"branches={len(branches)}")
PY
```

### 3.2 Local full clone path

If the orchestrator can clone with GitHub App/token, use a mirror clone:

```bash
mkdir -p audit_out
GIT_ASKPASS=/path/to/nonprinting_askpass.sh \
  git clone --mirror https://github.com/papaartemsmurf2002-commits/tradingbotsuite.git tradingbotsuite.mirror.git
cd tradingbotsuite.mirror.git

git for-each-ref --format='%(refname:short),%(objectname),%(committerdate:iso8601),%(authorname),%(subject)' refs/heads \
  | sort > ../audit_out/branch_inventory.csv

for b in $(git for-each-ref --format='%(refname:short)' refs/heads); do
  safe=$(echo "$b" | sed 's#[/:]#_#g')
  git ls-tree -r --name-only "$b" > "../audit_out/files_${safe}.txt"
  git show --stat --oneline --decorate --no-renames "$b" -1 > "../audit_out/last_commit_${safe}.txt"
  git grep -n -I -E 'api[_-]?key|secret|private[_-]?key|wallet|mnemonic|seed|hyperliquid|binance|order\(|cancel|leverage|live|real[-_ ]?trade|reduceOnly|scheduleCancel|funding|openInterest|forceOrder|websocket|knn|lorentz|hmm|regime|wavetrend|wt3d|xgboost|lightgbm|triple|barrier|cusum|backtest|slippage|fee|risk|kill' "$b" \
    > "../audit_out/grep_${safe}.txt" || true
done
```

### 3.3 Branch matrix schema

Create `branch_matrix.csv` with:

```text
branch_name
last_commit_sha
last_commit_date
author
purpose_guess
modules_touched
data_pipeline_changes
model_changes
execution_changes
risk_changes
tests_added
config_changes
secrets_risk
live_trading_risk
merge_status
recommended_action: keep/merge/archive/rewrite/delete
file_line_evidence
notes
```

### 3.4 Critical repo questions

The audit must answer:

```text
1. Is there one canonical event schema?
2. Is Binance data collection separated from Hyperliquid execution?
3. Does backtest use the same feature code as live?
4. Are features timestamped by availability, not by candle close convenience?
5. Are labels path-dependent and cost-aware?
6. Is there a real position reconciliation loop?
7. Are secrets excluded from code, configs, notebooks, and logs?
8. Does every order intent pass through risk checks?
9. Can the system recover from Binance/Hyperliquid websocket disconnects?
10. Can the strategy be disabled while data collection continues?
```

---

## 4. Production target architecture

```text
                          ┌──────────────────────────────┐
                          │        Config Registry        │
                          │ strategy/risk/model versions  │
                          └──────────────┬───────────────┘
                                         │
┌────────────────────┐       ┌───────────▼───────────┐       ┌─────────────────────┐
│ Binance Data Feed  │──────▶│ Event Normalizer       │──────▶│ Immutable Event Log │
│ trades/depth/mark  │       │ timestamps/symbols     │       │ parquet/db/kafka    │
│ funding/OI/liq     │       │ sequence checks        │       │                     │
└────────────────────┘       └───────────┬───────────┘       └──────────┬──────────┘
                                         │                              │
                                         ▼                              ▼
                              ┌───────────────────┐          ┌───────────────────┐
                              │ Bar/Event Builder │          │ Replay Engine      │
                              │ 1h/4h/CUSUM bars  │          │ exact simulation   │
                              └─────────┬─────────┘          └─────────┬─────────┘
                                        │                              │
                                        ▼                              ▼
                              ┌───────────────────┐          ┌───────────────────┐
                              │ Feature Store      │◀────────▶│ Research Harness   │
                              │ versioned features │          │ labels/backtests   │
                              └─────────┬─────────┘          └───────────────────┘
                                        │
                                        ▼
                              ┌───────────────────┐
                              │ Regime Engine      │
                              │ HMM posterior      │
                              │ entropy/dwell      │
                              └─────────┬─────────┘
                                        │
                     ┌──────────────────┼──────────────────┐
                     ▼                  ▼                  ▼
          ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
          │ KNN Similarity   │ │ Perp OFI Model  │ │ WT3D Features   │
          │ regime-local     │ │ XGB/LightGBM    │ │ pullback/exhaust│
          └────────┬────────┘ └────────┬────────┘ └────────┬────────┘
                   └──────────────────┬┴──────────────────┘
                                      ▼
                           ┌──────────────────────┐
                           │ Meta Decision Layer   │
                           │ trade/no-trade/size   │
                           │ calibrated EV         │
                           └──────────┬───────────┘
                                      ▼
                           ┌──────────────────────┐
                           │ Exit + Risk Governor  │
                           │ barriers/stops/limits │
                           └──────────┬───────────┘
                                      ▼
                           ┌──────────────────────┐
                           │ Hyperliquid Adapter   │
                           │ cloid/order/fill sync │
                           └──────────┬───────────┘
                                      ▼
                           ┌──────────────────────┐
                           │ Monitoring + TCA      │
                           │ drift/pnl/latency     │
                           └──────────────────────┘
```

---

## 5. Data design

### 5.1 Binance live feed requirements

Minimum Binance USD-M sources for BTCUSDT and ETHUSDT:

```text
aggTrade / trade stream
bookTicker stream
depth stream
kline streams: 1m, 5m, 15m, 1h, 4h
mark price stream @1s where available
forceOrder / liquidation snapshots
funding rate history and current premium/mark
open interest via REST polling
taker buy/sell volume or taker imbalance
long/short ratio endpoints as slow context only
```

Important implementation notes:

```text
- aggTrade is useful for taker-flow and trade-intensity features.
- markPrice contains mark/funding context; do not confuse mark with executable price.
- kline streams are useful for slow features but should not be the only source for research labels.
- open interest is REST/polled or vendor-normalized; do not pretend it is a native high-frequency websocket stream.
- liquidation streams can be throttled/snapshot-like; treat them as incomplete pressure proxies, not complete liquidation truth.
```

### 5.2 Hyperliquid live state requirements

Even when Binance is the signal source, the execution layer must consume Hyperliquid:

```text
l2Book / BBO / allMids
trades if needed for execution analytics
user order updates
user fills
user funding
clearinghouse/position state
open orders
account equity and margin
```

### 5.3 Event quality flags

Every feature row must carry quality flags:

```text
missing_depth
book_sequence_gap
funding_missing
open_interest_stale
liquidation_stream_stale
binance_ws_lag_ms
hyperliquid_ws_lag_ms
cross_venue_basis_abnormal
bar_builder_late
feature_nan_count
```

A live signal is invalid when core quality flags are unhealthy.

---

## 6. HMM regime engine

### 6.1 Purpose

The HMM is a **router and risk context model**, not a direct alpha model. It answers:

```text
What kind of market are we in?
Which strategy families are allowed?
How much size is allowed?
Which exits should dominate?
Should KNN be trusted or ignored?
```

### 6.2 Starting regimes

| Regime | Semantic name | Typical condition | Allowed behavior |
|---|---|---|---|
| R0 | Low-vol chop/range | weak trend, low realized vol, mean reversion | small mean-reversion, 6h/24h |
| R1 | Bull continuation | positive drift, supportive OI/flow | pullback longs, breakout continuation |
| R2 | Bear continuation | negative drift, downside impulse | failed-bounce shorts, continuation shorts |
| R3 | Shock/transition | vol-of-vol spike, liquidation, depth stress | mostly no-trade; reduce risk |

### 6.3 HMM feature set

Use a low-dimensional, robust set:

```text
returns_1h_z
returns_4h_z
returns_24h_z
realized_vol_4h_z
realized_vol_24h_z
atr_pct_z
vol_of_vol_z
ema_slope_24h_z
adx_or_trend_strength_z
choppiness_z
funding_rate_z
premium_or_basis_z
open_interest_delta_4h_z
taker_buy_imbalance_1h_z
liquidation_pressure_z
ethbtc_relative_return_z    # ETH model
btc_regime_proxy            # ETH model
```

### 6.4 Implementation spec

```text
Model: GaussianHMM or GMMHMM
States: compare 3, 4, 5; start with 4
Covariance: diagonal first; full only if stable
Feature scaling: rolling robust z-score from training window only
Winsorization: clip to [-5, 5]
Training cadence: daily/weekly offline retrain
Online use: posterior inference only
Outputs: posterior probabilities, entropy, top regime, dwell bars
```

Do not hardcode state ID semantics after retrain. Store a semantic mapping artifact:

```yaml
regime_model_version: hmm_btc_v003
state_semantics:
  state_0: low_vol_chop
  state_1: bull_continuation
  state_2: bear_continuation
  state_3: shock_transition
assignment_rule:
  - rank by mean return
  - rank by realized volatility
  - inspect funding/OI/liquidation stats
```

### 6.5 HMM gates

```text
normal size: max_posterior >= 0.60 and entropy below threshold
full size: max_posterior >= 0.75 and dwell confirmed
skip: entropy spike, too many flips, shock posterior high
```

---

## 7. Multi-KNN design

### 7.1 Correct role

KNN should answer:

```text
Inside this regime, have similar states historically led to upper barrier, lower barrier, or timeout?
```

KNN should not directly answer:

```text
Should we buy now?
```

KNN output should be a diagnostic vector:

```text
p_upper_barrier
p_lower_barrier
expected_net_return_bps
neighbor_agreement
mean_neighbor_distance
distance_percentile
sample_count
regime_consistency
horizon_consistency
```

### 7.2 Model grid

Train separate memories by:

```text
symbol: BTC, ETH
regime: range, bull, bear, shock
horizon: 6h, 24h, 72h, 168h
strategy_family: trend, pullback, mean_reversion, squeeze_reversal
```

Example models:

```text
knn_btc_range_reversion_6h
knn_btc_bull_pullback_24h
knn_btc_bear_continuation_24h
knn_eth_btclead_continuation_24h
knn_eth_range_reversion_6h
knn_eth_shock_reversal_6h
```

### 7.3 Distance metrics

Primary candidate:

```text
Weighted Lorentzian distance:
D(x, y) = Σ_i w_i * log(1 + |x_i - y_i|)
```

Compare against:

```text
Manhattan on robust z-score
Euclidean on robust z-score
cosine distance for directional vectors
Mahalanobis inside stable regimes only
```

Do not assume Lorentzian wins. It must win or add value in purged OOS tests.

### 7.4 KNN preprocessing

```text
compute only from data available at decision timestamp
rolling robust z-score using training window only
winsorize to [-5, 5]
missing values become explicit missing flags, not silent zeros
remove highly duplicated/collinear features
keep final KNN dimensions around 8-20
```

If the candidate feature set is 50-100 dimensions, KNN is probably the wrong final model. Use KNN diagnostics plus tree/meta-model instead.

### 7.5 KNN skip conditions

```text
sample_count < min_samples_by_regime
mean_neighbor_distance > distance_cutoff
neighbor_agreement < agreement_cutoff
expected_net_return_bps <= cost_adjusted_threshold
regime entropy too high
feature quality flags unhealthy
```

---

## 8. Feature sets to test

### 8.1 Perp microstructure core

Highest-priority candidate outside KNN.

```text
funding_rate
funding_rate_z_7d
funding_rate_z_30d
premium_index_z
basis_to_mark_z
open_interest_delta_1h
open_interest_delta_4h
open_interest_delta_24h
price_change_with_oi_change quadrant
volume_z
trade_count_z
taker_buy_volume_ratio
taker_buy_imbalance_z
book_imbalance_top_5
book_imbalance_top_25
spread_bps
depth_10bps_usd
depth_slope
liquidation_long_usd_z
liquidation_short_usd_z
liquidation_imbalance
```

Interpretation matrix:

| Pattern | Interpretation | Candidate action |
|---|---|---|
| Price up + OI up + taker buy positive + funding not extreme | trend participation | continuation long in bull regime |
| Price up + OI down | short squeeze / de-risking | continuation only if volume confirms |
| Price down + OI up + funding positive | trapped longs | bearish continuation or avoid longs |
| Positive funding extreme + long liquidations rising | crowded long unwind risk | reduce longs / short only if regime agrees |
| Negative funding + OI flush + stabilization | short crowding | long reversal candidate after confirmation |

### 8.2 WT3D feature family

Use WT3D as feature engineering, not a signal by itself.

```text
wt3d_fast
wt3d_normal
wt3d_slow
wt3d_fast_slope
wt3d_normal_slope
wt3d_slow_slope
wt3d_fast_accel
wt3d_normal_accel
fast_minus_normal
normal_minus_slow
all_speeds_aligned_flag
cross_direction
bars_since_fast_normal_cross
bars_since_normal_slow_cross
reversal_zone_intensity
regular_bullish_divergence_flag
regular_bearish_divergence_flag
hidden_bullish_divergence_flag
hidden_bearish_divergence_flag
kernel_signal_slope
mtf_agreement_score
```

Valid uses:

| Use case | Regime | Confirmation |
|---|---|---|
| Trend continuation | bull/bear | WT3D slow aligned + OI/volume confirmation |
| Pullback entry | bull/bear | fast oscillator mean-reverts while slow remains aligned |
| Range reversion | chop | reversal zone + low trend strength + VWAP stretch |
| Shock reversal | shock | divergence + liquidation/OI flush + basis normalization |

Invalid uses:

```text
WT3D cross alone
WT3D divergence alone
WT3D overbought/oversold alone
```

### 8.3 BTC-to-ETH spillover features

ETH should not be modeled as a standalone copy of BTC. ETH gets a dedicated BTC-lead model:

```text
btc_return_15m_1h_4h
btc_realized_vol_1h_4h
btc_regime_posterior
btc_funding_z
btc_oi_delta
btc_taker_imbalance
eth_return_minus_btc_return
ethbtc_return_1h_4h_24h
ethbtc_vwap_z
eth_beta_to_btc_rolling
eth_residual_return_z
eth_funding_minus_btc_funding
eth_oi_delta_minus_btc_oi_delta
```

### 8.4 Volatility compression/expansion

```text
realized_vol_1h_4h_24h
atr_pct
bollinger_bandwidth
keltner_channel_width
squeeze_flag
range_compression_duration
breakout_distance_from_range
volume_expansion_z
vol_of_vol
trend_strength_after_compression
```

Trade breakouts only when compression resolves with volume/OI confirmation.

### 8.5 Mean-reversion/range

```text
vwap_distance_z
session_vwap_distance_z
bollinger_z
rsi_z
wt3d_reversal_intensity
low_adx_flag
choppiness_index
funding_extreme_against_position
liquidation_exhaustion
book_imbalance_against_move
```

Use only in chop/range regimes, not trend regimes.

### 8.6 Shock/no-trade model

This may be more valuable than another alpha model.

```text
vol_of_vol_z
liquidation_pressure_z
book_spread_jump
depth_collapse
venue_basis_spike
funding_dislocation
price_gap_bps
regime_entropy_spike
ws_lag_or_data_quality_flags
```

Output:

```text
no_trade_probability
force_reduce_probability
safe_to_place_limit_orders
safe_to_hold
```

---

## 9. Candidate strategy stacks

### S1: HMM-routed Lorentzian KNN baseline

```text
HMM posterior
+ regime-local Lorentzian KNN
+ triple-barrier labels
→ p_upper, p_lower, EV, neighbor diagnostics
```

Use as explainable baseline. Promote only if OOS positive after costs and not dependent on one historical episode.

### S2: HMM + KNN diagnostics + LightGBM/XGBoost meta-filter

```text
HMM posterior
+ KNN p/EV/distance/agreement
+ perp features
+ WT3D features
+ cross-asset features
→ calibrated meta-model
→ trade/no-trade/size bucket
```

This is the most practical first production model.

### S3: Perp microstructure model

```text
funding/OI/taker/book/liquidation/volatility
+ HMM posterior
+ triple-barrier label
→ LightGBM/XGBoost/logistic baseline
```

This may beat KNN. It must be tested even if KNN research continues.

### S4: ETH BTC-lead model

```text
BTC regime + BTC impulse + BTC perp state
+ ETH/BTC residual
+ ETH perp state
→ ETH trade/no-trade
```

### S5: Regime-conditioned WT3D pullback

```text
HMM bull/bear posterior high
+ WT3D slow aligned
+ WT3D fast pullback/recovery
+ OI/volume confirmation
→ continuation entry
```

### S6: Shock no-trade / forced reduce model

```text
vol-of-vol + liquidation + depth collapse + cross-venue basis + HMM entropy
→ no trade / reduce / only IOC exits
```

Build this before live automation.

---

## 10. Labeling, validation, and exits

### 10.1 Event sampling

Use both:

```text
Time bars: 1h, 4h, 1d for slow features and HMM inference
CUSUM/event bars: model samples and labels
```

Label horizons:

```text
6h
24h
72h
168h
```

### 10.2 Triple-barrier labels

Every candidate entry gets:

```text
upper barrier: volatility/ATR adjusted
lower barrier: volatility/ATR adjusted
time barrier: 6h/24h/72h/168h
cost model: Hyperliquid fee + expected spread/slippage + funding accrual
```

Store:

```text
upper_hit
lower_hit
timeout
net_return_bps_after_fee_slippage_funding
holding_time_minutes
max_adverse_excursion_bps
max_favorable_excursion_bps
barrier_type
label_interval_start
label_interval_end
```

### 10.3 Live exit stack

```text
hard stop / lower barrier
take-profit / upper barrier
time stop
HMM posterior flip against position
HMM entropy spike / shock regime
funding cost exceeds expected EV
venue basis or HL liquidity abnormal
WT3D/kernel invalidation if WT3D stack triggered entry
reduce-only emergency exit on risk limit breach
```

### 10.4 Exit candidates

| Exit model | Priority | Use |
|---|---:|---|
| Static triple barrier | P0 | baseline label/live exit |
| Regime-adaptive triple barrier | P0 | production default |
| Volatility trailing stop | P1 | trend continuation |
| Hazard/survival model | P1 | exit timing without RL complexity |
| Meta-exit classifier | P1 | hold/reduce/exit based on state decay |
| RL exit policy | P3 | defer until deterministic exits work |

---

## 11. Backtest acceptance criteria

Use purged walk-forward validation with embargo at least equal to the maximum label horizon plus buffer.

Minimum protocol:

```text
train window: 12-24 months
validation window: 1-3 months
test window: rolling 1-3 months
embargo: max label horizon + safety buffer
purge: all overlapping labels
```

Required costs:

```text
Hyperliquid maker/taker fees
spread cost
slippage floor
market impact based on HL depth when available
funding paid/received
failed fill / partial fill simulation
latency delay
venue-basis mismatch between Binance signal and HL execution
```

Promote only if:

```text
positive OOS expectancy after all costs
positive/flat performance in at least 70% of test windows
no single month contributes >35% of OOS PnL
BTC and ETH reported separately
long and short reported separately
PnL by regime reported
probabilities calibrated or conservatively thresholded
no-trade model reduces tail loss/drawdown
replay engine deterministically reproduces decisions
```

Reject if:

```text
accuracy high but net PnL negative
edge disappears after funding/slippage
edge exists only in one bull period
feature importance dominated by leakage-prone variables
KNN neighbors mostly from one episode
HMM state IDs drift after retrain
signals fire during data-quality degradation
backtest fills at Binance mid while live executes on Hyperliquid
risk module logs warnings but cannot block orders
```

---

## 12. Hyperliquid execution requirements

The adapter must support:

```text
place_limit_order
place_market_or_ioc_order
place_trigger_stop_loss
place_trigger_take_profit
cancel_by_order_id
cancel_by_cloid
modify_order
schedule_cancel_deadman
fetch_open_orders
fetch_position_state
subscribe_order_updates
subscribe_user_fills
subscribe_user_funding
reconcile_state
```

Use deterministic client order IDs:

```text
cloid = hash(strategy_id + symbol + side + decision_ts + intent_seq)
```

Default order policy:

```text
Entry when urgency low: ALO/post-only limit
Entry when EV high and signal decays: IOC with strict slippage cap
Entry when execution feasibility low: no trade
Profit target: reduce-only trigger/take-profit when supported
Stop loss: reduce-only trigger stop
Emergency: reduce-only IOC
```

Dead-man cancel:

```text
Schedule cancel during active trading.
Refresh it periodically.
Cancel stale non-reduce orders on process shutdown.
Do not exceed daily trigger limits.
```

Reconciliation loop:

```text
local intended position
Hyperliquid actual position
open orders
pending trigger orders
last fills
funding payments
account equity/margin
```

If local and remote disagree:

```text
stop new entries
cancel non-reduce orders
fetch full state
reconstruct position from fills
resume only when reconciled
```

---

## 13. Agent responsibilities

### 13.1 Repo auditor agent

```text
Fetch all branches through GitHub App.
Build branch matrix.
Identify duplicate architecture attempts.
Classify production code vs experiments.
Search for direct order placement, secrets, model leakage, and broken backtests.
Produce merge/kill/archive plan with file-line evidence.
```

Outputs:

```text
branch_matrix.csv
repo_audit_report.md
merge_plan.md
risk_surface_map.md
secrets_scan_report.md
```

### 13.2 Data agent

```text
Connect to Binance market streams.
Poll REST-only OI/funding where needed.
Connect to Hyperliquid execution/market state streams.
Normalize timestamps and symbols.
Write immutable events.
Expose replay.
Set quality flags.
```

### 13.3 Feature agent

```text
Build versioned features from event log.
Guarantee availability timestamps.
Maintain robust scalers per train window.
Produce HMM, KNN, WT3D, perp, and cross-asset features.
Prevent future leakage.
```

### 13.4 Labeling agent

```text
Build CUSUM events.
Generate triple-barrier labels for 6h/24h/72h/168h.
Include fees, slippage, funding, and time-in-trade.
Output intervals for purging.
```

### 13.5 Regime agent

```text
Train HMM/GMMHMM.
Assign semantic regime labels.
Output posterior, entropy, dwell.
Track regime drift over retrains.
```

### 13.6 KNN agent

```text
Build regime/horizon memories.
Run exact Lorentzian baseline first.
Output neighbor probabilities and diagnostics.
Reject low-quality neighbor sets.
Ablate KNN on/off in meta-model.
```

### 13.7 Meta-model agent

```text
Train logistic/LightGBM/XGBoost baselines.
Compare with and without KNN diagnostics.
Calibrate probabilities.
Output trade/no-trade/size bucket.
Generate model card.
```

### 13.8 Backtest agent

```text
Run purged walk-forward validation.
Simulate costs, slippage, funding, latency, partial fills.
Report by symbol/regime/side/horizon.
Run ablations.
```

### 13.9 Execution agent

```text
Convert TradeDecision to Hyperliquid orders.
Enforce risk.
Place/cancel/modify.
Reconcile fills and positions.
Maintain dead-man cancel.
```

### 13.10 Monitoring agent

```text
Track data health.
Track model drift.
Track live-vs-backtest decay.
Track PnL attribution.
Alert on risk breaches.
Produce daily TCA.
```

---

## 14. What to kill or quarantine in the repo

Kill/quarantine if found:

```text
live order placement outside execution adapter
Binance price used as executable Hyperliquid fill
next-bar labels presented as production alpha
features without timestamp/availability proof
indicator-only strategies without costs and purged OOS tests
HMM state IDs hardcoded after retrain
KNN on raw unscaled features
KNN with too many dimensions and no ablation
backtest ignoring funding
risk module that cannot block orders
secrets in repo/config/notebooks/logs
notebook dependencies in live runtime
live strategy code with no kill switch
```

---

## 15. Production roadmap

### Phase 0: Repo access and audit

Deliver:

```text
repo_meta.json
branches.json
branch_matrix.csv
repo_audit_report.md
risk_surface_map.md
merge_plan.md
```

Exit:

```text
branch-specific claims have file/line evidence
one canonical architecture branch chosen
all live-risk code identified
```

### Phase 1: Data/replay foundation

Deliver:

```text
Binance event recorder
Hyperliquid state recorder
immutable event log
bar/event builder
feature timestamp tests
replay engine v0
```

### Phase 2: Labels and baseline models

Deliver:

```text
CUSUM sampler
triple-barrier labels
cost model
logistic/LightGBM baseline
baseline rules
```

### Phase 3: HMM router

Deliver:

```text
HMM training pipeline
semantic state mapper
posterior/entropy output
regime performance report
```

### Phase 4: KNN diagnostics

Deliver:

```text
regime-local KNN memories
exact Lorentzian KNN
neighbor diagnostics
KNN ablation report
```

### Phase 5: Meta-model and exits

Deliver:

```text
calibrated meta-decision model
regime-adaptive triple-barrier exits
hazard/meta-exit experiment
```

### Phase 6: Paper trading

Deliver:

```text
Hyperliquid paper/testnet or shadow mode
order reconciliation
TCA reports
live data-quality dashboard
```

### Phase 7: Canary live

Deliver:

```text
small-size live config
hard kill-switch
daily review report
capital escalation policy
```

---

## 16. Minimum viable production config

```yaml
symbols:
  - BTC
  - ETH
holding_horizons:
  - 6h
  - 24h
  - 72h
max_holding_time_hours: 168
risk:
  max_gross_leverage: 1.0
  max_symbol_leverage: 0.75
  max_daily_loss_pct: 1.0
  max_weekly_loss_pct: 2.5
  max_concurrent_positions: 2
  max_new_entries_per_day: 6
  kill_on_position_mismatch: true
  kill_on_data_stale_seconds: 30
execution:
  venue: hyperliquid
  default_entry_order: ALO_limit
  emergency_exit_order: reduce_only_IOC
  use_deadman_cancel: true
  max_entry_slippage_bps:
    BTC: 4
    ETH: 6
  max_spread_bps:
    BTC: 3
    ETH: 5
regime:
  min_posterior_normal_size: 0.60
  min_posterior_full_size: 0.75
  no_trade_on_entropy_spike: true
knn:
  enabled: true
  exact_first: true
  min_neighbors: 24
  max_neighbors: 64
  min_agreement: 0.58
  require_positive_ev_after_costs: true
meta_model:
  require_calibrated_probability: true
  min_expected_net_return_bps: 12
```

Numbers are placeholders and must be recalibrated by backtest and paper trading.

---

## 17. Decision ledger

| Decision | Verdict | Reason |
|---|---|---|
| Binance-driven signals | Accept | User constraint; Binance has rich USD-M data |
| Hyperliquid execution | Accept | User constraint; needs separate execution state |
| HMM regimes | Accept | Best used as router/risk context |
| Lorentzian KNN | Accept as candidate | Explainable local memory; not core brain until proven |
| WT3D | Accept as features only | Useful momentum/exhaustion descriptors; not edge proof |
| Gradient-boosted meta-model | Accept | Better final decision layer than pure KNN |
| RL full policy | Reject for initial production | Too much complexity before deterministic system works |
| News/sentiment | Defer | Possible value, but data/latency/reliability complications |

---

## 18. Final advisor conclusion

The probable real edge is not a single Lorentzian KNN or a single WT3D variant. The strongest architecture is:

```text
clean Binance perp data
+ event/replay correctness
+ CUSUM/triple-barrier labels
+ HMM regime posterior routing
+ perp microstructure and BTC→ETH spillover features
+ local KNN diagnostics
+ WT3D pullback/exhaustion descriptors
+ calibrated meta-decision model
+ state-aware exits
+ Hyperliquid execution/risk discipline
```

KNN should stay in the research program, but it should be demoted from “main alpha engine” to “regime-local similarity diagnostic” until it proves OOS contribution after costs.

The orchestrator’s immediate path is:

```text
GitHub-App repo audit
→ freeze live-risk surfaces
→ normalize architecture
→ data/replay correctness
→ labels/costs
→ HMM router
→ baseline meta-model
→ KNN/WT3D ablations
→ execution safety
→ paper trading
→ canary live
```

Do not add more indicators before proving data/replay/label/execution correctness.

---

## 19. Source log

### GitHub access

- GitHub REST branch endpoint / GitHub App token requirements: https://docs.github.com/rest/branches/branches

### Binance / data infrastructure

- Binance futures connector websocket client: https://github.com/binance/binance-futures-connector-python/blob/main/binance/websocket/um_futures/websocket_client.py
- Binance futures connector market-data file: https://github.com/binance/binance-futures-connector-python/blob/main/binance/um_futures/market.py
- Binance USD-M futures API/skills endpoint list: https://www.binance.com/en/skills/detail/binance/derivatives-trading-usds-futures
- Tardis Binance futures historical data details: https://docs.tardis.dev/historical-data-details/binance-futures

### Hyperliquid

- Hyperliquid websocket docs: https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/websocket
- Hyperliquid exchange endpoint: https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/exchange-endpoint
- Hyperliquid websocket subscriptions: https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/websocket/subscriptions

### Research

- Algorithmic crypto trading using information-driven bars, triple-barrier labeling and deep learning: https://link.springer.com/article/10.1186/s40854-025-00866-w
- Order flow and cryptocurrency returns: https://www.sciencedirect.com/science/article/pii/S1386418126000029
- Bitcoin price regime shifts with Bayesian MCMC and HMM: https://www.mdpi.com/2227-7390/13/10/1577
- Lorentzian distance metric in classification: https://www.sciencedirect.com/science/article/pii/S0167865516302392
- Robust distance measures for KNN classification: https://pmc.ncbi.nlm.nih.gov/articles/PMC7573750/
- Predictability of crypto returns from trading behavior: https://www.sciencedirect.com/science/article/pii/S2214635023000266

### Indicator / implementation inspiration

- TradingView Lorentzian classification: https://www.tradingview.com/script/WhBzgfDu-Machine-Learning-Lorentzian-Classification/
- TradingView WaveTrend 3D: https://www.tradingview.com/script/clUzC70G-WaveTrend-3D/
