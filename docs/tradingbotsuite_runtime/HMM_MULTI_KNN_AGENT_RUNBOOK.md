# HMM Multi-KNN Agent Runbook

This runbook maps the production matrix into implementation agents. Each agent writes research artifacts only.

Primary references:

- `HMM_MULTI_KNN_INPUT_LOOKUP.md` preserves the user-provided research inputs and workbook matrix in repo form.
- `HMM_MULTI_KNN_AGENT_PROMPTS.md` contains copy-ready prompts for independent implementation agents.
- `HMM_MULTI_KNN_AGENT_ISSUES.md` is the shared clarification queue. If it reaches 4 unresolved issues, agents must stop and report that the issue file contains 4 or more unresolved issues.

## Data Agent

- Inputs: BTCUSDT OHLCV, funding, premium, OI, aggTrade flow, book/depth context, and existing TradingView research signals.
- Outputs: point-in-time aligned dataset rows and missingness report.
- Guards:
  - no future timestamps
  - finalized funding only
  - degraded exchange endpoints become missingness flags
  - raw and normalized paths remain auditable

## Feature Agent

- Inputs: cleaned dataset rows and existing `src/tradingbotsuite/core/features.py` outputs.
- Outputs: robust-z feature matrix with versioned feature columns.
- Required feature blocks:
  - return/trend/chop
  - realized volatility and volatility shock
  - funding, basis, OI, premium
  - taker flow, queue imbalance, spread
  - WT3D fast/normal/slow and derivatives
  - session/funding-window context
- Guards:
  - scalers fit on train rows only
  - derivative features are clipped or winsorized
  - completed bars only for MTF alignment

## Regime Agent

- Inputs: train-only emission features.
- Outputs: posterior probabilities, entropy, top regime, state labels, no-trade flags.
- Phase 1 states:
  - range/chop
  - bull trend
  - bear trend
  - shock/transition
- Guards:
  - no future-smoothed Viterbi state in live-style output
  - no trade when `p_top < 0.60`
  - no trade when entropy exceeds threshold
  - no trade or reduced confidence after rapid state flips

## Labeling Agent

- Inputs: event samples, bars, costs, funding, and current triple-barrier labels.
- Outputs: path-dependent labels and trade outcome fields.
- Required output fields:
  - `gross_return`
  - `fees_bps`
  - `slippage_bps`
  - `funding_paid_or_received`
  - `time_in_trade`
  - `max_adverse_excursion`
  - `max_favorable_excursion`
  - `barrier_hit_type`
- Guards:
  - overlapping labels are purged in walk-forward evaluation
  - label horizons stay in `6h`, `24h`, `72h`, and `7d`
  - fees, slippage, and funding are never omitted from expected value

## KNN Agent

- Inputs: train-only scaled feature matrix, labels, and regime posteriors.
- Outputs: regime-specific Lorentzian KNN predictions and neighbor diagnostics.
- Required outputs:
  - `p_up_barrier`
  - `p_down_barrier`
  - `expected_net_return_after_costs`
  - `neighbor_agreement`
  - `neighbor_distance_quality`
  - neighbor ranks, weights, distances, labels, and regimes
- Guards:
  - same-regime neighbors only unless explicit fallback is configured
  - minimum neighbor count enforced
  - outlier compression validated through Lorentzian distance tests

## Meta-Model Agent

- Inputs: KNN outputs, HMM posteriors, WT3D features, perp features, and existing research features.
- Outputs: meta probability and research-only accepted flag.
- First backend: XGBoost.
- Fallback backend: random forest for default environments without the research extra.
- Guards:
  - report backend used in artifact manifest
  - compare against pure KNN
  - reject improvements from tiny samples or one split

## Backtest Agent

- Inputs: KNN/meta signals, labels, costs, and walk-forward splits.
- Outputs: `walk_forward_metrics.json`.
- Required reports:
  - trade count
  - expectancy after cost
  - profit factor
  - long and short counts
  - split summaries
  - no-trade rate
  - split concentration
- Guards:
  - promotion remains false
  - metrics include `research_only: true`
  - repo-wide pytest uses `--import-mode=importlib` from `pyproject.toml` so duplicate test module basenames collect deterministically
  - mid-development full-suite validation command is `$env:PYTHONPATH='src'; python -m pytest -q`, with the latest readiness scorecard recording `383 passed in 146.44s`
  - targeted HMM/KNN, research, and operator UI validation is green at `56 passed in 21.74s`
  - CLI/E2E fixture validation runs `research-hmm-knn` followed by `monitor-hmm-knn` through `python -m tradingbotsuite.main`, uses synthetic BTC data under `tmp_path`, verifies expected artifacts, and writes no repo data artifacts

## Execution And Risk Agent

No Phase 1 live execution work is allowed.

The only valid Phase 1 output is a research artifact. Any future live use requires a separate approval pass after BTC and ETH validation.

Final live-boundary invariant:

- HMM/KNN research, replay, monitoring, metrics, and UI summaries are observe-only.
- Do not route HMM/KNN artifact fields into live accept/reject gates, position sizing, Hyperliquid order placement, safety state, runtime-mode switching, or operator live controls.
- The readiness scorecard is mid-development research-contract validation only; it is not a positive expectancy or live-readiness claim.

## Monitoring Agent

- Track feature drift, regime distribution drift, posterior entropy, no-trade rate, neighbor distance quality, and live-vs-replay decay.
- Alert when research data quality degrades, but do not change live behavior.
- Run `monitor-hmm-knn --manifest <artifact_manifest.json>` against generated artifacts to write observe-only `monitoring_report.json`.
- Artifact smoke validation confirmed `monitoring_report.json` preserves `research_only: true`, `observe_only: true`, and `promotion_ready: false`.
