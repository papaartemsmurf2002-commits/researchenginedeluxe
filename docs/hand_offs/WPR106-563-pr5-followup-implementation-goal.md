# WPR106-563 PR5 Follow-Up Implementation Goal

Date: 2026-06-29
Basis:
`C:/Users/papaa/Downloads/PR5_RECOMMENDATION_VALIDATION_REPORT.md`

## Report Assessment

Treat the PR #5 validation report as directionally correct and worth pursuing,
with one explicit correction:

- Ignore the report section about trade-frequency and losing-month validation.
  Do not use that section as implementation authority.

PR #5 appears to have already handled the main math and policy work:

- USD account-notional capacity participation;
- `account_notional_usd=10000.0` propagation;
- `5` bps default spread fallback;
- explicit spread-unit preference with legacy lenient fallback;
- funding `0.0` score handling;
- monthly validation folds with `full_window` as diagnostic;
- cost-stress derivation from the base run for linear stress scenarios;
- basic Arrow predicate pushdown;
- worker stale-claimed handling and transaction-locked claiming;
- sidecar/index improvements for ledger and data-manifest duplicate checks.

The remaining useful work is mostly performance, storage scale, and accepted
research strictness. The next implementation should finish what PR #5 started
without weakening its corrected math.

## Goal For Next Implementation Agent

Implement the next scaling phase for the autonomous research engine:

```text
Build a reference-preserving fast research path that keeps the current Python
engine as the correctness reference, adds a columnar/array data path, introduces
a fast vectorized backtest lane with parity tests, and improves append-heavy
storage so autonomous sweeps can scale without rewriting large tables.
```

Suggested new implementation packet:

`docs/work_packets/WPR106-564-v2-autonomous-research-fast-engine-and-storage-scale.md`

## Required Reads

Read these before coding:

- `AGENTS.md`
- `docs/RESEARCH_AGENT_QUICKSTART.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/PRODUCT_SCOPE.md`
- `docs/V2_DECISION_REGISTER.md`
- `docs/V2_NO_TOUCH_PATHS.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md`
- `docs/work_packets/WPR106-562-v2-autonomous-research-math-policy-and-speed-implementation.md`
- `docs/audit/V2_AUTONOMOUS_RESEARCH_MATH_PERFORMANCE_FINAL_ROADMAP_2026_06_29.md`

Then run:

```powershell
$env:PYTHONPATH='src'; py -3.11 -m tradingbotsuite.v2.cli.main autonomy agent-context --repo-root .
```

Use that output as the current research-boundary truth.

## Implementation Priorities

### 1. Fast Array Backtest Engine

Priority: highest.

Add a new fast path while preserving the current row/Python engine as the
reference implementation.

Target design:

```text
reference_engine_python = current behavior and artifact contract
fast_vectorized_engine = optional array/columnar lane

panel arrays: timestamp x instrument x field
signals: timestamp x instrument
target_weights: timestamp x instrument
applied_weights: previous target weights
returns: timestamp x instrument
turnover: abs(target_weight_t - target_weight_t-1)
costs: vectorized fee/spread/slippage/impact/funding terms
```

Requirements:

- Exact same research-only boundary flags.
- Same run manifest/artifact schema or a clearly versioned compatible schema.
- Same cost and capacity math as PR #5.
- Same monthly fold validation semantics.
- Same `next_bar_open` causality semantics.
- Parity tests against the reference engine on small and medium fixtures.
- Documented numerical tolerance before accepting tiny differences.

Do not remove the reference engine.

### 2. Columnar Data Path Into The Fast Engine

Priority: high.

PR #5 added Arrow scanner filtering, but the downstream path still largely
returns Python row dictionaries.

Add a data-slice interface that can expose:

- existing row output for the reference engine;
- Arrow table output;
- optional Polars or NumPy panel output for the fast engine.

Requirements:

- Preserve current temporal-policy and manifest checks.
- Keep column projection and timestamp/instrument/timeframe predicate pushdown.
- Avoid converting large panels to `list[dict]` before the fast engine.
- Add tests that prove row and columnar outputs contain equivalent data.

### 3. Part-Based Ledger And Manifest Append

Priority: medium/high before large autonomous sweeps.

PR #5 added sidecar indexes and duplicate-check improvements, but the canonical
append path can still rewrite larger Parquet tables.

Implement or stage a part-based append design:

```text
ledger/
  parts/
    ledger_part_000001.parquet
    ledger_part_000002.parquet
  append_log.jsonl
  compacted/current.parquet
  index/
```

Requirements:

- Append new rows without rewriting the full canonical table.
- Preserve deterministic run IDs and duplicate protection.
- Provide a compaction path.
- Make leaderboard scans read either parts or compacted current state.
- Keep current small-repo behavior compatible.

The same pattern can be applied to high-churn request manifests if scope allows.

### 4. Accepted-Research Spread Unit Strictness

Priority: medium.

PR #5 improved spread handling but still allows legacy magnitude guessing when
units are absent.

Keep lenient fallback for sandbox and legacy paths, but add an accepted-research
strict mode:

