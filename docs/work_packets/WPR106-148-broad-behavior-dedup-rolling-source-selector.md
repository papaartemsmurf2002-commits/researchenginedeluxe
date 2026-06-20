# WPR106-148 Broad Behavior-Dedup Rolling Source Selector

Date: 2026-06-12
Owner: Codex Research Agent
Status: closed

## Objective

Move away from defending the rejected WPR106-133 path-specific lead and run a
broader behavior-deduped selector across previously discarded 2024-forward
source and fixed-family rows.

The packet uses the WPR106-144 direct source/family benchmark universe as the
starting point, then adds accepted-trade behavior de-duplication and rolling
pre-May holdout requirements before any May benchmark. The goal is to test
whether a broader source/family row set can satisfy the user's month-to-month
stability target better than the recent path-specific WPR106-133 work.

## Allowed Paths

- `docs/work_packets/WPR106-148-broad-behavior-dedup-rolling-source-selector.md`
- `docs/stage_reports/STAGE_R106_BROAD_BEHAVIOR_DEDUP_ROLLING_SOURCE_SELECTOR_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_148_broad_behavior_dedup_rolling_source_selector/**`

## Inputs

- `data/research/wpr106_141_causal_monthly_family_rotation_search/**`
- `data/research/wpr106_144_direct_source_family_stability_benchmark/**`
- source packet artifacts already consumed by WPR106-141, WPR106-144, and
  their source-universe loaders.

## Boundaries

- Research-only, observe-only, promotion-ready false.
- No candidate pack, paper/live artifact, order placement, sizing change,
  runtime-mode change, live configuration write, or promotion claim.
- May 2026 must not affect behavior hashes, rolling holdout requirements,
  selector thresholds, ranking, or fixed selected rows.
- The row universe may include active 1, 3, and 5 trades/day variants when
  costs and overlap are accounted for by the source/family replay helpers.
- This packet reuses existing artifact-level rows and replay helpers; it does
  not change shared strategy, feature, KNN, live, or candidate-pack code.
- CUDA is not expected. CPU/vectorized pandas/accounting is sufficient and no
  speedup claim is allowed unless a real CUDA path is used and verified.
- If a blocking correctness risk is found, update `docs/KNOWN_ISSUES.md`.

## Evidence Plan

1. Load the WPR106-144 individual-source and fixed-family portfolio rows and
   monthly returns.
2. Rebuild the WPR106-141/WPR106-144 source trade universe and replay each row
   on pre-May to compute accepted-trade behavior hashes.
3. Deduplicate rows by accepted pre-May behavior, keeping the best pre-May
   representative per behavior path.
4. Compute rolling pre-May train/holdout diagnostics over fixed anchored
   windows ending before May 2026.
5. Select only rows whose full pre-May profile and rolling holdouts meet
   stability requirements.
6. Replay the fixed selected rows on May 2026 as a benchmark only.
7. Summarize whether any broad row or family survives with enough stability to
   justify a new follow-up lead.

## Validation

Run focused script compile, then the branch baseline:

```powershell
python -m compileall -q data/research/wpr106_148_broad_behavior_dedup_rolling_source_selector/scripts
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

## Evidence Results

- Input rows: 2,181 WPR106-144 source/family candidate rows.
- Exact source behavior de-duplication snapshot: 659 source rows to 518 source
  rows.
- Accepted-trade behavior de-duplication: 1,219 unique pre-May behavior hashes.
- Pre-May behavior-deduped screen: 258 strict rows, 741 loose rows, 444
  rolling-candidate rows, and 134 robust rows.
- Fixed May benchmark set: 80 behavior-unique robust rows selected with no May
  data used for selection.
- May benchmark: 7/80 positive rows, 8.75% positive rate, median -0.012930,
  mean -0.015425, return sum -1.233990, best +0.019375, worst -0.133646.
- May by entity: 7/69 individual-source rows positive and 0/11 fixed
  source-family portfolios positive.

## Closeout

WPR106-148 rejects the broad behavior-deduped rolling source selector as a
candidate-ready or portfolio-ready direction. The pre-May controls are stronger
than the WPR106-147 path-specific audit, but the fixed May 2026 benchmark
rejects the broad survivor set. The few May-positive WPR106-137 pockets remain
research-only follow-up leads requiring new controls and materially distinct
evidence before any candidate-pack attempt.

Validation passed:

```powershell
python -m compileall -q data/research/wpr106_148_broad_behavior_dedup_rolling_source_selector/scripts
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

Contracts result: 460 passed.
