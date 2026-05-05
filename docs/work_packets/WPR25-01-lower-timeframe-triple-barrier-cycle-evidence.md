# WPR25-01 Lower-Timeframe Triple-Barrier Cycle Evidence

Status: closed
Owner: Codex Research Agent
Stage: Stage R25 lower-timeframe triple-barrier cycle evidence
Opened: 2026-05-04
Closed: 2026-05-04

## Objective

Expose lower-timeframe triple-barrier exits as explicit historical research-cycle candidate policies using fixture-backed lower-timeframe data. The reference engine already supports lower-timeframe ordering; this packet wires that capability into historical cycles with provenance and fail-closed behavior.

## Allowed paths

- `docs/KNOWN_ISSUES.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/work_packets/WPR25-01-lower-timeframe-triple-barrier-cycle-evidence.md`
- `docs/stage_reports/STAGE_R25_LOWER_TIMEFRAME_TRIPLE_BARRIER_CYCLE_EVIDENCE_REPORT.md`
- `src/tradingbotsuite/data/historical_fixture_pack.py`
- `src/tradingbotsuite/research_cycle/spec.py`
- `src/tradingbotsuite/research_cycle/runner.py`
- `src/tradingbotsuite/backtesting/vector_engine.py`
- `tests/backtesting/test_vector_engine_matches_reference.py`
- `tests/contracts/test_historical_fixture_pack_contract.py`
- `tests/contracts/test_research_cycle_contract.py`
- `tests/historical/test_full_cycle_local_fixture_pack.py`
- `tests/historical/test_full_cycle_synthetic.py`
- `tests/live/test_preflight.py`

## Non-goals

- No vector lower-timeframe implementation.
- No live, paper, shadow, testnet, canary, promotion, order-placement, or capital allocation work.
- No default behavior change; fixed holding remains the default exit policy.
- No candidate acceptance or promotion-ready claim from synthetic evidence.

## Implementation plan

1. Add lower-timeframe dataset provenance to cycle data specs and fixture pack validation payloads.
2. Allow explicit `triple_barrier` and `triple_barrier_atr` exit policies in historical research-cycle specs with positive target/stop returns.
3. Pass lower-timeframe dataset paths into aggregate, split, and stress `BacktestSpec` runs only when required by lower-timeframe exit policies.
4. Fail closed when a lower-timeframe exit policy is configured without usable lower-timeframe data.
5. Record lower-timeframe provenance in cycle manifests, candidate-space manifests, rankings/backtest index, and backtest manifests.
6. Preserve vector fallback semantics: explicit vector rejects unsupported lower-timeframe scope; `auto` falls back to reference with evidence.

## Exit criteria

- Default cycles remain fixed holding and do not require lower-timeframe data.
- Explicit triple-barrier cycles use fixture-backed lower-timeframe data and produce lower-timeframe sequence proof in trades.
- Missing lower-timeframe data fails closed before producing misleading evidence.
- Vector `auto` fallback evidence is recorded for lower-timeframe triple-barrier candidates.
- Focused contracts, historical tests, vector boundary tests, live preflight, and diff check pass.

## Completion summary

- Added lower-timeframe dataset provenance to historical cycle data specs, fixture-pack validation payloads, candidate-space manifests, cycle manifests, rankings, and backtest index rows.
- Allowed explicit `triple_barrier` and `triple_barrier_atr` research-cycle exit policies with required positive target and stop returns.
- Routed lower-timeframe dataset paths into aggregate, split, and cost-stress `BacktestSpec` runs only for lower-timeframe exit policies.
- Added early fail-closed checks for missing, unreadable, empty, or schema-invalid lower-timeframe datasets.
- Preserved fixed-holding defaults and recorded default-cycle evidence that lower-timeframe sequencing is not required or used.
- Preserved vector scope boundaries: explicit vector remains unsupported for lower-timeframe runs, while `auto` falls back to the reference engine with artifact evidence.
- Kept all outputs research-only, observe-only, and `promotion_ready: false`.

## Validation evidence

```powershell
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts/test_historical_fixture_pack_contract.py tests/contracts/test_research_cycle_contract.py tests/backtesting/test_vector_engine_matches_reference.py tests/historical/test_full_cycle_local_fixture_pack.py tests/historical/test_full_cycle_synthetic.py tests/live/test_preflight.py -q
git diff --check
```

Results: compile passed, contracts passed with 75 tests, WPR25 packet tests passed with 85 tests, and `git diff --check` reported line-ending warnings only.
