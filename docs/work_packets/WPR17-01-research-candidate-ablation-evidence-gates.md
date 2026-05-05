# WPR17-01 Research Candidate Ablation And Stress Evidence Gates

Status: closed
Owner: Codex Research Agent
Stage: Stage R17 research candidate ablation and stress evidence gates
Opened: 2026-05-04
Closed: 2026-05-04

## Objective

Make research candidate pack eligibility require candidate-tied feature-ablation evidence and the full research stress scenario set instead of only requiring that an `ablation_report.json` file and a few cost-stress rows exist.

Passing candidates must either have a complete baseline feature-set status with no optional feature claim, or, for optional feature claims such as WT3D, have an explicit comparator feature-set row proving the candidate does not depend on the optional feature family. All evidence remains research-only, observe-only, and non-promotable.

Passing candidates must also carry complete stress evidence for base costs, 2x slippage, 3x slippage, adverse funding, wide spread, missing optional context, high volatility, low volatility, trend-only, range-only, and shock/transition-only scenarios.

## Allowed paths

- `docs/KNOWN_ISSUES.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/work_packets/WPR17-01-research-candidate-ablation-evidence-gates.md`
- `docs/stage_reports/STAGE_R17_RESEARCH_CANDIDATE_ABLATION_EVIDENCE_GATES_REPORT.md`
- `src/tradingbotsuite/research_cycle/runner.py`
- `src/tradingbotsuite/research_artifacts/candidate_pack.py`
- `tests/contracts/test_research_cycle_contract.py`
- `tests/historical/test_full_cycle_synthetic.py`
- `tests/historical/test_full_cycle_local_fixture_pack.py`
- `tests/research_artifacts/test_candidate_pack.py`
- `tests/live/test_preflight.py`

## Non-goals

- No live, paper, shadow, testnet, canary, promotion, order-placement, or capital allocation work.
- No new data ingestion or network fetching.
- No vectorized engine or optimizer rewrite in this packet.
- No acceptance of feature claims from synthetic or incomplete evidence.

## Implementation plan

1. Add candidate-level feature-ablation status fields to full-cycle rankings.
2. Expand the full-cycle `ablation_report.json` with candidate-tied ablation rows.
3. Expand the cost-stress scenario registry to the full research set and write scenario IDs/statuses into `metrics_by_cost_stress.parquet`.
4. Require candidate-pack gates to reject missing, failed, placeholder, or incomplete ablation/stress evidence.
5. Preserve pass eligibility for baseline no-optional-claim feature sets when all other gates pass.
6. Add tests proving complete baseline feature-set evidence can pass, WT/optional feature claims require comparators, missing/failed ablation rows fail closed, and base-only/four-scenario stress evidence fails closed.

## Exit criteria

- Ranking rows include ablation evidence status, comparator feature set where applicable, ablation deltas, and pass/fail state.
- `ablation_report.json` includes candidate-tied rows that can be audited independently of rankings.
- Candidate packs cannot pass if candidate ablation evidence is missing, failed, or unsupported.
- `metrics_by_cost_stress.parquet`, rankings, and gate reports expose the full required scenario set and fail closed when any scenario is missing or unevaluated.
- Existing WPR16 complete fixture pass path still writes a research-only candidate pack.
- Synthetic/incomplete evidence remains blocked.
- Focused historical/research-artifact tests, contracts, live preflight, compileall, and diff checks pass.

## Completion evidence

- Ranking rows now include candidate-level feature-ablation fields: required/pass flags, evidence status, comparator feature set/candidate, deltas, and failure reasons.
- `ablation_report.json` now includes candidate-tied rows and the candidate-pack durable gate independently validates them.
- The full research stress set now includes base costs, 2x slippage, 3x slippage, adverse funding, wide spread, missing optional context, high volatility, low volatility, trend-only, range-only, and shock/transition-only scenarios.
- `metrics_by_cost_stress.parquet` now records scenario group, filters/transforms, spread, source rows, dataset hash, and status.
- Candidate-pack gates reject missing ablation rows, failed ablation status, base-only/four-scenario stress evidence, missing required stress scenarios, unevaluated stress rows, and missing stress backtest manifests.
- Complete non-synthetic fixture evidence still writes a research-only, observe-only, `promotion_ready: false` pack; synthetic/incomplete evidence stays blocked.

Validation:

```powershell
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/research_artifacts/test_candidate_pack.py -q
$env:PYTHONPATH='src'; python -m pytest tests/historical -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
$env:PYTHONPATH='src'; python -m pytest tests/live/test_preflight.py -q
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite -q
git diff --check
```

Results:

- `compileall`: passed.
- `tests/research_artifacts/test_candidate_pack.py`: 23 passed.
- `tests/historical`: 10 passed.
- `tests/contracts`: 59 passed.
- `tests/live/test_preflight.py`: 24 passed.
- `tests/tradingbotsuite`: 273 passed.
- `git diff --check`: passed with existing LF-to-CRLF warnings only.
