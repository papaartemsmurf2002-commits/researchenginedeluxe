# HMM Multi-KNN Agent Prompt Pack

Use these prompts when assigning independent agents. Every agent must treat the work as research-only and must use the shared issue protocol.

## Global Instructions For Every Agent

You are working in `c:/Users/papaa/Music/tradingbotsuite`.

Read these files before making decisions:

- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_INPUT_LOOKUP.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_REALIZATION_PLAN.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_MODEL_SPEC.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_RUNBOOK.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_SOURCE_LOG.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md`
- `docs/tradingbotsuite_runtime/source_inputs/tradingbotsuite_critical_audit_orchestrator_next_agent.md`
- `docs/tradingbotsuite_runtime/source_inputs/orchestrator_btc_eth_perps_architecture_review_v3.md`
- `configs/v2_btc_hmm_multi_knn_research.json`

If `docs/tradingbotsuite_runtime/agent_artifacts/` exists, read relevant existing artifacts before starting. These artifacts are the handoff channel between agents and the supervisor.

Hard boundaries:

- Phase 1 is BTC-only.
- ETH is Phase 2; design interfaces, but do not build ETH unless explicitly assigned.
- All work is research-only.
- Do not change live gating, live sizing, Hyperliquid execution behavior, safety behavior, or operator live controls.
- Do not fabricate missing funding, OI, premium, microstructure, or sentiment fields. Preserve explicit missingness.
- Fit scalers, HMMs, KNN pools, feature selectors, and meta-models only on train rows.
- The uploaded critical audits override any optimistic interpretation of the HMM/KNN package: current real BTC evidence is diagnostic, negative, sparse, BTC-only, and not promotable.
- Do not describe the branch as BTC/ETH live-capable. BTC is the only implemented research path; ETH is a Phase 2 design target requiring separate data, labels, artifacts, metrics, and promotion gates.
- Do not claim KNN is the main alpha engine. Treat KNN as a regime-local similarity diagnostic unless out-of-sample costed evidence proves otherwise.
- Prioritize safety, event journals, replayability, point-in-time features, cost-aware labels, and execution boundaries ahead of model tuning.

Critical audit live-safety constraints:

- LIVE risk caps must not be zero or disabled in any future live-readiness work.
- Research jobs must be hard-banned in LIVE, even when there are no open positions.
- HMM/KNN artifacts with `research_only: true` or `observe_only: true` must never be live-promotable.
- Binance-derived signals are not executable prices for Hyperliquid. Future live feasibility must check Hyperliquid basis, spread, depth, funding, book staleness, user-state staleness, open orders, and position reconciliation.
- Hyperliquid execution must eventually be idempotent through deterministic `cloid`, append-only order/fill journals, cancel-by-cloid, reduce-only exits, dead-man cancel, and restart reconciliation before any live automation discussion.
- Root launchers must not bypass canonical CLI/preflight behavior or reconstruct config in a way that drops fields.
- Default webhook secrets such as `change-me` are invalid for LIVE or externally exposed modes.

Minimum evidence floor from the critical audit before model conclusions are meaningful:

- `>= 10000` event rows per asset, or a documented power-analysis exception.
- `>= 1000` rows per HMM regime.
- `>= 300` labeled trades per side per asset.
- `>= 50` accepted trades per validation split.
- `>= 6` walk-forward validation splits.
- Multiple volatility regimes and at least one major stress period.

Artifact communication protocol:

- Every agent must create or update one work artifact for the task under `docs/tradingbotsuite_runtime/agent_artifacts/`.
- Use this filename pattern: `YYYYMMDD_<agent_slug>_<task_slug>.md`.
- The artifact must be written as part of the task, even for read-only review work.
- Treat these files as the handoff channel between agents and the supervisor; read relevant prior artifacts before starting and cite any artifact that influenced your work.
- Include these sections:
  - Agent name
  - Task received
  - Files read
  - Files changed
  - Commands/tests run
  - Decisions made
  - Assumptions
  - Open issues or blockers
  - Handoff notes for other agents
- The model/spec documentation must mention this protocol so artifact readers know where agent-level decisions, commands, and handoff notes live.

Issue protocol:

- If you hit a difficult blocker, high-impact ambiguity, or get lost and cannot efficiently resolve the task, append an issue to `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md`.
- Keep the issue concise and use the issue template in that file.
- If the file contains 4 or more unresolved open issues, stop work and report exactly:

```text
HMM_MULTI_KNN_AGENT_ISSUES.md contains 4 or more unresolved issues. Please provide a clarification markdown file for the collected issues.
```

- Do not continue by guessing once the 4-issue threshold is reached.

Definition of done:

- Code or docs are scoped to your assigned subsystem.
- Tests or validation commands are documented.
- Work artifact is created or updated under `docs/tradingbotsuite_runtime/agent_artifacts/`.
- Research artifacts include `research_only: true` where applicable.
- Existing tracked tests remain green for your touched area.

## Critical Audit Agent Overlay

All agents must keep the following overlay in mind when working from the uploaded audit documents:

| Agent | Added audit responsibility |
| --- | --- |
| Data Agent | Move future work toward Binance USD-M and Hyperliquid append-only journals, not ad hoc exports; distinguish TradingView/export rows as non-promotable. |
| Feature Agent | Prove timestamp availability, avoid silent zero-fill, add availability flags, and ensure WT3D is computed on continuous completed bars before joining to events. |
| Labeling Agent | Replace promotable label assumptions based on signal-bar close with executable-entry modeling; output label intervals for label-window-aware purge/embargo. |
| Regime Agent | Treat HMM as posterior/entropy/dwell-time diagnostics only; do not hardcode state IDs after retrain. |
| KNN Agent | Keep KNN exact, regime-local, out-of-fold/prior-only, and diagnostic; report small pools, low quality, and concentrated neighbors as failures. |
| Meta-Model Agent | Ensure KNN diagnostics used by meta are out-of-fold; compare against logistic/tree baselines and report failure for one-class or tiny samples. |
| Backtest Agent | Enforce purged walk-forward validation with costs, funding, latency, venue-basis assumptions, long/short/regime/horizon reports, and split concentration. |
| Execution And Risk Agent | Own live-readiness blockers, research/live isolation, artifact promotion refusal, venue-basis guard requirements, idempotent execution requirements, and dead-man/reconciliation requirements. |
| Monitoring Agent | Keep monitoring observe-only; track feature outages, regime drift, neighbor quality, funding/cost anomalies, calibration decay, and feed/execution staleness as future readiness risks. |

## Data Agent Prompt

Task: Build or improve point-in-time BTC research data support for HMM-routed KNN.

Context:

- Existing dataset builder: `src/tradingbotsuite/research/dataset.py`
- Existing Binance context client: `src/tradingbotsuite/adapters/binance.py`
- Existing config: `configs/v2_btc_research.json`
- HMM/KNN config: `configs/v2_btc_hmm_multi_knn_research.json`

Responsibilities:

- Ensure BTCUSDT research rows include OHLCV, funding, premium, OI, available microstructure, and existing TradingView signal context.
- Preserve point-in-time alignment.
- Ensure missing exchange context is represented by missingness flags or nulls, never guessed values.
- Keep data raw enough to audit and normalized enough for research consumers.
- Verify the Phase 1 BTC-only guard remains explicit and ETH remains an interface-only Phase 2 concern.
- Verify raw exchange context availability counts are preserved in manifests or handoff artifacts.
- Preserve public dataset manifest fields: `label_outcome_fields`, `missing_feature_rates`, `raw_context_available_counts`, `exchange_context_summary`, and `planned_split_summary`.

Required outputs:

- Dataset or dataset-builder changes if needed.
- Manifest additions if needed, with `research_only: true`, BTC Phase 1 `asset_scope`, and current public dataset hardening fields.
- Tests proving no future timestamps and deterministic dataset builds.
- Work artifact documenting available versus missing historical context fields.

Do not:

- Add live trading behavior.
- Add ETH data in Phase 1.
- Use current-only Binance fields as historical context.

## Feature Agent Prompt

Task: Build robust research features for HMM and KNN.

Context:

- Core features: `src/tradingbotsuite/core/features.py`
- WT3D implementation baseline: `src/tradingbotsuite/research/hmm_knn.py`
- Lookup: `HMM_MULTI_KNN_INPUT_LOOKUP.md`

Responsibilities:

- Add or refine feature construction for return path, volatility, trend/chop, perp structure, microstructure, and WT3D.
- Use robust z-score or train-only scaling for KNN inputs.
- Keep WT3D features completed-bar only.
- Avoid future-pivot divergence features unless the implementation is provably non-leaking.
- Verify public feature names and feature-version changes are reflected in `HMM_MULTI_KNN_MODEL_SPEC.md`.
- If the lookup doc has corrupted source filenames or source aliases, document the cleanup need or fix it if assigned.

Required outputs:

- Versioned feature additions.
- Unit tests for feature determinism and no future leakage.
- Documentation updates in the model spec if new columns are public artifact fields.
- Work artifact listing feature families touched and leakage checks performed.

Do not:

- Fit scalers on validation/test rows.
- Duplicate highly correlated oscillator variants without a reason.

## Regime Agent Prompt

Task: Implement or improve HMM regime routing.

Context:

- Current module: `src/tradingbotsuite/research/hmm_knn.py`
- Config section: `hmm`
- Required outputs: `regime_posteriors.parquet`

Responsibilities:

- Fit Gaussian HMM using `hmmlearn` when the research extra is available.
- Keep deterministic fallback for environments without optional research packages.
- Emit posterior probabilities, entropy, top regime, state labels, recent-flip flag, and no-trade flag.
- Preserve public regime artifact fields: posterior columns, `top_regime`, `top_regime_label`, `max_regime_probability`, `posterior_entropy`, `recent_regime_flip`, `regime_no_trade`, `regime_model_backend`, `walk_forward_split`, `source_row_index`, and `hmm_fit_end_row`.
- Use train-only fitting in every walk-forward split.
- Label states by observed train statistics, not by assuming component IDs are stable.
- Verify online/live-style output is based on forward-only posterior calculations and not future-smoothed Viterbi states.
- Document optional dependency behavior for `hmmlearn` in the work artifact.

Required tests:

- HMM fitting does not use validation/test rows.
- Output does not depend on future-smoothed Viterbi states.
- Uncertain posterior creates no-trade or reduced-confidence records.

Do not:

- Use future-smoothed sequence labels for live-style decisions.
- Force every row into a tradeable state.

## Labeling Agent Prompt

Task: Improve event sampling and triple-barrier label outputs for HMM/KNN research.

Context:

- Existing triple-barrier-compatible logic: `src/tradingbotsuite/research/dataset.py`
- Existing math helpers: `src/tradingbotsuite/core/math.py`
- Config sections: `labels`, `evaluation`

Responsibilities:

- Keep labels path-dependent, not next-bar-only.
- Add or preserve fields for gross return, fees, slippage, funding, MFE, MAE, time in trade, and barrier hit type.
- Support configured horizons `6h`, `24h`, `72h`, and `7d`.
- Respect purge/embargo for overlapping labels.
- Verify purging uses label exit time where available, not only entry timestamp.
- Preserve explicit missingness for unavailable future cost components instead of silently assuming zero unless the config says so.

Required tests:

- Label fields are present in generated research artifacts.
- Fees, slippage, and funding are included in expected value.
- No label information leaks into feature rows.
- Work artifact lists label columns audited and any cost assumptions.

Do not:

- Optimize barrier parameters on the test fold.
- Treat missing future bars as successful labels.

## KNN Agent Prompt

Task: Implement or improve regime-specific Lorentzian KNN predictions.

Context:

- Current module: `src/tradingbotsuite/research/hmm_knn.py`
- Config section: `knn`
- Required outputs: `knn_predictions.parquet`, `neighbor_diagnostics.csv`

Responsibilities:

- Use Lorentzian distance on robust-z features.
- Search same-regime neighbor pools by default.
- Support `k` sweep values from config, with a primary `k`.
- Support inverse-distance and softmax-style weighting.
- Output probabilities, expected net return, neighbor agreement, distance quality, and diagnostics.
- Preserve public KNN diagnostics fields: `k`, `weighting`, `is_primary`, `same_regime_only`, `fallback_used`, `knn_skip_reason`, `source_row_index`, `query_regime`, `neighbor_rank`, `neighbor_source_index`, `neighbor_distance`, `neighbor_distance_quality`, `neighbor_weight`, `neighbor_label_accept`, `neighbor_label_pnl_multiple`, and `neighbor_regime`.
- Verify fallback to compatible regimes is disabled unless explicitly configured.
- Record K sweep settings and selected primary K in the work artifact.

Required tests:

- Distance is deterministic.
- Distance rejects invalid scales.
- Outliers are compressed relative to linear distance.
- Same-regime neighbor search is enforced unless fallback is explicitly configured.
- Neighbor diagnostics are written and include enough detail for later monitoring.

Do not:

- Return direct buy/sell commands.
- Compare shock and trend rows just because oscillator values look similar.

## Meta-Model Agent Prompt

Task: Implement or improve XGBoost meta-filter research.

Context:

- Optional dependency extra: `research`
- Config section: `meta_model`
- Required outputs: `meta_predictions.parquet`, `walk_forward_metrics.json`

Responsibilities:

- Use XGBoost when available.
- Use deterministic fallback only to keep default tests runnable.
- Combine HMM posteriors, KNN outputs, WT3D features, perp features, microstructure, and existing research columns.
- Report the backend used in `meta_predictions.parquet` as `meta_model_backend` and in `artifact_manifest.json` as `dependencies.meta_backend`; also preserve `dependencies.xgboost_available`.
- Compare meta-filter results against pure KNN.
- Verify KNN-derived meta features are out-of-fold or prior-only and cannot see validation/test labels.
- Explicitly report failure modes for tiny samples, one-class labels, or unavailable optional dependencies.

Required tests:

- Meta-model reports improvement or explicit failure.
- Backend used is recorded.
- One split or tiny sample cannot silently pass acceptance.
- Work artifact states whether XGBoost, fallback, or failure path was used.

Do not:

- Hide poor KNN performance by reporting only the meta-model.
- Promote any output to live gating.

## Backtest Agent Prompt

Task: Validate HMM/KNN research artifacts through purged walk-forward metrics.

Context:

- Current metrics: `walk_forward_metrics.json`
- Config section: `evaluation`
- Acceptance section: `acceptance`

Responsibilities:

- Report pure KNN and meta-filter metrics.
- Include fees, slippage, and funding.
- Report long and short counts separately.
- Report split concentration and positive split ratio.
- Keep `promotion_ready: false` and `research_only: true`.
- Own integration validation for the first sweep of HMM/KNN work.
- Run targeted HMM/KNN, research, and operator UI tests when assigned by the supervisor.
- If broader tests are impractical, document exactly which tests were run and why the rest were skipped.

Required tests:

- Metrics are deterministic except runtime latency.
- Promotion failures are explicit.
- No single split can dominate without being flagged.
- `research-hmm-knn`, `replay-hmm-knn`, and `monitor-hmm-knn` command paths remain importable and testable.

Do not:

- Mark research as live-ready.
- Omit low-trade-count failure reasons.

## Execution And Risk Agent Prompt

Task: Review research outputs for future execution feasibility without changing live execution.

Context:

- Live execution is out of scope in Phase 1.
- Current execution stack: `src/tradingbotsuite/adapters/execution.py`, `src/tradingbotsuite/core/engine.py`

Responsibilities:

- Identify future execution constraints for potential Phase 2/3 promotion.
- Document cost, slippage, funding, liquidation, spread, and safety considerations.
- Keep findings in docs or research metrics only.
- Review changed runtime-adjacent files for accidental live behavior changes.
- Confirm whether live execution, sizing, live gates, Hyperliquid behavior, or operator live controls were touched.
- Keep or update `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_EXECUTION_RISK_REVIEW.md` when assigned.

Do not:

- Change order placement.
- Change position sizing.
- Change live accept/reject gates.
- Add automatic execution from HMM/KNN outputs.

## Monitoring Agent Prompt

Task: Define or improve monitoring for HMM/KNN research artifacts.

Context:

- Operator console can display research artifacts, but live behavior must not change.
- Main monitoring fields: drift, entropy, no-trade rate, neighbor quality, funding costs, feature outages.

Responsibilities:

- Propose or implement research-only dashboards/reports.
- Track feature distribution drift and regime distribution drift.
- Track calibration decay and live-vs-replay mismatch only if artifacts exist.
- Alert through docs or observe-only UI states.
- Verify `monitor-hmm-knn` writes an observe-only `monitoring_report.json` when assigned.
- Verify operator UI summaries display HMM/KNN research artifacts without creating live controls.
- Ensure monitoring output remains `observe_only: true`, `promotion_ready: false`, and `research_only: true`.

Do not:

- Trigger live trading state changes.
- Auto-retrain into production.
