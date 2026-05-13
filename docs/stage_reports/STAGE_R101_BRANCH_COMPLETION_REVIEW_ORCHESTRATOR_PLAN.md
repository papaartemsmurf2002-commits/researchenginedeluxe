# Stage R101 Branch Completion Review And Orchestrator Plan

Date: 2026-05-13
Branch: `research/v3-experimental-engine`
Packet: `docs/work_packets/WPR101-01-branch-completion-review-orchestrator-plan.md`

## Scope

This was a documentation/governance review packet. No implementation files,
configs, generated data, live settings, runtime modes, order-placement paths,
candidate packs, or promotion artifacts were changed.

The review covered:

- governance: `AGENTS.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`,
  `docs/KNOWN_ISSUES.md`, `docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md`, recent
  stage reports, and branch reference/handoff documents
- branch implementation surfaces: data contracts, fixture packs, feature
  builders, strategy contracts, backtest engines, optimization/stability,
  historical research cycle, discovery engine, candidate-pack bridge,
  candidate-pack gates, live preflight, promotion validators, CLI, and operator
  UI
- repo assets: configs, checked fixture manifests, work packets, and stage
  reports

## Validation And Static Review

Passed:

```powershell
python -m compileall -q src\tradingbotsuite
# passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
# 417 passed

$env:PYTHONPATH='src'; python -m pytest tests\research_discovery tests\live tests\historical tests\backtesting tests\optimization tests\research_artifacts tests\features -q
# 434 passed, 1 skipped

git diff --check
# passed with line-ending warnings only

$env:PYTHONPATH='src'; python -m pytest -q
# 1323 passed, 1 skipped, 92 warnings
```

Warnings were the existing pandas FutureWarnings from legacy
`src/tradingbot/lorentz_lc.py` tests plus one XGBoost device fallback warning
in the local environment.

Static review notes:

- Config JSON and checked fixture-pack manifest JSON parsed cleanly.
- Static scan found no unsafe source/config/data artifact setting
  `promotion_ready: true`; matches were tests/docs only.
- Static scan found no order-placement calls in research/data/features/
  strategies/backtesting/optimization/research-cycle/discovery/artifact
  packages beyond explicit `order_placement_used: false` evidence fields.
- Static scan found no forbidden order-placement imports in
  `research_cycle`, `optimization`, `research_artifacts`, `promotion`, or
  `live`; however, contract tests do not currently cover every one of those
  roots.

## Review Findings

### P1: Fixture source provider capability mismatch is not validated

`src/tradingbotsuite/data/historical_fixture_pack.py` attaches
`provider_capability` metadata to top-level fixture source metadata, but the
validator only calls `_validate_provider_capability_metadata()` from
`_validate_context_family_metadata()` for context-family entries. Tests assert
the generated source capability exists and reject context-family mismatches,
but there is no regression for a tampered top-level source capability.

Risk: A fixture manifest can carry misleading top-level source capability
metadata while still passing fixture validation. Candidate-pack provenance
checks compare cycle evidence to the fixture manifest, so a tampered fixture can
propagate the same misleading source metadata into later evidence unless the
source capability is validated at the fixture contract layer.

Recorded as `ISSUE-R101-001`.

### P1: Direct research CLI output-directory allowlist is incomplete

`src/tradingbotsuite/main.py` contains `_resolve_research_output_dir()` and uses
it for the discovery candidate-pack bridge, while many older research CLI
commands still pass `Path(args.output_dir)` directly. The operator UI has
stronger isolated-output behavior for historical cycles and discovery runs, but
direct CLI behavior is still weaker.

Risk: A direct research command can write outside the configured research output
root when a user supplies an absolute or parent-traversing output directory.
That is not an observed live write, but it is a boundary hardening gap and was
already explicitly deferred by R98.

Recorded as `ISSUE-R101-002`.

### P1: Durable candidate-ready empirical evidence is still absent

The branch has robust machinery but still lacks durable multi-window BTCUSDT
and ETHUSDT evidence adequate for candidate-ready claims. Latest-window REST
context and Crypto Lake free-sample liquidation evidence are correctly
diagnostic-only. Candidate-pack absence remains the right outcome until durable
source, validation-floor, exit-lab, multiple-testing, split/side/regime,
cost-stress, ablation, and stability evidence pass together.

Recorded as `ISSUE-R101-003`.

### P2: Import-boundary coverage omits important roots

`tests/contracts/test_import_boundaries.py` covers `research`,
`research_discovery`, `data`, `features`, `backtesting`, and `strategies`, but
not `research_cycle`, `optimization`, or `research_artifacts`. Static scans did
not find forbidden imports there today, but future regressions should be caught
by contract tests.

Recorded as `ISSUE-R101-004`.

### P2: Provider capability metadata is not yet a gate input

The provider capability registry is a useful metadata layer, but readiness and
pack gates still mostly consume older fields such as latest-window,
free-sample, diagnostic-only, fixture validation, and evidence-scope flags.
Durability class, health policy, and candidate-ready default should become
first-class data-source and gate evidence before the branch claims completion.

Recorded as `ISSUE-R101-005`.

### P3: Package naming remains split

The canonical console script is now `tradingbotsuite`, but `pyproject.toml`
still declares the distribution as `tradingbot-framework`. This is acceptable
for local compatibility, but should be resolved before release-style handoff.

Recorded as `ISSUE-R101-006`.

## Other Weak Points

- The largest orchestration files remain very large:
  `research_cycle/runner.py`, `historical_fixture_pack.py`,
  `research/market_data.py`, `research_discovery/runner.py`, and
  `research_artifacts/candidate_pack.py`. This is manageable with current
  tests, but future changes should prefer narrow helper extraction and targeted
  contract tests instead of broad rewrites.
