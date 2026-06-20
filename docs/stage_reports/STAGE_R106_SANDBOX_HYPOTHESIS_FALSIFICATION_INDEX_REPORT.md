# Stage R106 Sandbox Hypothesis Falsification Index Report

Date: 2026-06-18
Work packet: `docs/work_packets/WPR106-235-sandbox-hypothesis-falsification-index.md`
Status: closed

## Summary

WPR106-235 adds hypothesis-level falsification indexes for Rapid Strategy
Iteration Sandbox artifacts. Agents can now inspect grouped hypothesis outcomes
instead of manually scanning row-level venue/exit/filter rankings.

## Implementation

- Added `src/tradingbotsuite/research_sandbox/falsification.py`.
- Added run-level `summarize_sandbox_hypotheses`.
- Added suite-level `summarize_sandbox_suite_hypotheses`.
- Reports validate sandbox manifests, rankings Parquet boundary columns, and
  evidence-request descriptors before summarizing.
- Reports group rows by hypothesis/family and include:
  - tested venues, symbols, data families, holding periods, exits, and filters;
  - source IDs, sides, run IDs, case IDs, and run directories;
  - result, screened, rejected, and blocked counts;
  - best trial ID/rank/status/score/net/trade-count metrics;
  - evidence-request trial IDs;
  - blocked and rejected reason counts;
  - a sandbox falsification decision and reason.
- Run-level output writes `hypothesis_falsification.json` and
  `hypothesis_falsification.parquet`.
- Suite-level output writes `suite_hypothesis_falsification.json` and
  `suite_hypothesis_falsification.parquet`.
- Added `summarize-rapid-strategy-sandbox-hypotheses` as a research CLI command
  with research-root `--run-dir`/`--suite-dir` enforcement.
- Registered the command in the research command registry and boundary
  contract.
- Extended the sandbox research contract with hypothesis falsification rules.

## Boundary

Hypothesis falsification reports are sandbox analysis artifacts. They carry:

- `research_only: true`
- `observe_only: true`
- `promotion_ready: false`
- `sandbox_only: true`
- `candidate_evidence: false`
- `candidate_pack_eligible: false`

The reports can say a hypothesis deserves a later strict-validation request,
but that is not candidate evidence and is not promotion readiness. The packet
does not execute strict validation, write candidate packs, create paper/live
signals, define sizing, place orders, mutate runtime mode, write live
configuration, or claim promotion readiness.

## Validation

Final validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q
# 40 passed

$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q
# 11 passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
# 11 passed

python -m compileall -q src\tradingbotsuite
# passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
# 461 passed
```

## Remaining Work

This packet does not execute strict validation from evidence requests and does
not add an interactive UI/query layer. Those remain separate follow-up work
under the active sandbox objective.
