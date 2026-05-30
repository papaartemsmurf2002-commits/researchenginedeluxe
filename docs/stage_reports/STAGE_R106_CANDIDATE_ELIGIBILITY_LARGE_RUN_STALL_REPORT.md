# Stage R106 Candidate Eligibility Large-Run Stall Report

Work packet:
`docs/work_packets/WPR106-27-candidate-eligibility-large-run-stall.md`

Date: 2026-05-30

## Summary

WPR106-27 investigated the autopilot run that had been running for about
16 hours. The job was not in catalog refresh, cycle execution, exact discovery,
analysis, or exit-lab work. It had reached BTCUSDT candidate-pack eligibility
and stalled before writing a `candidate_pack_eligibility` output directory.

Two P1 performance blockers were fixed:

- the eligibility bridge reread all 570,240 exact-discovery trial JSON records
  twice before candidate evaluation;
- the bridge called the historical-cycle candidate gate for every interesting
  discovery candidate, reloading shared cycle evidence for each row.

No generated artifacts were rewritten.

## Observed Running Job

- Job ID:
  `run-research-autopilot-9a4ce549dd1c4ffba99ab54449ef2a0b`.
- Operator DB status: `running`.
- Requested symbols: `BTCUSDT`, `ETHUSDT`.
- Last log: `autopilot skipped: frozen_entry_exit_lab` for `BTCUSDT` at
  `2026-05-29T17:47:55Z`.
- Autopilot manifest status: `running`, last updated
  `2026-05-29T17:47:55Z`.
- `candidate_pack_eligibility` output directory: not present.
- Active process command line:
  `python -m tradingbotsuite.main serve --host 127.0.0.1 --port 8000`.

Interpretation: the server process entered the synchronous BTC candidate
eligibility helper and did not return.

## Data Size Evidence

BTC exact discovery:

- completed trials: 570,240;
- interesting candidates: 22,560;
- blocked candidates: 547,680;
- filter blockers: 0.

BTC historical cycle:

- candidate rankings: 63 rows;
- candidate gate report: 63 rows;
- backtest index: 303 rows;
- discovery candidate ID overlap with cycle rankings: 0.

The correct eligibility result for current BTC evidence is therefore an audit
artifact with 22,560 blocked rows and no eligible candidate-pack rows.

## Root Cause

The bridge did full trial-record integrity validation by opening every trial
JSON once in `_run_state_reasons` and again in `_ledger_integrity_reasons`.
That is acceptable for small unit and smoke runs, but not for 570,240 durable
trial records inside the one-button operator path.

After that preflight, each discovery candidate invoked
`evaluate_research_candidate_gate()`. For the current BTC run, every discovery
candidate is absent from the 63-row historical-cycle ranking table, so the
historical gate can be decided from ranking membership after one rankings load.
The old code still reloaded the same cycle manifest and rankings thousands of
times.

## Fix Implemented

- `src/tradingbotsuite/research_discovery/candidate_pack_bridge.py`
  - Keeps exhaustive trial-record reads for small discovery runs.
  - Uses count checks, ledger ID coverage checks, vectorized
    `record_sha256` checks, and deterministic sampled trial-record validation
    for large completed discovery runs.
  - Reads large discovery manifests with targeted `required_outputs`
    normalization instead of recursively normalizing every completed-trial
    hash entry.
  - Builds one candidate-gate context per cycle manifest and reuses it across
    all discovery candidates.
- `src/tradingbotsuite/research_artifacts/candidate_pack.py`
  - Adds `ResearchCandidateGateContext`,
    `build_research_candidate_gate_context()`, and
    `evaluate_research_candidate_gate_from_context()`.
  - Caches ranking membership and candidate gate results for repeated
    eligibility checks.
- `src/tradingbotsuite/research_artifacts/__init__.py`
  - Exports the new context helpers.
- `tests/research_discovery/test_candidate_pack_bridge.py`
  - Adds regression coverage for unranked discovery candidates avoiding full
    cycle-gate calls.
  - Adds regression coverage for sampled large-run trial-record auditing.

## Real Artifact Check

Command:

```powershell
$env:PYTHONPATH='src'
@'
from pathlib import Path
from time import perf_counter
from tradingbotsuite.research_discovery.candidate_pack_bridge import evaluate_discovery_candidate_pack_eligibility

repo = Path.cwd()
discovery = repo / 'data/research/operator_runs/discovery_runs/exact-entry-sweep-btcusdt-candidate-depth-v1/discovery_run_manifest.json'
cycle = repo / 'data/research/operator_runs/historical_cycles/r105-btcusdt-durable-public-archive-candidate-depth-v1/run-historical-research-cycle-3f12dcdc483945cfa753e4eb00d42280/research_cycle_manifest.json'
start = perf_counter()
result = evaluate_discovery_candidate_pack_eligibility(discovery_manifest_path=discovery, cycle_manifest_path=cycle)
print(round(perf_counter() - start, 3), len(result.eligibility))
'@ | python -
```

Result:

```text
elapsed_seconds 9.234
rows 22560
eligible 0
global_reasons 0 []
research_candidate_gate_status:
blocked 22560
research_candidate_gate_reasons:
candidate_missing_from_rankings 22560
```

Important operational note: running the same command without
`$env:PYTHONPATH='src'` imported a stale installed package and reproduced the
slow behavior. The UI/server must be restarted from this checkout with
`PYTHONPATH=src` for the fix to apply.

## Validation

Passed:

```powershell
python -m compileall -q src\tradingbotsuite\research_artifacts\candidate_pack.py src\tradingbotsuite\research_discovery\candidate_pack_bridge.py
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_candidate_pack_bridge.py::test_bridge_does_not_run_full_cycle_gate_for_each_unranked_discovery_candidate tests\research_discovery\test_candidate_pack_bridge.py::test_bridge_samples_trial_record_audit_for_large_completed_discovery -q
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_candidate_pack_bridge.py::test_bridge_samples_trial_record_audit_for_large_completed_discovery tests\research_discovery\test_candidate_pack_bridge.py::test_bridge_rebases_migrated_discovery_manifest_required_outputs -q
```

Observed:

- new focused regressions: `2 passed`;
- sampled-audit plus migrated-path focused tests: `2 passed`;
- compileall: passed;
- real BTC eligibility evaluation: completed in `9.234` seconds.

## Final Assessment

The 16-hour run should be stopped and the UI/server restarted from the current
checkout with `PYTHONPATH=src`. After restart, clicking autopilot should no
longer stall in BTC candidate eligibility on the known exact-discovery run.

The expected current BTC candidate eligibility outcome is not a candidate-ready
claim. It is a fast research-only rejection artifact: all 22,560 BTC discovery
candidates are blocked because they do not map to the current historical-cycle
candidate rankings. `ISSUE-R104-001` remains open for empirical
candidate-ready evidence.
