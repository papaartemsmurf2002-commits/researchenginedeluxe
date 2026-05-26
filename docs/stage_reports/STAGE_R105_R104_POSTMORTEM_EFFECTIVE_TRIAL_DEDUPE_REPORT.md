# Stage R105 R104 Postmortem Effective Trial Dedupe Report

Date: 2026-05-19
Owner: Codex Research Agent
Stage: R105 candidate factory component falsification
Status: research-only postmortem complete; no candidate-ready claim

## Research Boundary

This packet starts the R105 candidate-factory path with postmortem and pruning
evidence only. It does not promote a candidate, write live configuration, place
orders, change runtime mode, touch sizing, or make a profitability claim. All
new outputs are `research_only`, `observe_only`, and `promotion_ready: false`.

`ISSUE-R104-001` remains open. The compact public-archive fixture is valid for
screening and artifact/schema checks, but expanded durable BTC/ETH primary-bar
evidence and reruns are still required before candidate-ready claims.

## Implemented

- Added `src/tradingbotsuite/research_discovery/artifact_keys.py` with
  deterministic R105 research-discovery artifact key helpers.
- Added `src/tradingbotsuite/research_discovery/r105_component_factory.py`
  with a `postmortem` command:

```powershell
$env:PYTHONPATH='src'; python -m tradingbotsuite.research_discovery.r105_component_factory postmortem `
  --run data\research\operator_runs\discovery_runs\exact-entry-sweep-btcusdt-durable-r104-v1\run-discovery-142f3b61b761470b8aeb105967dd9c47 `
  --out data\research\operator_runs\r105\postmortem_r104
```

- Added focused tests for artifact keys and postmortem artifact writing.
- Generated derived R105 postmortem artifacts without modifying the source
  R104 run.

## Generated Evidence

Output directory:

```text
data/research/operator_runs/r105/postmortem_r104
```

This directory is generated local evidence under ignored operator-run storage.
The committed audit trail includes the tracked sanitized summary:

```text
docs/stage_reports/STAGE_R105_R104_POSTMORTEM_TRACKED_SUMMARY.json
```

Required outputs:

| Artifact | Purpose |
| --- | --- |
| `r105_postmortem_manifest.json` | Research-only manifest, source hashes, output hashes, limitations, and issue status. |
| `effective_trial_summary.parquet` | Blocker/feature/horizon/distance summary with effective-trial counts and signature counts. |
| `prediction_hash_clusters.parquet` | Ledger-level prediction-signature clusters. |
| `top_blocked_by_cluster.parquet` | Top blocker clusters for R105 pruning and lab ordering. |
| `r104_postmortem.md` | Human-readable postmortem report. |

Summary from `r105_postmortem_manifest.json`:

| Field | Value |
| --- | ---: |
| Scheduled trials | `570240` |
| Blocked rows | `570240` |
| Effective parameter keys | `570240` |
| Prediction signature clusters | `564` |
| Entry signature clusters | `38` |

Blocker distribution:

| Blocker | Rows |
| --- | ---: |
| `overlap_ratio_above_ceiling` | `222720` |
| `independent_event_count_below_floor` | `194976` |
| `signal_rate_near_ceiling` | `86304` |
| `signal_rate_above_discovery_ceiling` | `60480` |
| `realized_expectancy_below_discovery_floor` | `5760` |

No-regime inactive dimensions are now explicitly recorded as dropped from the
effective-trial key when present:

- `hmm_entropy_threshold`
- `hmm_posterior_threshold`
- `hmm_state_count`
- `regime_detector_type`
- `regime_gate_enabled`
- `same_regime_neighbor_pool_enabled`
- `same_regime_only`
- `true_hmm_backend_used`

The R104 exact sweep configured these no-op dimensions as singletons, so the
effective parameter-key count still equals the scheduled trial count. The more
important compression in the available artifacts is behavioral: the existing
ledger collapses to `564` prediction-summary signatures and `38` entry-summary
signatures.

## Limitations

- Per-bar prediction artifacts were not persisted for blocked R104 trials
  because the run used `interesting_only` persistence and all trials were
  blocked.
- `prediction_hash` and `entry_event_hash` in the R105 postmortem are therefore
  deterministic ledger-summary signatures, not timestamp-level prediction vector
  hashes.
- This packet does not rerun historical cycles, exact sweeps, exit labs,
  validation floors, multiple-testing gates, or candidate-pack eligibility.
- This packet does not close `ISSUE-R104-001`.

## Validation

Passed:

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Results:

- `tests/research_discovery`: `179 passed`
- `tests/contracts`: `425 passed`

## Next Work

Use this postmortem as the input to R105 entry-only, exit-only, orderflow,
KNN/regime, and filter falsification labs. Do not run another coupled
brute-force sweep as the default next step unless component evidence justifies
it.