- accepted/high-confidence validation should require `spread_bps` or explicit
  spread units;
- ambiguous raw spread without units should produce a warning or blocker,
  depending on validation tier;
- manifests should record whether spread was explicit, converted, or inferred.

Do not weaken the `5` bps default fallback.

### 5. Chunked OF Materialization

Priority: medium later, only if OF-heavy strategies are active.

Do not treat this as more urgent than the fast array engine.

Recommended design:

```text
partition by provider / family / symbol / timeframe / month
write RecordBatch/Parquet chunks
dedupe inside partition
materialize OF features with process workers
output compact features as Parquet
cache by raw_sha + materializer_version + bucket_seconds
```

Requirements:

- Avoid treating large archives as one in-memory stream.
- Prefer Parquet feature output over JSONL for downstream research.
- Preserve source-family naming.

### 6. Venue Probe Expansion

Priority: low/medium.

Add only after the core fast engine and storage scale work is stable.

Suggested order:

1. Bitget history candles probe.
2. Bybit OI/funding pagination proof.
3. OKX pagination confirmation.
4. MEXC/Gate basic candle/funding/OI probes.

Keep these as probe lanes. Do not create uncontrolled archive bloat.

### 7. GPU Acceleration

Priority: low.

Do not start with GPU work. GPU only becomes useful after the CPU
Arrow/NumPy/Polars path exists and exposes large matrix workloads.

## Explicit Non-Goals

- Do not change trade-frequency or losing-month policy from this handoff.
- Do not weaken PR #5 math fixes.
- Do not rewrite WPR106-556 generated evidence unless a new packet explicitly
  scopes a bounded evidence refresh.
- Do not touch live, paper, order-placement, sizing, promotion,
  candidate-pack, runtime-mode, secret, or local-state paths.
- Do not remove the current reference engine.
- Do not attempt GPU acceleration before the array/columnar CPU path is proven.

## Suggested Validation

Minimum after implementation:

```powershell
py -3.11 -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_backtest_engine_phase12.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_backtest_data_phase9.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_cost_models_phase12.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_validation_phase14.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_validation_worker_phase32.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_ledger_phase13.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_strategy_specs_phase10.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_workers_phase7.py -q
git diff --check
```

Broaden to:

```powershell
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2 -q
```

when artifact schemas, data slices, ledger storage, or engine outputs change.

Add dedicated parity tests:

- reference engine versus fast engine metrics;
- reference engine versus fast engine equity curve;
- reference engine versus fast engine trades and positions where deterministic;
- row data slice versus columnar data slice;
- part-based ledger append versus existing leaderboard and duplicate behavior.

## Success Criteria

The next implementation is successful when:

- the fast engine can run at least one representative fixture with metrics that
  match the reference engine within documented tolerance;
- the loader can provide columnar data without forcing `list[dict]` conversion;
- ledger append can add runs without rewriting the full canonical table in the
  common append path;
- accepted-research spread-unit strictness exists without breaking legacy
  sandbox compatibility;
- all touched paths preserve research-only, observe-only,
  `promotion_ready=false` semantics;
- tests and diff checks pass.

## Final Prompt For The Implementation Agent

```text
You are continuing after PR #5 and WPR106-562 in:
C:\Users\papaa\Music\researchenginedeluxe

Your goal is to finish the remaining PR #5 follow-up work that is still worth
pursuing: fast array/vectorized engine, columnar data path, append-part ledger
storage, accepted-research spread-unit strictness, and later OF/venue scaling.

Ignore the PR #5 report's trade-frequency and losing-month section. Do not
change those policies unless the owner gives a new explicit decision.

Start by reading:
- AGENTS.md
- docs/RESEARCH_AGENT_QUICKSTART.md
- docs/ORCHESTRATOR_STAGE_LEDGER.md
- docs/PRODUCT_SCOPE.md
- docs/V2_DECISION_REGISTER.md
- docs/V2_NO_TOUCH_PATHS.md
- docs/audit/V2_AUDIT_INDEX.md
- docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md
- docs/work_packets/WPR106-562-v2-autonomous-research-math-policy-and-speed-implementation.md
- docs/hand_offs/WPR106-563-pr5-followup-implementation-goal.md

Then create a new implementation work packet, suggested:
docs/work_packets/WPR106-564-v2-autonomous-research-fast-engine-and-storage-scale.md

Keep the current Python backtest engine as the correctness reference. Add an
optional fast array/columnar path with parity tests. Do not weaken PR #5 math,
do not remove monthly folds, do not alter account-notional capacity math, and
do not touch live/paper/order/sizing/promotion/candidate/runtime/secret paths.

Implement in this order:
1. parity fixtures and baseline tests;
2. columnar data-slice output;
3. fast vectorized backtest lane;
4. part-based ledger/manifest append path;
5. accepted-research spread-unit strict mode;
6. chunked OF materialization only if scoped and time remains;
7. venue probes later, after engine/storage scale.

Run focused tests and broaden to tests\v2 -q if shared contracts or artifacts
change.
```
