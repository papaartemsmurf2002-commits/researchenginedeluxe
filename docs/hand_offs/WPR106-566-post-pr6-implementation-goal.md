# WPR106-566 Post-PR6 Implementation Goal

Date: 2026-06-29
Assessment:
`docs/audit/V2_POST_PR6_RECOMMENDATIONS_CRITICAL_ASSESSMENT_2026_06_29.md`
Input report: `C:/Users/papaa/Downloads/POST_PR6_RECOMMENDATIONS.md`

## Goal

Continue after PR #6 by making autonomous research agents archive-aware before
they collect, materialize, or test anything.

The next implementation agent should build the archive inventory and
strategy-data requirement resolver first. This is more urgent than more venue
expansion because PR6 already added the first fast lane, part-backed storage,
strict spread mode, OF Parquet parts, and bounded Bybit/OKX pagination helpers.

## Ignore This From The Report

Per owner instruction, ignore the report section about trade-frequency and
losing-month validation. Do not change those policies from this handoff.

## Recommended Packet

Create a new implementation work packet:

```text
docs/work_packets/WPR106-567-v2-autonomous-research-systems-layer.md
```

Suggested objective:

```text
Implement a deterministic archive inventory service, CLI, strategy
data-requirement resolver, structured DataGapRequest flow, fast-lane policy
metadata, artifact-light run modes, batched ledger parts, feature-store catalog,
and research-only collector templates so agents can prove whether required data
already exists before collecting, materializing, sweeping, or writing adapters.
```

## Required Reads

Read these first:

- `AGENTS.md`
- `docs/RESEARCH_AGENT_QUICKSTART.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/PRODUCT_SCOPE.md`
- `docs/V2_DECISION_REGISTER.md`
- `docs/V2_NO_TOUCH_PATHS.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md`
- `docs/work_packets/WPR106-564-v2-autonomous-research-fast-engine-and-storage-scale.md`
- `docs/work_packets/WPR106-565-v2-of-materialization-and-venue-probe-scaling.md`
- `docs/audit/V2_POST_PR6_RECOMMENDATIONS_CRITICAL_ASSESSMENT_2026_06_29.md`

Then run:

```powershell
$env:PYTHONPATH='src'; py -3.11 -m tradingbotsuite.v2.cli.main autonomy agent-context --repo-root .
```

Use the output as the current research-boundary truth.

## Primary Implementation Scope

### 1. Archive Inventory

Add a new package:

```text
src/tradingbotsuite/v2/archive_inventory/schemas.py
src/tradingbotsuite/v2/archive_inventory/service.py
src/tradingbotsuite/v2/archive_inventory/__init__.py
```

Inventory records should expose at least:

```text
instrument_id
venue
source_id
family
timeframe
start_ts
end_ts
row_count
coverage_ratio
coverage_min
source_file_ids
archive_snapshot_id
coverage_report_id
universe_snapshot_id
evidence_scope
accepted_research_evidence_allowed
native_to_hyperliquid
proxy_to_hyperliquid
data_quality_status
known_gap_reasons
research_only
observe_only
promotion_ready
```

The service should read existing archive manifests, coverage reports, and
snapshot metadata. It must not collect data.

### 2. Archive Inventory CLI

Add CLI entry points under the existing v2 CLI style.

Target commands can be equivalent to:

```powershell
$env:PYTHONPATH='src'; py -3.11 -m tradingbotsuite.v2.cli.main archive-inventory --summary
$env:PYTHONPATH='src'; py -3.11 -m tradingbotsuite.v2.cli.main archive-inventory --symbol BTC --family bars --timeframe 1m
$env:PYTHONPATH='src'; py -3.11 -m tradingbotsuite.v2.cli.main archive-inventory --missing-for-strategy configs\strategies\example.json
```

Use the repo's existing CLI conventions rather than inventing a separate
command runner.

### 3. Strategy Data Requirement Resolver

Add a resolver that accepts:

```text
strategy_spec
target instruments/universe
requested time range
evidence mode
```

It should return:

```text
ready
usable_instruments
missing_instruments
missing_fields
missing_families
missing_time_ranges
usable_archive_refs
required_feature_materializations
recommended_collection_tasks
do_not_collect_reason
data_gap_requests
```

Important behavior:

- If data exists, tell the agent to use it.
- If data is missing, identify the narrow missing family/instrument/time range.
- If collection is unnecessary, return a clear `do_not_collect_reason`.
- If the request touches lockbox or unsupported evidence mode, fail closed.
- Do not write collectors in this packet.

### 4. DataGapRequest

Add a structured schema for missing data:

