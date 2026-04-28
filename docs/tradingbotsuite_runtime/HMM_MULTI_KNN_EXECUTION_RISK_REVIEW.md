# HMM Multi-KNN Execution Risk Review

Date: April 28, 2026

Agent: Execution and Risk Agent

## Scope

This document is a BTC-only, research-only execution feasibility review for the HMM-routed Lorentzian KNN workstream.

It does not approve live trading. It does not change live execution, position sizing, live accept/reject gates, Hyperliquid order behavior, operator live controls, or runtime safety behavior.

Phase 1 output remains advisory research metadata only. Any future live use requires a separate approval pass after BTC validation and later ETH validation.

## Current Repo State

- Shared issue protocol: `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md` currently reports no open issues.
- HMM/KNN plan config: `configs/v2_btc_hmm_multi_knn_research.json`.
- HMM/KNN research module: `src/tradingbotsuite/research/hmm_knn.py`.
- Current execution stack for future compatibility review only:
  - `src/tradingbotsuite/adapters/execution.py`
  - `src/tradingbotsuite/core/engine.py`
- Runtime safety references:
  - `docs/tradingbotsuite_runtime/BTC_RUNTIME_RELIABILITY_GUIDE.md`
  - `docs/tradingbotsuite_runtime/OPERATOR_GUIDE.md`

At review time, `data/research/v2-btc-hmm-multi-knn-1/artifact_manifest.json` was not present, so artifact replay was not available. This review therefore defines the execution-risk checklist that should be applied once HMM/KNN research artifacts exist.

## Runtime-Adjacent Change Review

Reviewed on April 28, 2026 after reading `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_PROMPTS.md` and the required HMM/KNN context files.

Changed files reviewed:

- `pyproject.toml`: adds optional `research` extra dependencies for `hmmlearn` and `xgboost`; no default runtime dependency or live behavior change was identified.
- `src/tradingbotsuite/main.py`: adds `research-hmm-knn`, `replay-hmm-knn`, and `monitor-hmm-knn` CLI commands; existing `serve`, `manual`, and `smoke-live` command branches were not changed.
- `src/tradingbotsuite/operator_console.py`: adds read-only HMM/KNN artifact and monitoring summaries to the research artifact listing; manual commands, smoke-live, runtime-mode switching, and live position handling branches were not changed by the diff reviewed.
- `src/tradingbotsuite/web/templates/research.html`: adds observe-only HMM/KNN monitoring display on the Research page; no Control page, live command form, runtime-mode control, or live execution action was changed.
- `src/tradingbotsuite/research/dataset.py`: changes are scoped to research dataset building, historical context preservation, BTC Phase 1 guarding, and research label outputs; no live engine path was changed.
- `src/tradingbotsuite/research/hmm_knn.py` and `src/tradingbotsuite/research/hmm_knn_monitoring.py`: research artifact generation and observe-only monitoring only; no execution intents, order placement, live sizing, or Hyperliquid adapter calls were identified.
- `tests/tradingbotsuite/test_operator_ui.py`, `tests/tradingbotsuite/test_research.py`, and `tests/tradingbotsuite/test_hmm_knn.py`: tests cover research artifacts and HMM/KNN paths.

Critical files confirmed unchanged by `git diff --name-only`:

- `src/tradingbotsuite/adapters/execution.py`
- `src/tradingbotsuite/core/engine.py`
- `src/tradingbotsuite/config.py`
- `src/tradingbotsuite/runtime.py`
- `src/tradingbotsuite/web/operator.py`
- `src/tradingbotsuite/web/templates/control.html`
- `src/tradingbotsuite/operator_commands.py`

Verification commands:

```powershell
$env:PYTHONPATH="src"
python -m tradingbotsuite.main --help
python -m pytest tests/tradingbotsuite/test_operator_ui.py::test_operator_artifacts_include_hmm_knn_monitoring_summary tests/tradingbotsuite/test_hmm_knn.py
```

Result:

- `python -m tradingbotsuite.main --help` succeeded and showed the new HMM/KNN commands beside existing runtime commands.
- Targeted pytest run passed: `18 passed`.

Execution and risk confirmation:

- No live execution behavior change identified.
- No position sizing change identified.
- No live accept/reject gate change identified.
- No Hyperliquid adapter or order behavior change identified.
- No operator live control change identified.
- HMM/KNN monitoring remains observe-only and research-only.

## Post-Labeling Runtime-Adjacent Recheck

Rechecked after Labeling Agent changes were present.

Commands requested and run:

