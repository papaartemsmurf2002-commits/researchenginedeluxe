# WPR85-01 Real Discovery Search Alignment

## Objective

Fix the operator research flow so "full research" no longer launches only smoke
or placeholder discovery work. The discovery run manager must execute real
research-only HMM/KNN trial evaluations for standard/deep discovery modes and
the UI must make the smoke/standard/deep distinction explicit.

## Diagnosis

The latest operator run completed quickly because it launched
`configs/discovery/quick_smoke_btcusdt_v4.json`. That spec has three placeholder
trial templates. The discovery runner also generated placeholder trials for
`entry_discovery_standard` and `deep_candidate_harvest`, while the benchmark
tiers intentionally used tiny regression guardrail budgets. This is not aligned
with the V4 goal of extensive, resumable search through feature sets, KNN
settings, regimes, and filters.

The historical cycle is a capped foundation review, not the broad discovery
engine. It should remain a validation/gate surface, while discovery should do
the broad search.

## Allowed paths

- `src/tradingbotsuite/research_discovery/**`
- `src/tradingbotsuite/operator_console.py`
- `src/tradingbotsuite/web/templates/research.html`
- `configs/discovery/**`
- `tests/research_discovery/**`
- `tests/tradingbotsuite/test_operator_ui.py`
- `docs/work_packets/WPR85-01-real-discovery-search-alignment.md`
- `docs/stage_reports/STAGE_R85_REAL_DISCOVERY_SEARCH_ALIGNMENT_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md` only if a blocking risk is discovered

## Constraints

- Preserve research-only, observe-only, and `promotion_ready: false` semantics.
- Do not import live order-placement adapters or mutate live runtime state.
- Keep quick smoke available for plumbing checks.
- Standard/deep discovery must write snapshots, ledgers, and trial records that
  identify real parameters and blocker reasons.
- Keep test budgets small; checked operator presets may be larger because they
  are not executed by routine tests.

## Exit criteria

- `entry_discovery_standard` and `deep_candidate_harvest` execute real
  split-safe HMM/KNN trial evaluations when given data.
- Discovery trial records and ledgers no longer claim placeholder work for real
  modes.
- Operator UI exposes quick smoke, standard real discovery, and deep harvest
  presets, with standard real discovery as the default.
- Starting a new discovery run from the operator UI does not collide with a
  previously completed run; resume remains available for stable run IDs.
- Focused discovery and operator UI tests pass, plus compile and contract
  baseline validation.
