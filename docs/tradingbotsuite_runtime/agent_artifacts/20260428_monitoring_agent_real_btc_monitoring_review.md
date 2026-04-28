# Agent name

Monitoring Agent

# Task received

Evaluate the real-data `monitoring_report.json`.

Report:

- feature outages
- regime drift
- entropy/no-trade warnings
- neighbor quality warnings
- funding warnings
- calibration placeholders
- whether every alert is observe-only

# Files read

- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_PROMPTS.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md`
- `data/research/v2-btc-hmm-multi-knn-1/monitoring_report.json`
- `data/research/v2-btc-hmm-multi-knn-1/artifact_manifest.json`
- `data/research/v2-btc-hmm-multi-knn-1/walk_forward_metrics.json`
- `src/tradingbotsuite/research/hmm_knn_monitoring.py`

# Files changed

- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_monitoring_agent_real_btc_monitoring_review.md`

# Commands/tests run

```powershell
Get-Content docs\tradingbotsuite_runtime\HMM_MULTI_KNN_AGENT_PROMPTS.md
Get-Content docs\tradingbotsuite_runtime\HMM_MULTI_KNN_AGENT_ISSUES.md
Get-ChildItem -Recurse -File -Path C:\Users\papaa\Music\tradingbotsuite -Filter monitoring_report.json
Get-Content data\research\v2-btc-hmm-multi-knn-1\monitoring_report.json
```

Structured report extraction:

```powershell
@'
import json
from pathlib import Path
report_path = Path('data/research/v2-btc-hmm-multi-knn-1/monitoring_report.json')
report = json.loads(report_path.read_text(encoding='utf-8'))
feature = report.get('feature_outages', {})
features = feature.get('features', {})
high = {k:v for k,v in features.items() if (not v.get('present', True)) or (v.get('missing_or_nonfinite_rate') or 0) > feature.get('outage_threshold', 0.2)}
alerts = report.get('alerts', [])
summary = {
    'path': str(report_path.resolve()),
    'research_only': report.get('research_only'),
    'observe_only': report.get('observe_only'),
    'promotion_ready': report.get('promotion_ready'),
    'alert_count': len(alerts),
    'alert_codes': [a.get('code') for a in alerts],
    'all_alerts_observe_only': all(a.get('observe_only') is True for a in alerts),
    'configured_feature_count': feature.get('configured_feature_count'),
    'high_outage_feature_count': feature.get('high_outage_feature_count'),
    'high_outage_features': high,
    'entropy_no_trade': report.get('entropy_no_trade'),
    'regime_distribution_drift': report.get('regime_distribution_drift'),
    'neighbor_quality': report.get('neighbor_quality'),
    'funding_costs': report.get('funding_costs'),
    'calibration_decay': report.get('calibration_decay'),
    'source_metrics': report.get('source_metrics'),
}
print(json.dumps(summary, indent=2, sort_keys=True))
'@ | python -
```

# Report reviewed

```text
data/research/v2-btc-hmm-multi-knn-1/monitoring_report.json
```

Identity:

- `monitoring_report_version`: `v2-hmm-knn-monitoring-report-1`
- `symbol`: `BTCUSDT`
- `asset_scope`: `["BTCUSDT"]`
- `row_count`: `446`
- `research_only`: `true`
- `observe_only`: `true`
- `promotion_ready`: `false`
- `live_vs_replay_mismatch`: `not_available`

# Monitoring findings

## Feature outages

- Configured feature count: `28`
- High outage feature count: `0`
- Outage threshold: `0.20`
- All monitored feature columns are present with `missing_or_nonfinite_rate: 0.0`.
- No `feature_outage` alert was emitted.

## Regime drift

- Regime drift is available.
- Baseline split: `0`
- Max drift from baseline: `0.1995790279372369`
- This stays below the monitor warning threshold used by code (`0.35`), so no `regime_distribution_drift` alert was emitted.
- Split distributions:
  - Split `0`: bear `0.4423`, bull `0.1282`, range `0.2692`, shock `0.1603`
  - Split `1`: bear `0.3782`, bull `0.0513`, range `0.3141`, shock `0.2564`
  - Split `2`: bear `0.3134`, bull `0.3060`, range `0.2910`, shock `0.0896`