```powershell
git diff --name-only
git diff -- src/tradingbotsuite/main.py src/tradingbotsuite/operator_console.py src/tradingbotsuite/web/templates/research.html src/tradingbotsuite/research/dataset.py
git diff --name-only -- src/tradingbotsuite/adapters/execution.py src/tradingbotsuite/core/engine.py src/tradingbotsuite/config.py src/tradingbotsuite/runtime.py src/tradingbotsuite/web/operator.py src/tradingbotsuite/web/templates/control.html src/tradingbotsuite/operator_commands.py
```

`git diff --name-only` reported only:

- `pyproject.toml`
- `src/tradingbotsuite/main.py`
- `src/tradingbotsuite/operator_console.py`
- `src/tradingbotsuite/research/dataset.py`
- `src/tradingbotsuite/web/templates/research.html`
- `tests/tradingbotsuite/test_operator_ui.py`
- `tests/tradingbotsuite/test_research.py`

The specific runtime-adjacent diff showed:

- `src/tradingbotsuite/main.py`: research-only HMM/KNN CLI commands.
- `src/tradingbotsuite/operator_console.py`: read-only HMM/KNN artifact summary support.
- `src/tradingbotsuite/web/templates/research.html`: observe-only HMM/KNN monitoring display on the Research page.
- `src/tradingbotsuite/research/dataset.py`: research dataset labeling, BTC Phase 1 guard, point-in-time checks, raw context preservation, and label outcome fields.

Critical live/control files still had no diffs:

- `src/tradingbotsuite/adapters/execution.py`
- `src/tradingbotsuite/core/engine.py`
- `src/tradingbotsuite/config.py`
- `src/tradingbotsuite/runtime.py`
- `src/tradingbotsuite/web/operator.py`
- `src/tradingbotsuite/web/templates/control.html`
- `src/tradingbotsuite/operator_commands.py`

Post-labeling confirmation:

- No live execution impact identified.
- No live sizing impact identified.
- No live gate impact identified.
- No Hyperliquid behavior impact identified.
- No operator live-control impact identified.
- The dataset helper constructs research labels using existing exit math, but it does not modify runtime position sizing, execution intents, order placement, or live supervision behavior.

## Research Artifacts To Review

When available, the Execution and Risk Agent should inspect these files under `data/research/<plan_version>/`:

| Artifact | Execution-risk use |
| --- | --- |
| `artifact_manifest.json` | Confirm `research_only: true`, symbol scope, dependency backends, config path, dataset path, and artifact paths. |
| `walk_forward_metrics.json` | Confirm `promotion_ready: false`, promotion failures, trade count, expectancy after cost, split concentration, long/short counts, and positive split ratio. |
| `regime_posteriors.parquet` | Review posterior confidence, entropy, top regime labels, recent regime flips, and `regime_no_trade`. |
| `knn_predictions.parquet` | Review expected net return after fees/slippage/funding, neighbor agreement, distance quality, neighbor count, and KNN skip reasons. |
| `meta_predictions.parquet` | Review meta probability, accepted research decisions, direction mix, regime mix, and whether meta filtering hides weak pure-KNN behavior. |
| `neighbor_diagnostics.csv` | Review neighbor distances, weights, labels, source indices, and same-regime neighbor behavior. |

Required invariant: all artifacts must stay research-only and must not emit direct order commands.

## Execution Feasibility Checks

### Cost And Expected Value

Future promotion requires evidence that `expected_net_return_after_costs` remains positive after:

- configured fees
- configured slippage
- funding paid or received over the primary horizon
- adverse funding near funding windows
- stressed slippage during wide-spread or volatile bars

The research cost model should not be considered execution-ready unless the metrics show both normal-case and stressed-case expectancy. A positive raw label or gross return is insufficient.

### Slippage And Spread

The current runtime already has spread protection through `TBS_MAX_SPREAD_BPS` and the engine's spread block. HMM/KNN research must report whether accepted rows cluster near elevated spreads or low neighbor-quality periods.

Future promotion blockers:

- accepted rows require spread assumptions tighter than the live threshold
- expected edge disappears under doubled slippage
- accepted rows concentrate in regimes where order book depth is degraded
- research uses missing spread or book data as neutral instead of explicit missingness

### Funding And Perp Structure

Funding is part of the configured HMM/KNN evaluation and must remain directional. Longs pay positive funding; shorts benefit from positive funding, with the inverse behavior for negative funding.

Future promotion blockers:

- funding cost is missing from expected value
- accepted rows depend on stale or unavailable funding fields
- funding impact is not reported by direction and horizon
- model acceptance increases during adverse funding without a compensating edge

### Liquidation And Leverage Risk

Phase 1 does not size positions and must not infer leverage. A future promotion review must still estimate whether research exits are compatible with liquidation distance and exchange margin constraints.

Future required evidence:

- stop-loss distance, MAE, and barrier widths are compatible with the proposed leverage
- shock/transition regime mostly blocks trades instead of increasing risk
- liquidation-sensitive scenarios are stress-tested before any live sizing change
- open-risk and daily-loss limits remain runtime controls, not model outputs

### Regime Confidence And Flip Risk

HMM output is not execution-ready when confidence is low or state assignment is unstable.

Future promotion blockers:

- high `posterior_entropy` rows are accepted at a high rate
- `recent_regime_flip` rows show poor expectancy but remain accepted
- `regime_no_trade` is bypassed by KNN or meta-model output
- component IDs are treated as stable instead of using train-statistic labels

### Neighbor Quality

Lorentzian KNN output is only useful when analog quality is measurable.

Future promotion blockers:

- `neighbor_count` is below the configured minimum
- `neighbor_distance_quality` is low for accepted rows
- neighbor agreement is high but expected net return is weak
- same-regime neighbor search silently falls back across regimes
- a small number of historical rows dominate accepted signals

### Direction And Split Concentration

Future promotion requires durable behavior across directions and walk-forward splits.

Future promotion blockers:

- long or short side has too few accepted rows
- one split dominates PnL
- positive expectancy comes from one regime only without an explicit no-trade rule for the others
- meta-model results are reported without pure-KNN comparison

## Runtime Safety Compatibility

The existing runtime already has safety controls that must remain authoritative:

- stale market-data safe mode
- Hyperliquid heartbeat and account preflight checks
- reconciliation stale and reconciliation mismatch safe modes
- basis dislocation checks between Binance and Hyperliquid mids
- spread abnormality entry block
- daily-loss and open-risk entry blocks
- live entry confirmation before position persistence
- protective TP/SL order placement and ambiguity handling

HMM/KNN outputs must not bypass these controls. In any future integration design, research acceptance would be one input upstream of the existing decision path, and runtime safety would still be allowed to reject or halt independently.

## Advisory Research Checklist

Later agents may add these fields to `walk_forward_metrics.json` or a separate research-only review artifact. They are advisory metadata only and must not be consumed by live execution:

| Field | Meaning |
| --- | --- |
| `execution_feasibility_status` | Overall research-only status: `blocked`, `needs_more_evidence`, or `research_pass`. |
| `cost_model_status` | Whether fees, slippage, and funding are included and stress-tested. |
| `slippage_stress_status` | Whether expectancy survives wider spread and doubled-slippage scenarios. |
| `funding_stress_status` | Whether adverse funding is reported by direction and horizon. |
| `liquidation_risk_status` | Whether MAE, stop distance, and proposed leverage are compatible in future research. |
| `spread_liquidity_status` | Whether accepted rows rely on healthy spread and book-depth conditions. |
| `promotion_blockers` | Explicit list of unresolved execution-risk blockers. |

Default status for Phase 1 should remain:

```json
{
  "execution_feasibility_status": "blocked",
  "promotion_blockers": [
    "research_only_not_live_promotable",
    "no_live_execution_approval"
  ]
}
```

## Minimum Future Promotion Evidence

Before any Phase 2/3 live-promotion discussion, the research package must show:

- `research_only: true` remains present in all artifacts during research.
- `promotion_ready` remains false until a separate approval pass.
- Pure KNN and meta-filter metrics are both reported.
- Expected value remains positive after fees, slippage, and funding stress.
- No single split dominates results.
- Long and short counts are reported separately and are sufficient.
- High-entropy, recent-flip, low-neighbor-quality, and no-trade rows are not accepted.
- Missing market context stays explicit and is not treated as neutral.
- Runtime safety controls remain outside model control.

## Validation Commands

If HMM/KNN artifacts exist:

```powershell
$env:PYTHONPATH="src"
python -m tradingbotsuite.main replay-hmm-knn --manifest data/research/v2-btc-hmm-multi-knn-1/artifact_manifest.json
```

If future work extends research metrics schema:

```powershell
$env:PYTHONPATH="src"
pytest tests/tradingbotsuite/test_hmm_knn.py
pytest tests/tradingbotsuite/test_engine.py
```

For this docs-only review, no runtime test suite is required.

## Execution And Risk Decision

Current decision: blocked for live promotion.

Reason: Phase 1 is explicitly research-only, and no HMM/KNN artifact manifest is currently available for replay in `data/research/v2-btc-hmm-multi-knn-1/`.

Allowed next step: generate or replay HMM/KNN research artifacts and apply this checklist as an advisory execution-risk review.

Disallowed next steps without separate approval:

- automatic execution from HMM/KNN outputs
- live gate changes
- position sizing changes
- order placement changes
- Hyperliquid adapter changes
- operator live-control changes