- Data/provider layering is still mixed in places: some `data.providers`
  wrappers call into `research.market_data`, while legacy research paths still
  use `tradingbotsuite.adapters.binance` for market-data collection. This is
  not an order-placement violation, but it keeps provider and research
  responsibilities less clean than the package map suggests.
- The legacy `src/tradingbot/` package and live-adjacent launchers remain in
  the repo. Current guards are effective, but future agents should continue
  treating them as compatibility/live-adjacent surfaces, not active research
  truth.
- Optional CUDA/Tensor Core paths remain diagnostic; local evidence did not
  support production speedup claims. Keep CPU/reference validation authoritative
  for candidate gates.

## Undeveloped Or Incomplete Branch Areas

These are not regressions, but they are still necessary before the branch can
be called empirically complete:

- durable BTCUSDT/ETHUSDT multi-window public-archive or vendor-backed fixture
  packs
- capability-aware candidate-readiness gates that distinguish direct REST,
  latest-window REST, public archive, local vendor export, registered-only, and
  free-sample data without relying on loose flags alone
- true no-regime/GMM/optional true-HMM comparison evidence; current regime
  materialization should not be overstated as temporal HMM transition evidence
- candidate-ready orderflow/depth evidence; current AggTrade features are a
  trade-flow proxy, not true L2/order-book imbalance
- liquidation evidence that is provider-backed and candidate-pack eligible;
  current free-sample liquidation evidence remains diagnostic
- direct CLI output-root allowlisting
- package/distribution naming cleanup
- Stage 13 paper/shadow/testnet/canary/live execution and any promotion
  authorization; this remains outside the research branch unless a later
  governed process explicitly changes scope

## Research Recommendations

Highest-value research direction:

1. Fix contract and boundary gaps before more candidate harvesting:
   source capability validation, output-dir allowlisting, import-boundary
   coverage, and capability-aware gates.
2. Build durable data first. Use public archives or vendor exports for
   BTCUSDT/ETHUSDT over multiple market windows; keep latest-window and
   free-sample surfaces diagnostic.
3. Run falsification, not promotion. Treat each candidate as a hypothesis that
   must survive no-regime/GMM comparisons, independent-event accounting,
   side-separated evidence, split/regime evidence, costs/funding/slippage
   stress, exit-lab comparisons, filter ablations, feature ablations,
   multiple-testing controls, and stability neighborhoods.
4. Keep KNN exact and cached before adding ANN/GPU. Exact neighbor-cache reuse
   and vectorized threshold sweeps are safer than broad randomized or
   approximate acceleration until parity evidence exists.
5. Prefer compact, interpretable feature families. Add trade-flow/orderflow
   proxies only with clear source capability and missingness evidence; defer
   true L2/OFI until depth snapshots and diff-depth stream reconstruction or a
   durable archived-depth provider exist.
6. Do not treat high signal-rate, one-sided, latest-window, or long-horizon
   overlapping-event results as strategy evidence. They are leads until
   independent-event and validation floors pass.

## Orchestrator Completion Plan

Recommended next implementation stages:

### Stage R102: Contract and boundary gap closure

Must close `ISSUE-R101-001` and `ISSUE-R101-002` first. Also close or reduce
`ISSUE-R101-004` and `ISSUE-R101-005` where practical.

Packets:

- `WPR102-01-fixture-source-capability-validation`
- `WPR102-02-cli-output-root-allowlist`
- `WPR102-03-import-boundary-coverage-expansion`
- `WPR102-04-capability-aware-readiness-gate-foundation`

### Stage R103: Durable BTC/ETH data foundation

Goal: produce durable, validated, non-synthetic, non-latest-window BTCUSDT and
ETHUSDT fixture packs with capability metadata and source-health evidence.

Packets:

- `WPR103-01-btcusdt-public-archive-multi-window-fixture`
- `WPR103-02-ethusdt-public-archive-multi-window-fixture`
- `WPR103-03-aggtrade-orderflow-durable-context`
- `WPR103-04-context-source-health-and-gap-evidence`

### Stage R104: Candidate validation on durable evidence

Goal: rerun historical cycles and discovery on durable packs, preserving
research-only status and accepting candidate-pack absence when gates block.

Packets:

- `WPR104-01-durable-historical-cycle-btc-eth`
- `WPR104-02-discovery-validation-floors-on-durable-fixtures`
- `WPR104-03-discovery-to-candidate-pack-bridge-recheck`
- `WPR104-04-operator-ui-durable-evidence-truthfulness`

### Stage R105: Empirical falsification matrix

Goal: test whether any strategy family survives falsification rather than just
searching for more leads.

Packets:

- `WPR105-01-no-regime-gmm-true-hmm-comparison-plan`
- `WPR105-02-independent-event-and-signal-density-gate`
- `WPR105-03-matched-feature-filter-exit-ablation`
- `WPR105-04-side-split-regime-cost-stability-review`

### Stage R106: Packaging and maintainability polish

Goal: make the branch easier to hand off once contract/data/gate work is
closed.

Packets:

- `WPR106-01-distribution-name-decision`
- `WPR106-02-large-module-extraction-plan`
- `WPR106-03-doc-and-start-here-refresh`

### Stage R107: Promotion handoff planning only

Open only after at least one research-only candidate pack exists with durable
evidence and all research gates passing. This stage may prepare paper/shadow
handoff artifacts but must not start live execution from this branch.

## Stage Decision

R101 closes as a review and planning stage. There are no open P0 issues and
three open P1 issues, so the ledger may open the next implementation stage
under the stage stop rule. The branch is not empirically complete and must not
claim candidate, promotion, live, profitability, or speedup readiness.

Validation passed as recorded above, including the full suite and
`git diff --check`.
