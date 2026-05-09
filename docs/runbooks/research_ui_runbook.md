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

- `Provider Pipeline`: prepares or verifies provider/archive inputs. Use
  `Intake`, `Dataset`, `Evidence`, or `All` depending on the desired scope.
- `Research Experiment`: runs a configured evidence bundle from
  `configs/experiments/`.
- `Historical Cycle Review`: runs a configured full cycle from
  `configs/research/` into an isolated operator output directory.
- `V4 Discovery Run`: runs or resumes real HMM/KNN entry-discovery searches
  from `configs/discovery/`.
- `Run Full Research Review`: queues the operator-visible review bundle.

The page also renders profitability, candidate mix, gate status, holding-window,
and discovery-ledger charts from the newest artifacts found under the configured
research output directory.

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

- Jobs table: status, error text, and result paths.
- Artifacts panel: latest manifests and summaries.
- Discovery ledger chart: interesting, blocked, and filter-blocked counts.
- HMM/KNN monitoring: entropy, no-trade behavior, neighbor quality, drift, and
  alert summaries.
- Stage 13 readiness: should remain blocked until required paper, shadow,
  testnet, rollback, and approval evidence exists.

## Related Docs

- `docs/OPERATOR_QUICKSTART.md`
- `docs/OPERATOR_GUIDE.md`
- `docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md`
