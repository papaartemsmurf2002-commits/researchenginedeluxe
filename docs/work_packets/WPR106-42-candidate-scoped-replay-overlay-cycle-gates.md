# WPR106-42 Candidate-Scoped Replay Overlay Cycle Gates

## Goal

Add a fail-closed historical-cycle contract for candidate-scoped materialized
prediction overlays so replayed WPR106-31 KNN prediction artifacts can be
evaluated through normal ranking, split, cost-stress, gate, and rejection paths
without weakening gates or treating research evidence as live signals.

## Current Repo Facts

- Active checkout is `main`, documented as the migrated R106 research mirror.
- Open P0 count is zero. The remaining open P1 is `ISSUE-R104-001`, which
  blocks candidate-ready empirical claims until durable candidate-depth cycles,
  exact sweeps, and eligibility review complete.
- WPR106-31 produced 24 BTCUSDT and 24 ETHUSDT replayed KNN prediction
  artifacts, entry-signal manifests, and blocked top-3 frozen-entry exit-lab
  slices. No candidate pack or candidate-ready claim exists.
- Historical-cycle materialized prediction overlays already validate
  research-only/observe-only manifests, reject promotion-ready overlays, enforce
  split-safety columns, and merge required KNN columns into feature frames.
- Current overlay behavior is feature-set scoped: one
  `hmm_knn_local_analog_v2` overlay is merged globally into the feature frame
  for all candidates using that feature set.
- Candidate generation, aggregate backtests, split backtests, cost-stress
  backtests, rankings, gate reports, and candidate-pack writing already flow
  through the existing historical runner. Candidate packs are written only when
  `evaluate_research_candidate_gate()` passes.

## Conflicts And Stale Docs Found

- Older docs still reference `research/v3-experimental-engine` as the current
  branch; `docs/ACTIVE_INDEX.md` and WPR106-21+ evidence identify this checkout
  as `main`.
- WPR106-31 artifacts are replay evidence, not cycle-ranking or candidate-pack
  evidence.
- A single global overlay cannot truthfully evaluate 24 separate replayed KNN
  prediction frames in one cycle. Candidate-scoped routing is needed before
  full replay-overlay cycle runs are meaningful.
- Exact WPR106-31 replayed parameter values may not all fit the current
  historical-cycle strategy metadata search-domain. That mismatch must remain
  fail-closed unless a later packet explicitly scopes exact replay spec
  materialization.

## Allowed Edit Paths

- `docs/work_packets/WPR106-42-candidate-scoped-replay-overlay-cycle-gates.md`
- `docs/work_packets/WPR106-42-progress.jsonl`
- `src/tradingbotsuite/research_cycle/spec.py`
- `src/tradingbotsuite/research_cycle/runner.py`
- `tests/contracts/test_research_cycle_contract.py`
- `tests/historical/test_full_cycle_synthetic.py`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md` only if a new blocker is discovered
- `docs/stage_reports/STAGE_R106_CANDIDATE_SCOPED_REPLAY_OVERLAY_CYCLE_GATES_REPORT.md`

## Forbidden Edit Paths

- live, paper, runtime, order-placement, and promotion execution paths
- strategy plugin behavior and strategy parameter domains
- candidate gate thresholds, validation floors, and pack eligibility logic
- backtest execution, latency, cost, fill, or split semantics
- generated research artifacts under `data/research/**`
- generated candidate packs
- broad docs rewrites outside active index, ledger, known issues if needed, and
  the stage report
- `.pytest_cache/**`

## Subagents Used

- Research Runner Agent: audited WPR106-31 replay artifacts and identified the
  global-overlay versus per-candidate-overlay mismatch.
- Validation Engineer: read-only review of candidate-scoped overlay integration
  hazards, gate preservation, provenance, and focused tests.

## Tests To Run

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_research_cycle_contract.py -q
$env:PYTHONPATH='src'; python -m pytest tests\historical\test_full_cycle_synthetic.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
git diff --check
```

Broaden to `tests\research_artifacts\test_candidate_pack.py` if candidate-pack
gate inputs or manifest fields change beyond provenance pass-through.

## Artifacts Expected

- Versioned spec fields for candidate-scoped materialized prediction overlays.
- Runner support for selecting per-candidate overlay frames while preserving
  existing global overlay behavior.
- Provenance columns in rankings and backtest index showing overlay scope,
  candidate key, prediction path/hash, manifest path/hash, row count, and
  split-safety status.
- Focused contract tests for parsing, duplicate rejection, fail-closed unmatched
  candidate overlays, and candidate-specific feature-frame identity.
- Stage report and progress ledger.

No generated research-cycle replay outputs, candidate packs, live signals,
paper signals, order-placement behavior, runtime-mode changes, or promotion
claims are expected in this packet.

## Definition Of Done

- Existing global materialized prediction overlays continue to work.
- Candidate-scoped overlays can be keyed to generated candidate IDs and are
  merged only for that candidate.
- Candidate-scoped overlays fail closed when unmatched, duplicate, missing, not
  research/observe-only, promotion-ready, row-mismatched, or split-unsafe.
- Aggregate, split, and cost-stress backtests use the same candidate-scoped
  feature frame and hash for a candidate.
- Rankings and backtest index preserve overlay provenance for audit.
- Candidate gates remain unchanged; zero eligible candidates remains valid.
- Focused validation and contract validation pass.

## Rollback Plan

Revert only files listed in allowed edit paths. Do not touch generated research
artifacts, candidate packs, live/runtime paths, strategy plugins, search-domain
metadata, or unrelated cache state.
