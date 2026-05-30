# Stage R106 Discovery Lead Materialization Lane Report

Work packet:
`docs/work_packets/WPR106-30-discovery-lead-materialization-lane.md`

Date: 2026-05-30

## Summary

WPR106-30 adds the first bounded lane that turns exact-discovery KNN leads into
deterministic materialization descriptors. This is deliberately not a
candidate-pack or ranking writer. The lane preserves source discovery evidence,
assigns stable materialized candidate IDs, emits candidate descriptor JSONL, and
records every downstream gate still required before a lead can be treated as a
cycle/backtest/ranking-equivalent candidate.

Subagents inspected the discovery and research-cycle interfaces before
implementation. Both inspections agreed on the safety boundary: WPR106-30 may
describe how discovery leads should be validated next, but must not write
`candidate_rankings.parquet`, `candidate_gate_report.parquet`, `pack_eligible:
true`, or `promotion_ready: true` without full runner-equivalent evidence.

## Code Changes

Added:

- `src/tradingbotsuite/research_discovery/discovery_lead_materialization.py`
- `tests/research_discovery/test_discovery_lead_materialization.py`

Updated:

- `src/tradingbotsuite/research_discovery/__init__.py`

The new module provides:

- `DiscoveryLeadMaterializationSpec`
- `materialize_discovery_leads_from_manifest()`
- `write_discovery_lead_materialization_artifacts()`
- `validate_discovery_lead_materialization_manifest()`

## Artifact Contract

Each materialization run writes:

- `discovery_lead_materialization_manifest.json`
- `materialized_discovery_leads.parquet`
- `materialization_candidate_specs.jsonl`

The manifest and rows preserve:

- source discovery manifest path and SHA-256;
- source interesting-candidates ledger SHA-256;
- source trial ID, trial index, attempt ID, discovery candidate ID, and
  immutable trial `record_sha256`;
- `prediction_signature_hash`;
- `entry_event_signature_hash`;
- `effective_trial_key`;
- deterministic `materialized_candidate_id`;
- candidate descriptor fields for the frozen KNN entry lead family;
- explicit required downstream gates.

Required downstream gates are:

- `cycle_backtest_required`
- `cycle_ranking_required`
- `research_candidate_gate_required`
- `baseline_comparator_required`
- `no_trade_comparator_required`
- `exit_lab_required`
- `multiple_testing_required`
- `validation_floor_required`
- `candidate_pack_eligibility_required`

All outputs remain:

- `research_only: true`
- `observe_only: true`
- `promotion_ready: false`
- `candidate_pack_written: false`
- `candidate_pack_eligible: false`

## Selection Policy

The materializer is intentionally bounded:

- `max_candidates: 24`
- `max_per_entry_signature: 1`
- sort order: highest `final_score`, then `score`, independent event count,
  trade count, and candidate ID.

The entry-signature cap prevents one dense parameter family from consuming the
entire downstream validation budget. It also makes the next packet cheaper:
instead of backtesting tens of thousands of near-duplicate leads, it starts from
24 diverse event-signature descriptors per symbol.

## BTCUSDT Evidence

Source discovery manifest:

`data/research/operator_runs/discovery_runs/exact-entry-sweep-btcusdt-candidate-depth-v1/discovery_run_manifest.json`

Materialization outputs:

- `data/research/operator_runs/wpr106_30_discovery_lead_materialization/btcusdt/discovery_lead_materialization_manifest.json`
- `data/research/operator_runs/wpr106_30_discovery_lead_materialization/btcusdt/materialized_discovery_leads.parquet`
- `data/research/operator_runs/wpr106_30_discovery_lead_materialization/btcusdt/materialization_candidate_specs.jsonl`

Summary:

- source discovery rows: 22,560;
- materialized descriptors: 24;
- unique selected entry-event signatures: 24;
- skipped by entry-signature cap: 22,466;
- skipped by materialization budget after signature diversification: 70;
- candidate-pack eligible descriptors: 0;
- candidate pack written: false;
- promotion ready: false.

Hashes:

- source discovery manifest:
  `766ac347ed2fc4d8022110d038b82b6ef3b71c62bd0954f2b21391e53cb39e75`
- source interesting-candidates ledger:
  `c06eb92ba42e44a02e5abbdae0d9e7c04f4f70bc6cfb8d672676332eb83cfef5`
- materialized leads Parquet:
  `266762715c575802e5d9505ce1ed76ca36c0deee25992834a2d481a568fa896a`
- candidate specs JSONL:
  `81df80a1ba20ead8a409a3cdda440f68762dda949275c9aa326bf62d50e38613`

## ETHUSDT Evidence

Source discovery manifest:

`data/research/operator_runs/discovery_runs/exact-entry-sweep-ethusdt-candidate-depth-v1/discovery_run_manifest.json`

Materialization outputs:

- `data/research/operator_runs/wpr106_30_discovery_lead_materialization/ethusdt/discovery_lead_materialization_manifest.json`
- `data/research/operator_runs/wpr106_30_discovery_lead_materialization/ethusdt/materialized_discovery_leads.parquet`
- `data/research/operator_runs/wpr106_30_discovery_lead_materialization/ethusdt/materialization_candidate_specs.jsonl`

Summary:

- source discovery rows: 23,040;
- materialized descriptors: 24;
- unique selected entry-event signatures: 24;
- skipped by entry-signature cap: 22,944;
- skipped by materialization budget after signature diversification: 72;
- candidate-pack eligible descriptors: 0;
- candidate pack written: false;
- promotion ready: false.

Hashes:

- source discovery manifest:
  `73586c7f630bef66a8ecd1e97b5410896c7d5abc0c3c93ca00e183398b82b902`
- source interesting-candidates ledger:
  `5ff32b854e2347b0523b94092a6fc0452957b7358216c4bff6ad5f06eb733e76`
- materialized leads Parquet:
  `51ef4fd47c9d6e715474d3a00ca17206e8d1ceeef75d09eb43d4240cf1b393a8`
- candidate specs JSONL:
  `ec6814ec410f9a49f12082d20c22793d8d74b5db5b92686c87830e5087fd1286`

## Interpretation

WPR106-30 moves the project forward from "autopilot completed but every
discovery lead is outside the ranked cycle candidate universe" to "there is a
bounded, hash-backed descriptor set ready for the next validation packet."

This still does not prove a candidate. The descriptors are not:

- backtest evidence;
- cycle rankings;
- candidate gate rows;
- exit-lab pass evidence;
- multiple-testing pass evidence;
- validation-floor pass evidence;
- candidate-pack eligibility evidence;
- promotion evidence.

The next packet should run these descriptors through a real
cycle/backtest/ranking evidence path. Only after that evidence exists should the
candidate-pack bridge be rerun against materialized candidates.

## Validation

Passed:

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
$env:PYTHONPATH='src'; python -m pytest tests\research_artifacts\test_candidate_pack.py -q
```

Observed:

- compileall passed;
- research-discovery tests: 218 passed;
- contract tests: 427 passed;
- candidate-pack tests: 37 passed.

No new P0/P1 issue was opened. WPR106-30 intentionally preserves the existing
candidate-pack rejection boundary and creates only the safe descriptor artifact
needed for the next empirical work.
