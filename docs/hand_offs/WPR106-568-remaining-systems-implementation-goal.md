# WPR106-568 Remaining Systems Implementation Goal

Date: 2026-06-29
Audit:
`docs/audit/V2_DISCUSSION_CHANGES_FINAL_AUDIT_AND_REMAINING_ROADMAP_2026_06_29.md`

## Goal

Finish the post-PR6 autonomous research systems closure layer.

Most discussed systems are implemented and focused validation passed. The next
agent should not redo PR5, PR6, or WPR106-567. The next agent should prove the
whole system end to end, collect realistic benchmark evidence, broaden parity
coverage, and remove the last known scaling caveats.

## Suggested Packet

```text
docs/work_packets/WPR106-569-v2-autonomous-research-end-to-end-systems-closure.md
```

## Required Reads

- `AGENTS.md`
- `docs/RESEARCH_AGENT_QUICKSTART.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/PRODUCT_SCOPE.md`
- `docs/V2_DECISION_REGISTER.md`
- `docs/V2_NO_TOUCH_PATHS.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md`
- `docs/work_packets/WPR106-567-v2-autonomous-research-systems-layer.md`
- `docs/audit/V2_DISCUSSION_CHANGES_FINAL_AUDIT_AND_REMAINING_ROADMAP_2026_06_29.md`

Then run:

```powershell
$env:PYTHONPATH='src'; py -3.11 -m tradingbotsuite.v2.cli.main autonomy agent-context --repo-root .
```

## Implementation Priorities

### 1. End-To-End Workflow Smoke

Implement fixture and real-local-archive workflows:

```text
strategy spec
-> archive inventory
-> resolver
-> existing archive refs or DataGapRequest
-> columnar data load
-> fast metrics_only run
-> sampled reference audit
-> full replay plan
-> full replay verification
-> batched ledger read/write/export
-> feature-store discovery
```

No data collection. No generated evidence rewrite outside the packet output
root.

### 2. Real Benchmark Evidence

Run the existing benchmark scaffolding on realistic panels:

- smoke fixture;
- single-symbol 1m multi-month panel;
- multi-symbol 1m panel;
- repeated parameter-sweep style run;
- OF-derived feature panel if available.

Record reference runtime, fast runtime, speedup ratio, data load time, artifact
write time, memory peak, parity status, artifact mode, panel size, instrument
count, timeframe, and hardware/runtime context.

Do not claim speedup unless complete measured evidence supports it.

### 3. Fast-Lane Parity Matrix

Expand parity coverage for current strategy families and execution modes:

- rank/cross-sectional;
- funding carry;
- momentum/reversion;
- volatility-filtered strategies;
- multi-instrument panels;
- close/mark/oracle/next-bar-open price bases;
- strict/lenient spread policies;
- full/summary/metrics-only artifact modes.

Parity failures must block leaderboard acceptance until investigated.

### 4. OF Non-Monotonic Streaming Hardening

If profiling shows OF materialization is the bottleneck, replace the remaining
full-sort fallback for very large non-monotonic inputs with bounded spill,
chunked merge-sort, or partitioned processing.

Keep deterministic hashes and feature-store discoverability.

### 5. Review And PR Hygiene

The current WPR106-567 worktree is uncommitted. Before finalizing:

- inspect dirty/untracked files;
- ensure no generated evidence/archive data is accidentally included;
- run focused validation;
- run full `tests\v2 -q` if scope and time allow;
- stage only intended docs/source/tests;
- commit/open PR only if requested by owner.

## Constraints

- Do not collect data by default.
- Do not add venues proactively.
- Do not weaken PR5/PR6/WPR106-567 math or boundary fixes.
- Do not remove the Python/reference engine.
- Do not touch live, paper, order-placement, sizing, promotion,
  candidate-pack, runtime-mode, secret, local-state, generated-evidence,
  ledger data, Lead Book data, or archive data paths unless a new packet
  explicitly allows it.
- Ignore the post-PR6 report's trade-frequency and losing-month section unless
  the owner gives a new decision.

## Success Criteria

- A strategy can be resolved through inventory/resolver and either uses existing
  archive refs or emits bounded `DataGapRequest` objects.
- A real local archive workflow reaches fast metrics-only execution and sampled
  reference audit.
- At least one light run has a full replay plan and verified full replay.
- Benchmark evidence exists but speedup remains unclaimed unless fully
  supported.
- Ledger batching and feature-store discovery are exercised in the workflow.
- All touched validation passes.

## Copy-Paste Goal

```text
Goal: finish post-PR6 autonomous research systems closure.

Do not redo completed PR5/PR6/WPR106-567 work. Prove the whole system end to
end: archive inventory, resolver, DataGapRequest, existing archive refs,
columnar load, fast metrics-only execution, sampled reference audit, full
replay verification, batched ledger handling, feature-store discovery, and
real benchmark evidence.

Do not collect data, add venues by default, rewrite generated evidence, weaken
math fixes, remove reference-engine authority, or touch live/paper/order/
sizing/promotion/candidate/runtime/secret/local-state paths.

Success means agents can test from existing archive when possible, emit bounded
gap requests when not, run large sweeps safely, replay promising results in full
artifact mode, and avoid speed claims without complete benchmark evidence.
```