```text
strategy_id
requested_family
requested_fields
instrument_ids
venue_preference
start_ts
end_ts
reason
existing_archive_refs_checked
missing_coverage_report_ids
suggested_collector
estimated_size_bytes
priority
research_only
observe_only
promotion_ready
candidate_evidence=false
live_signal=false
paper_signal=false
sizing_instruction=false
order_placement_instruction=false
runtime_mode_change=false
```

This object is a request for manual/agent review, not permission to collect
data automatically.

### 5. Archive-First Agent Rule

Update the current research-agent docs so future agents follow this rule:

```text
Before collecting data or writing a new adapter, query archive inventory and
the data-requirement resolver. If sufficient data exists, use it. If data is
missing, collect only the missing instrument/family/time range after a scoped
work packet allows it. Do not add venues proactively.
```

Suggested docs to update only if allowed by the new packet:

- `AGENTS.md`
- `docs/RESEARCH_AGENT_QUICKSTART.md`
- current handoff docs

## Suggested Allowed Paths For WPR106-567

Use only the paths actually needed, but likely include:

- `docs/work_packets/WPR106-567-v2-archive-inventory-and-data-requirement-resolver.md`
- `src/tradingbotsuite/v2/archive_inventory/**`
- `src/tradingbotsuite/v2/cli/main.py`
- `src/tradingbotsuite/v2/backtest_data/**` if reusing manifest helpers requires small exports
- `src/tradingbotsuite/v2/strategy_specs/**` if field-requirement extraction needs helper exports
- `tests/v2/test_archive_inventory_phase*.py`
- `tests/v2/test_data_requirement_resolver_phase*.py`
- `AGENTS.md` and `docs/RESEARCH_AGENT_QUICKSTART.md` only for archive-first rule docs

Do not include source or generated-data paths merely for convenience.

## Follow-Up Packets After WPR106-567

After inventory/resolver exists, pursue these in order:

1. Fast-lane rollout and reference parity audit policy.
2. `artifact_mode = full | summary | metrics_only` plus replay-to-full.
3. Ledger part batching with configurable max rows/size per part.
4. Feature-store catalog plus streaming/parallel OF materialization.
5. Collector adapter template.
6. Optional venue probes only when resolver proves missing data.

## Validation Baseline

Minimum for WPR106-567:

```powershell
py -3.11 -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_backtest_data_phase9.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_strategy_specs_phase10.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_autonomy_agent_context_phase79.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\contracts -q
git diff --check
```

Add new focused inventory/resolver tests and run them explicitly. Broaden to
`tests\v2 -q` if CLI, archive manifest contracts, or strategy spec contracts
change broadly.

## Stop Conditions

Stop and document a blocker if:

- inventory cannot distinguish accepted-research evidence from sandbox or
  diagnostic data;
- resolver would silently approve lockbox-overlapping data;
- resolver cannot explain which exact field/family/time slice is missing;
- implementation would require collecting data in this packet;
- implementation would touch live, paper, order-placement, sizing, promotion,
  candidate-pack, runtime-mode, secret, local-state, generated-evidence, ledger,
  Lead Book, or archive data paths outside the new packet.

## Prompt For The Next Agent

```text
You are continuing after PR #6 in:
C:\Users\papaa\Music\researchenginedeluxe

Your task is WPR106-567: implement archive inventory and a strategy
data-requirement resolver so future agents know what data already exists before
they collect or write adapters.

Read:
- AGENTS.md
- docs/RESEARCH_AGENT_QUICKSTART.md
- docs/ORCHESTRATOR_STAGE_LEDGER.md
- docs/PRODUCT_SCOPE.md
- docs/V2_DECISION_REGISTER.md
- docs/V2_NO_TOUCH_PATHS.md
- docs/audit/V2_AUDIT_INDEX.md
- docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md
- docs/work_packets/WPR106-564-v2-autonomous-research-fast-engine-and-storage-scale.md
- docs/work_packets/WPR106-565-v2-of-materialization-and-venue-probe-scaling.md
- docs/audit/V2_POST_PR6_RECOMMENDATIONS_CRITICAL_ASSESSMENT_2026_06_29.md
- docs/hand_offs/WPR106-566-post-pr6-implementation-goal.md

Ignore the post-PR6 report section about trade-frequency and losing-month
validation. Do not change those policies.

Create:
docs/work_packets/WPR106-567-v2-archive-inventory-and-data-requirement-resolver.md

Implement:
1. archive inventory schemas/service;
2. archive inventory CLI;
3. strategy data-requirement resolver;
4. structured DataGapRequest;
5. archive-first agent rule in docs.

Do not collect data, add venues by default, rewrite generated evidence, compact
ledgers, update Lead Book rows, or touch live/paper/order/sizing/promotion/
candidate/runtime/secret/local-state paths.

Success means a strategy spec can be checked against the local archive and the
agent receives either usable archive refs or a precise, bounded DataGapRequest.
```