## Entropy and no-trade

- Alert emitted: `high_no_trade_rate`
- Alert severity: `warn`
- Alert is observe-only: `true`
- Overall posterior entropy mean: `0.23115281296041446`
- Overall posterior entropy p95: `0.5350898796165469`
- Overall recent regime flip rate: `0.8946188340807175`
- Overall regime no-trade rate: `0.9103139013452914`
- Split no-trade rates:
  - Split `0`: `0.9423076923076923`
  - Split `1`: `0.8717948717948718`
  - Split `2`: `0.917910447761194`
- No `high_posterior_entropy` alert was emitted; the warning is specifically the elevated no-trade rate.

## Neighbor quality

- Alert emitted: `low_neighbor_quality`
- Alert severity: `warn`
- Alert is observe-only: `true`
- Diagnostic coverage rate: `1.0`
- Insufficient neighbor rate: `0.0`
- Minimum configured neighbor count: `8`
- Mean neighbor count: `32.0`
- Minimum observed neighbor count: `32.0`
- Mean neighbor distance quality: `0.15553586717814147`
- p05 neighbor distance quality: `0.10972238899570713`
- Skip reasons: `none: 446`
- Interpretation: neighbor pools are present and fully diagnosed, but distance quality is weak enough to trigger an advisory warning.

## Funding warnings

- No funding warning was emitted.
- Available funding/cost columns:
  - `funding_rate`
  - `funding_paid_or_received`
  - `expected_net_return_after_costs`
- Funding rate mean/min/max: `0.00010000000000000003` / `0.0001` / `0.0001`
- Funding paid/received mean/min/max: `2.6905829596412563e-06` / `-0.00030000000000000003` / `0.00030000000000000003`
- Expected net return after costs mean/min/max: `-0.16607214237780166` / `-0.7465637324705753` / `0.7290431777054845`

## Calibration placeholders / calibration decay

- Calibration decay is available, not a placeholder-only section.
- KNN calibration:
  - Overall Brier score: `0.24022957147733126`
  - Rows: `446`
  - Split Brier scores: `0.2484992657953483`, `0.23502411928667144`, `0.23666224482160203`
  - Buckets are populated across probability bands up to `(0.6, 0.8]`.
- Meta calibration:
  - Overall Brier score: `0.251159594803084`
  - Rows: `446`
  - Split Brier scores: `0.2543693737224081`, `0.25389788614177594`, `0.24423497569673702`
  - Buckets are populated across `(0.2, 0.4]`, `(0.4, 0.6]`, and `(0.6, 0.8]`.
- `live_vs_replay_mismatch` remains the explicit placeholder: `not_available`.

# Alert observe-only confirmation

Alerts in the report:

```text
high_no_trade_rate
low_neighbor_quality
```

Every alert has:

```json
"observe_only": true
```

No alert changes live state. The report remains JSON research metadata and does not trigger live gating, safe mode, execution, position sizing, Hyperliquid behavior, or operator live controls.

# Decisions made

- Treated `data/research/v2-btc-hmm-multi-knn-1/monitoring_report.json` as the real BTC monitoring report because it is under the repo `data/research` tree and references `data/research/v2-btc-research-1/btcusdt_dataset.parquet`.
- Did not run a new monitor generation command; this task asked to inspect and report the existing real-data monitoring report.
- Did not modify monitoring code, live code, operator controls, or generated research artifacts.

# Assumptions

- "Real-data monitoring report" refers to the repo-local BTC artifact report under `data/research/v2-btc-hmm-multi-knn-1/monitoring_report.json`, not the synthetic temp reports under `%TEMP%`.
- Calibration placeholders means both the populated `calibration_decay` section and the still-placeholder `live_vs_replay_mismatch: not_available` should be called out.

# Open issues or blockers

None.

`docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md` reported no open issues.

# Handoff notes for other agents

- Real BTC monitoring has no feature outage warning and no regime drift warning.
- Real BTC monitoring does warn on elevated no-trade rate and low neighbor quality.
- Funding data is present; no funding warning is active.
- Calibration sections are populated for both KNN and meta outputs.
- The report remains research-only and observe-only: `research_only: true`, `observe_only: true`, `promotion_ready: false`.
