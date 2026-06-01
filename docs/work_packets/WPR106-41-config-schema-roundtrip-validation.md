# WPR106-41 Config Schema And Roundtrip Validation

## Goal

Add fail-closed schema guards and roundtrip tests for active research-cycle and
discovery-run JSON spec surfaces without changing research behavior, candidate
gates, live/paper behavior, order placement, promotion logic, or generated
artifacts.

## Current Repo Facts

- `HistoricalResearchCycleSpec` and `DiscoveryRunSpec` parse JSON with
  dataclass `from_payload()` methods and write resolved configs through
  `to_payload()`.
- Both parsers already perform many semantic checks for synthetic fallback,
  validation split modes, compute settings, discovery execution settings, and
  regime mode semantics.
- Some configs contain intentional research metadata keys that are not consumed
  by the parser, such as `research_only`, `promotion_ready`, blocker notes, and
  work packet references.
- Existing tests cover many invalid values but do not assert a stable schema
  guard against misspelled nested fields or a full parser roundtrip contract.

## Conflicts And Stale Docs Found

- `configs/research/**` contains multiple non-cycle JSON manifests, so any
  historical-cycle schema validation must apply only inside
  `HistoricalResearchCycleSpec.from_payload()` and not to every JSON file in
  that directory.
- Some historical-cycle config metadata is intentionally documentary and should
  remain accepted, but misspelled parser sections and known nested parser fields
  should fail closed.

## Allowed Edit Paths

- `docs/work_packets/WPR106-41-config-schema-roundtrip-validation.md`
- `docs/work_packets/WPR106-41-progress.jsonl`
- `src/tradingbotsuite/research_cycle/spec.py`
- `src/tradingbotsuite/research_discovery/spec.py`
- `tests/contracts/test_research_cycle_contract.py`
- `tests/research_discovery/test_discovery_spec.py`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/stage_reports/STAGE_R106_CONFIG_SCHEMA_ROUNDTRIP_VALIDATION_REPORT.md`

## Forbidden Edit Paths

- strategy plugins and search spaces
- backtest execution semantics, costs, fills, or split logic
- live/paper/runtime/order-placement adapters
- candidate gate thresholds or promotion logic
- generated research artifacts, fixture data, and candidate packs
- broad historical docs rewrites outside active index, ledger, and report
- `.pytest_cache/**`

## Subagents Used

- Schema Engineer: read-only audit of active spec parsing, schema gaps, and
  roundtrip test coverage.

## Tests To Run

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_research_cycle_contract.py tests\research_discovery\test_discovery_spec.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
git diff --check
```

## Artifacts Expected

- Parser-level schema guard helpers for active historical-cycle and
  discovery-run specs.
- Roundtrip tests proving `from_payload(to_payload())` preserves the effective
  spec contract.
- Tests proving misspelled active nested fields fail closed.
- Updated stage report.

No generated research artifacts, candidate packs, promotion claims, or live
runtime behavior are expected.

## Definition Of Done

- Historical-cycle and discovery-run specs reject unknown active nested fields
  with actionable error messages.
- Intentional documentary metadata in checked historical-cycle configs remains
  accepted.
- Effective payload roundtrips are stable for both spec types.
- Focused and contract validation passes.

## Rollback Plan

Revert only files listed in allowed edit paths. Do not touch generated
artifacts, candidate packs, live/runtime paths, or unrelated cache state.
