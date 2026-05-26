# WPR105-01 Latest Sweep Postmortem Effective Trials

Owner: Codex Research Agent
Stage: R105 candidate factory component falsification
Status: closed
Created: 2026-05-19

## Goal

Start the R105 candidate-factory path by turning the completed R104 exact BTC
discovery sweep into reusable postmortem evidence. The packet measures
scheduled versus effective-equivalent trials, blocker clusters, and available
prediction/entry signature clusters so later R105 work can prune no-op
dimensions before running entry, exit, filter, and orderflow labs.

## Allowed paths

- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `docs/work_packets/**`
- `docs/stage_reports/**`
- `src/tradingbotsuite/research_discovery/**`
- `tests/research_discovery/**`
- `tests/contracts/**`
- `data/research/operator_runs/r105/**`

## Constraints

- Keep all outputs `research_only`, `observe_only`, and
  `promotion_ready: false`.
- Do not add live execution, runtime-mode changes, order placement, live config
  writes, promotion behavior, or sizing behavior.
- Do not claim candidate readiness or profitability from the compact R104
  fixture.
- Preserve `ISSUE-R104-001`; expanded durable primary-bar evidence remains
  required before candidate-ready claims.
- Do not overwrite the completed R104 run artifacts. R105 postmortem outputs
  must be new derived artifacts under the research output tree.

## Planned implementation

1. Add deterministic artifact-key utilities for stable R105 trial,
   effective-trial, prediction-signature, and entry-signature hashing.
2. Add an R105 component-factory postmortem command that reads an existing
   discovery run manifest/ledger, reconstructs scheduled trial parameters from
   the resolved discovery spec, drops no-op regime dimensions under
   `regime_mode: none`, and writes clustered Parquet/JSON/Markdown artifacts.
3. Add focused regressions for no-regime effective-trial collapse, research
   boundary metadata, output schemas, and truthful limitations when per-bar
   prediction ledgers were not persisted.
4. Run the postmortem on the completed R104 BTCUSDT exact sweep.
5. Record the evidence in a stage report and ledger without closing
   `ISSUE-R104-001`.

## Validation target

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
git diff --check
```

## Exit evidence

- Added deterministic R105 artifact-key helpers in
  `src/tradingbotsuite/research_discovery/artifact_keys.py`.
- Added the research-only R105 component-factory postmortem command in
  `src/tradingbotsuite/research_discovery/r105_component_factory.py`.
- Generated postmortem artifacts under
  `data/research/operator_runs/r105/postmortem_r104/`:
  - `r105_postmortem_manifest.json`
  - `effective_trial_summary.parquet`
  - `prediction_hash_clusters.parquet`
  - `top_blocked_by_cluster.parquet`
  - `r104_postmortem.md`
- The completed R104 sweep remains a no-candidate research result:
  `570240` blocked rows, `570240` effective parameter keys, `564`
  ledger-level prediction signature clusters, and `38` entry signature
  clusters.
- Per-bar prediction hashes are explicitly unavailable from the existing R104
  artifacts because the run persisted `interesting_only` trial artifacts and
  all trials were blocked.
- `ISSUE-R104-001` remains open; this packet does not create expanded durable
  fixture evidence, rerun durable cycles, or claim candidate readiness.
- Validation passed:
  `python -m compileall -q src\tradingbotsuite`;
  `$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q`;
  `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`.
