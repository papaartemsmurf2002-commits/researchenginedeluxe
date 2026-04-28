# Execution Risk Next Experiment Boundary Review

## Agent name

Execution and Risk Agent

## Task received

Review the proposed experiment matrix. Classify each experiment as docs/config only, offline research run, data regeneration, or forbidden live-impacting. Reject or flag any experiment requiring live execution, live sizing, live gates, Hyperliquid behavior, or operator live controls. Run:

```powershell
git diff --name-only
rg -n "Hyperliquid|live|execution|sizing|operator live|Control page|runtime" docs/tradingbotsuite_runtime/agent_artifacts
```

Write this artifact.

## Files read

- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_regime_agent_next_experiment_spec.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_monitoring_agent_next_experiment_thresholds.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_meta_model_agent_next_experiment_spec.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_data_agent_next_dataset_regeneration_spec.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_backtest_agent_phase1_research_status_memo.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_regime_agent_architecture_gap_review.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_meta_model_agent_architecture_gap_review.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_monitoring_agent_architecture_gap_review.md`

## Files changed

- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_execution_risk_next_experiment_boundary_review.md`

## Commands/tests run

```powershell
git diff --name-only
```

Result:

```text
<no tracked diff output before writing this artifact>
```

```powershell
rg -n "Hyperliquid|live|execution|sizing|operator live|Control page|runtime" docs/tradingbotsuite_runtime/agent_artifacts
```

Result summary:

- Many prior artifacts repeat the live-boundary rule.
- The relevant next-experiment specs explicitly keep experiments research-only and out of live execution, sizing, gates, Hyperliquid behavior, safety behavior, and operator live controls.
- Monitoring thresholds are described as observe-only experiment-monitoring requirements, not live gates.
- Dataset regeneration spec explicitly says no live data fetch is authorized and current-only websocket state must not be used for historical rows.

Additional lookup:

```powershell
rg -n "experiment|matrix|next experiment|proposed|sweep|real-data|real data|runbook|readiness|candidate" docs/tradingbotsuite_runtime/agent_artifacts docs/tradingbotsuite_runtime
```

Used to identify the proposed experiment matrix artifacts.

## Experiment boundary classification

| Experiment | Source artifact | Classification | Boundary decision |
| --- | --- | --- | --- |
| Flip-cooldown sensitivity grid over `hmm.flip_cooldown_bars` | `20260428_regime_agent_next_experiment_spec.md` | Offline research run | Allowed if run via cloned research configs and local BTC dataset/output dirs only. Does not require live execution or live controls. |
| Entropy threshold sensitivity over `hmm.entropy_threshold` | `20260428_regime_agent_next_experiment_spec.md` | Offline research run | Allowed as research-only config sweep. Must not feed live gates. |
| Posterior threshold sensitivity over `hmm.posterior_threshold` | `20260428_regime_agent_next_experiment_spec.md` | Offline research run | Allowed as research-only config sweep. Must report diagnostic rates only. |
| HMM emission feature subset ablation | `20260428_regime_agent_next_experiment_spec.md` | Offline research run | Allowed as research-only config sweep. Moving fields between HMM/KNN/meta must remain research config/code only. |
| Longer training history / walk-forward split sensitivity | `20260428_regime_agent_next_experiment_spec.md` | Offline research run | Allowed as research-only config sweep. Must preserve train-only fitting and local artifact output. |
| Monitoring red/yellow/green thresholds for no-trade, flip, neighbor quality, feature outages, calibration, regime drift | `20260428_monitoring_agent_next_experiment_thresholds.md` | Docs/config only | Allowed as observe-only experiment-monitoring requirements. Must not be wired into live gates, sizing, execution, safe mode, retraining, or operator live controls. |
| Lower meta threshold diagnostic ladder | `20260428_meta_model_agent_next_experiment_spec.md` | Offline research run | Allowed only as diagnostic research output. Any regime-veto bypass must be reported as diagnostic-only and must not change official `accepted_by_meta` or live behavior. |
| XGBoost research-extra backend comparison | `20260428_meta_model_agent_next_experiment_spec.md` | Offline research run | Allowed in a research environment with optional deps. Must compare against fallback using same local dataset/splits and remain `promotion_ready: false`. |
| Pure KNN-only baseline comparison and candidate expansion matrix | `20260428_meta_model_agent_next_experiment_spec.md` | Offline research run | Allowed as research-only baseline. Must report poor KNN behavior rather than hide it behind meta. |
| Meta trained only after expanded KNN candidate generation | `20260428_meta_model_agent_next_experiment_spec.md` | Offline research run | Allowed if implemented in research code/config only. Must preserve no-leakage rules and decomposed candidate/regime/meta counts. |
| Regenerate real BTC dataset with latest hardened label/context manifest | `20260428_data_agent_next_dataset_regeneration_spec.md`, `20260428_backtest_agent_phase1_research_status_memo.md` | Data regeneration | Allowed only as local/offline or explicitly authorized historical data regeneration. This task does not authorize live data fetches. Current-only websocket state is forbidden for old rows. |
| Increase historical coverage and review per-regime neighbor pool depth | `20260428_backtest_agent_phase1_research_status_memo.md` | Data regeneration / offline research run | Allowed if based on local regenerated dataset or explicitly authorized historical extraction. Forbidden if it uses live/current-only data to backfill historical rows. |
| Run with research extra dependencies so XGBoost and hmmlearn availability can be evaluated | `20260428_backtest_agent_phase1_research_status_memo.md` | Offline research run | Allowed. This is environment/dependency research validation, not runtime behavior. |
| Tune no-trade / flip-cooldown thresholds after data quality and pool depth are adequate | `20260428_backtest_agent_phase1_research_status_memo.md` | Offline research run | Allowed only after data-quality prerequisites; still research-only and not live gates. |

## Rejections and flags

No proposed experiment is currently classified as forbidden live-impacting when executed as written.

Flagged boundary conditions:

- Any experiment that writes to live runtime paths instead of temp or explicit research experiment dirs is rejected.
- Any experiment that routes HMM/KNN outputs into live signals, live sizing, live gates, Hyperliquid execution, safe mode, or operator live controls is rejected.
- Any dataset regeneration that uses current-only websocket/order-book state to reconstruct historical rows is rejected.
- Any live exchange execution, live order placement, Hyperliquid adapter change, or Control page/operator live-control change is rejected.
- Any diagnostic regime-veto bypass or lower-threshold run must stay in a separate diagnostic artifact and must not alter official live or research acceptance semantics.

## Decisions made

- Classified regime, meta, and threshold-sweep work as offline research runs when executed, even if they require temporary cloned configs.
- Classified monitoring thresholds as docs/config only because they define observe-only requirements.
- Classified real BTC dataset rebuild as data regeneration and explicitly not authorized for live fetches by this review.
- Did not classify any proposed item as safe for live promotion.

## Assumptions

- Experiments use BTC Phase 1 scope only.
- Experiments use local dataset/artifact paths such as `data/research/v2-btc-research-1/btcusdt_dataset.parquet` or temporary research output directories.
- Installing optional research dependencies is acceptable only for research runs and does not change default runtime behavior.
- "Live-impacting" means changes to live execution, sizing, live gates, Hyperliquid behavior, runtime safety behavior, or operator live controls.

## Open issues or blockers

No open issues or blockers for boundary classification.

## Handoff notes for other agents

The next experiment package is allowed only as research/offline/data-regeneration work. Keep output flags `research_only: true`, `promotion_ready: false`, and monitoring `observe_only: true`. Do not wire experiment thresholds or outputs into live runtime controls.
