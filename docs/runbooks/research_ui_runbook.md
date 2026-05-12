# Research UI Runbook

Stage: current research branch operator UI

## Purpose

The Research page is a browser control room for offline research jobs and
artifact review. It helps an operator run provider preparation, research
experiments, historical-cycle reviews, and V4 discovery searches without using
live order controls.

Research outputs remain `research_only`, `observe_only`, and
`promotion_ready: false` unless a later promotion process changes them.

## Start

```powershell
$env:TBS_OPERATOR_UI_ENABLED="true"
$env:TBS_OPERATOR_UI_SECRET="change-this-local-secret"
$env:TBS_RUNTIME_MODE="paper"
python -m tradingbotsuite.main serve
```

Open `http://127.0.0.1:8000/ui`, log in, then select `Research`.

## Main Controls

- `Operator Board`: first-pass status for data readiness, current run, progress,
  latest snapshot, blockers, leads, artifact count, and maturity.
- `Provider Pipeline`: prepares or verifies provider/archive inputs. Use
  `Intake`, `Dataset`, `Evidence`, or `All` depending on the desired scope.
- `Research Experiment`: runs a configured evidence bundle from
  `configs/experiments/`.
- `Historical Cycle Review`: runs a configured full cycle from
  `configs/research/` into an isolated operator output directory.
- `V4 Discovery Run`: runs or resumes real GMM-regime/KNN entry-discovery
  searches from `configs/discovery/`, including explicit no-regime baselines.
- `Queue Evidence Review Bundle`: queues the operator-visible provider,
  experiment, historical-cycle, and discovery review sequence.
- Routine buttons queue common research-only actions: `Preflight Data
  Readiness`, `Quick Discovery`, `Standard Discovery`, `Deep Discovery`, `Pause
  After One Trial`, `Resume Run`, `Open Latest Snapshot`, `Review Candidate
  Eligibility`, and `Open Artifact List`.

The page also renders profitability, candidate mix, gate status, holding-window,
and discovery-ledger charts from the newest artifacts found under the configured
research output directory. If chart evidence is missing, the page shows the
missing-evidence reason in page text instead of relying on an empty shell.

## Maturity Labels

- `Diagnostic`: plumbing, data-quality, or smoke evidence only.
- `Screen-worthy`: a lead exists and has artifacts worth manual review, but
  blockers and validation evidence are still being inspected.
- `Candidate-ready`: requires exit-lab evidence, comparator evidence,
  no-regime baseline when a regime mode is claimed, validation floors, and gate
  evidence. This remains research-only and does not authorize live use.

## Overwrite Protection

- Historical-cycle jobs write a copied spec and isolated output directory under
  `data/research/operator_runs/historical_cycles/`.
- Fresh discovery jobs write under a job-specific output directory.
- Paused or resumed discovery jobs use the stable run-id directory so snapshots,
  ledgers, and `run_state.json` can continue from the previous checkpoint.
- Existing completed discovery runs refuse overwrite. Use a new run id for a new
  full run.

## Safety Rules

- The Research page does not expose manual signal, smoke-live, set-mode, sizing,
  or canary controls.
- Research jobs are blocked in live mode and while live position state is unsafe.
- UI path validators allow specs only from `configs/data`, `configs/experiments`,
  `configs/research`, `configs/discovery`, or the configured research output
  directory as appropriate.
- Submitted jobs must pass CSRF and same-origin checks.
- Passive polling and chart refreshes must not launch heavy jobs.

## Evidence To Check

- Operator Board: data readiness, current run, progress, latest snapshot,
  blockers, leads, artifact count, and maturity label.
- Jobs table: status, error text, and result paths.
- Artifacts panel: latest manifests and summaries.
- Discovery ledger chart: interesting, blocked, and filter-blocked counts.
- HMM/KNN monitoring: entropy, no-trade behavior, neighbor quality, drift, and
  alert summaries.
- Candidate eligibility: exit lab, comparator, no-regime baseline when regime is
  claimed, validation floors, blocker registry, and gate evidence.
- Stage 13 readiness: planning evidence only. It does not start canaries, switch
  mode, place orders, promote artifacts, or change sizing.

## Related Docs

- `docs/OPERATOR_QUICKSTART.md`
- `docs/OPERATOR_GUIDE.md`
- `docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md`
