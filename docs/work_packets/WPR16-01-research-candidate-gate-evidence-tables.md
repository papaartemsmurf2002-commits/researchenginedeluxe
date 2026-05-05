# WPR16-01 Research Candidate Gate And Evidence Tables

Status: closed
Owner: Codex Research Agent
Stage: Stage R16 research candidate gate evidence tables
Opened: 2026-05-04
Closed: 2026-05-04

## Objective

Make full-cycle research rankings and evidence tables truthful enough to support research-only candidate-pack eligibility when complete non-synthetic evidence exists, while failing closed for synthetic, incomplete, aggregate-only, side-less, regime-less, comparator-less, stress-incomplete, or unstable evidence.

The runner must stop writing aggregate-only side/regime evidence as if it were full validation evidence, and it must stop hard-coding every candidate ranking as rejected when the candidate evidence actually satisfies the research-only gate. Passing the gate is not live readiness and must still produce `research_only`, `observe_only`, and `promotion_ready: false` artifacts.

## Allowed paths

- `docs/KNOWN_ISSUES.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/work_packets/WPR16-01-research-candidate-gate-evidence-tables.md`
- `docs/stage_reports/STAGE_R16_RESEARCH_CANDIDATE_GATE_EVIDENCE_TABLES_REPORT.md`
- `src/tradingbotsuite/research_cycle/runner.py`
- `src/tradingbotsuite/research_artifacts/candidate_pack.py`
- `tests/contracts/test_research_cycle_contract.py`
- `tests/historical/test_full_cycle_synthetic.py`
- `tests/historical/test_full_cycle_local_fixture_pack.py`
- `tests/research_artifacts/test_candidate_pack.py`
- `tests/live/test_preflight.py`

## Non-goals

- No live, paper, shadow, testnet, canary, promotion, order-placement, or capital allocation work.
- No fabrication of real BTC evidence when a validated non-synthetic fixture is missing.
- No large dataset ingestion or network fetching.
- No vectorized engine work.
- No full optimizer rewrite, adaptive mesh refinement, or new benchmark tier in this packet.

## Implementation plan

1. Inspect full-cycle ranking, metrics-by-side/regime, durable gate, and candidate-pack eligibility contracts.
2. Replace aggregate-only side/regime metric outputs with real per-candidate evidence derived from backtest metrics/trades where available.
3. Add a fail-closed research gate evaluator for full-cycle candidates covering non-synthetic fixture provenance, split evidence, side evidence, regime evidence, cost/stress evidence, comparator evidence, stability evidence, and artifact safety.
4. Let ranking rows set `research_gate_passed` / `research_pack_eligible` only when the gate evaluator passes; otherwise write explicit rejection reasons.
5. Keep candidate packs research-only and non-promotable, and keep synthetic/incomplete evidence rejected.
6. Add tests for one complete research-only fixture-backed pass path and several fail-closed paths.

## Exit criteria

- Full-cycle `metrics_by_side` and `metrics_by_regime` are real per-candidate evidence tables, not duplicated aggregate ranking rows.
- Ranking rows include truthful gate fields and reasons, and no longer hard-code every candidate as rejected independent of evidence.
- Candidate-pack eligibility can pass only from non-synthetic fixture-backed complete evidence and remains `research_only`, `observe_only`, `promotion_ready: false`.
- Synthetic/incomplete/side-less/regime-less/stress-incomplete/stability-incomplete evidence fails closed.
- Focused historical/research-artifact tests, contracts, live preflight, compileall, and diff checks pass.

## Risk controls

- Candidate gate pass means research pack eligibility only, not promotion or live readiness.
- Do not loosen live/preflight/promotion boundaries.
- Do not use missing fixture data as evidence.
- Update `docs/KNOWN_ISSUES.md` if a blocking risk is discovered and cannot be fixed in this packet.

## Completion evidence

- Full-cycle `metrics_by_side` is derived from candidate trade rows and includes side-specific trade count, expectancy, net return, hit rate, backtest manifest, trades path, and trades hash.
- Full-cycle `metrics_by_regime` is derived from backtest `split_by_regime` metrics and rejects aggregate-only placeholder labels for pack eligibility.
- Ranking rows now include side/regime/stress/split-dominance evidence fields and can set `research_gate_passed` only for non-synthetic fixture-backed complete evidence.
- Candidate packs remain `research_only`, `observe_only`, and `promotion_ready: false`, with no live, paper, shadow, testnet, order-placement, or capital-allocation scope.
- Synthetic, aggregate-only, side-less, regime-less, incomplete-stress, incomplete-split, unstable, and comparator-failing candidates fail closed with explicit reasons.

Validation:

```powershell
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
$env:PYTHONPATH='src'; python -m pytest tests/historical -q
$env:PYTHONPATH='src'; python -m pytest tests/research_artifacts -q
$env:PYTHONPATH='src'; python -m pytest tests/live/test_preflight.py -q
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite -q
git diff --check
```

Results:

- `compileall`: passed.
- `tests/contracts`: 59 passed.
- `tests/historical`: 10 passed.
- `tests/research_artifacts`: 21 passed.
- `tests/live/test_preflight.py`: 24 passed.
- `tests/tradingbotsuite`: 273 passed.
- `git diff --check`: passed with existing LF-to-CRLF warnings only.
