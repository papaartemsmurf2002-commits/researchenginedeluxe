# Known Issues

Last updated: 2026-05-13

This registry is the blocking issue source for orchestrator stage gates.

Severity levels:

- P0: safety, data leakage, live trading risk, corrupt data, branch boundary violation.
- P1: invalid backtest assumption, non-deterministic experiment, broken artifact contract, severe performance blocker.
- P2: incomplete docs, minor missing tests, non-blocking refactor debt.
- P3: polish and convenience.

Stage advancement stop rule:

- Any open P0 blocks stage advancement.
- Four or more unresolved P1 issues block stage advancement.
- P2/P3 can carry forward only with explicit orchestrator note and owner.

## Current summary

| Severity | Open | In progress | Resolved | Accepted debt |
| --- | ---: | ---: | ---: | ---: |
| P0 | 0 | 0 | 1 | 0 |
| P1 | 0 | 0 | 8 | 0 |
| P2 | 0 | 0 | 2 | 0 |
| P3 | 0 | 0 | 1 | 0 |

## ISSUE-R101-001: Fixture source provider capability mismatch is not validated

Severity: P1
Stage discovered: Stage R101 - Branch completion review and orchestrator plan
Owner: Codex Research Agent
Status: resolved
Paths affected: `src/tradingbotsuite/data/historical_fixture_pack.py`, `tests/contracts/test_historical_fixture_pack_contract.py`

### Problem

WPR100 added provider capability metadata to generated fixture-pack source and
context entries, but fixture validation only checks provider capability payloads
on context families. A tampered top-level fixture `source.provider_capability`
can claim the wrong durability class or source identity without failing
`validate_historical_fixture_pack_manifest()`.

### Evidence

Review found `_provider_source_metadata()` attaches provider capability
metadata, while `_validate_provider_capability_metadata()` is only called from
`_validate_context_family_metadata()` for context-family entries. Existing
tests assert source capability is present and reject context mismatches, but
there is no source mismatch regression.

### Required resolution

Validate top-level fixture `source.provider_capability` against the fixture
source name and primary data family, add a regression that tampers the source
capability, and ensure candidate-pack provenance evidence cannot inherit a
tampered source capability as trusted truth.

### Resolution notes

Resolved by WPR102-01. Top-level fixture `source.provider_capability`
metadata is now revalidated against the declared source and primary data
family, with regressions for tampered source identity and durability class.

## ISSUE-R101-002: Direct research CLI output-directory allowlist is incomplete

Severity: P1
Stage discovered: Stage R101 - Branch completion review and orchestrator plan
Owner: Codex Research Agent
Status: resolved
Paths affected: `src/tradingbotsuite/main.py`, `tests/live/**`, `tests/tradingbotsuite/**`

### Problem

The operator UI now isolates historical-cycle and discovery output under the
configured research output root, and the discovery candidate-pack bridge uses a
central output-dir resolver. Many direct CLI research commands still pass
`--output-dir` values through as raw `Path(args.output_dir)` values. This leaves
the direct CLI boundary weaker than the operator boundary and keeps alive the
R98-deferred risk that research commands can write outside the research output
tree.

### Evidence

Review found `_resolve_research_output_dir()` in `src/tradingbotsuite/main.py`,
but most research CLI handlers still pass `Path(args.output_dir)` directly.
WPR98 explicitly deferred wholesale output-directory allowlist hardening.

### Required resolution

Create a dedicated CLI output-root allowlist packet. Route all research command
output directories through a shared resolver, keep input/source paths separate,
add command-level tests for each `--output-dir`, and preserve existing operator
UI isolated-output behavior.

### Resolution notes

Resolved by WPR102-01. Direct research CLI output directories are routed
through the shared research output-root resolver, command tests cover the
allowlist boundary, and input/source paths remain separate from output
resolution.

## ISSUE-R101-003: Candidate-ready empirical evidence is still blocked by durable multi-window data gaps

Severity: P1
Stage discovered: Stage R101 - Branch completion review and orchestrator plan
Owner: Codex Research Agent
Status: resolved
Paths affected: `configs/research/**`, `configs/discovery/**`, `data/research/fixtures/**`, `src/tradingbotsuite/research_cycle/**`, `src/tradingbotsuite/research_discovery/**`

### Problem

The branch has strong machinery for fixture validation, discovery, backtesting,
gates, and candidate-pack rejection, but it still lacks durable multi-window
BTCUSDT/ETHUSDT evidence sufficient for candidate-ready empirical claims. The
latest-window REST context fixtures and Crypto Lake free-sample liquidation
fixture are correctly diagnostic-only, so they cannot complete candidate-ready
research by themselves.

### Evidence

Configs and fixture manifests continue to label latest-window context and free
sample evidence as diagnostic or non-promotable. Recent stage reports and the
branch technology reference defer durable BTC/ETH multi-window evidence,
liquidation candidate eligibility, true L2/depth evidence, and Stage 13
execution.

### Required resolution

Build durable BTCUSDT/ETHUSDT multi-window fixture packs from public archive or
vendor-backed sources with capability metadata, run historical-cycle and
discovery validation on those packs, and keep all candidate packs blocked until
validation floors, exit lab, multiple-testing, side/split/regime, stability,
cost-stress, and source-capability evidence pass.

### Resolution notes

Resolved by WPR102-01 and WPR103-01. WPR102 made provider capability and
durable public archive readiness first-class blockers in research-cycle,
discovery validation-floor, bridge, and candidate-pack gates. WPR103 added
checksum-verified BTCUSDT and ETHUSDT Binance Vision multi-window fixture
packs under `data/research/fixtures/*_public_archive_multi_window_v1`, each
with 15m bars, 1m lower-timeframe bars, 1m aggregated aggTrade trade-flow
proxy context, source archive hashes, provider capability metadata, window
selection metadata, and durable public-archive readiness validation. No
candidate pack, promotion artifact, latest-window-only evidence, or fabricated
data was promoted; candidate validation remains a later research-only stage.

## ISSUE-R101-004: Import-boundary tests omit several live-adjacent research packages

Severity: P2
Stage discovered: Stage R101 - Branch completion review and orchestrator plan
Owner: Codex Research Agent
Status: resolved
Paths affected: `tests/contracts/test_import_boundaries.py`, `src/tradingbotsuite/research_cycle/**`, `src/tradingbotsuite/optimization/**`, `src/tradingbotsuite/research_artifacts/**`

### Problem

Import-boundary tests cover `research`, `research_discovery`, `data`,
`features`, `backtesting`, and `strategies`, but do not cover
`research_cycle`, `optimization`, or `research_artifacts`. These packages are
central to candidate gates and live-adjacent artifact handling, so future import
regressions could bypass the current contract test.

### Evidence

Static review found no forbidden order-placement imports in those packages, but
`tests/contracts/test_import_boundaries.py` does not enumerate them.

### Required resolution

Extend import-boundary tests to include `research_cycle`, `optimization`, and
`research_artifacts`, and keep the forbidden import list aligned with the
boundary contract.

### Resolution notes

Resolved by WPR102-01. Import-boundary tests now cover `research_cycle`,
`optimization`, and `research_artifacts`, and the boundary contract documents
those roots as research/live-adjacent surfaces that must not import
order-placement adapters.

## ISSUE-R101-005: Provider capabilities are not yet consumed by readiness and pack gates

Severity: P2
Stage discovered: Stage R101 - Branch completion review and orchestrator plan
Owner: Codex Research Agent
Status: resolved
Paths affected: `src/tradingbotsuite/data/contracts.py`, `src/tradingbotsuite/data/historical_fixture_pack.py`, `src/tradingbotsuite/research_cycle/**`, `src/tradingbotsuite/research_artifacts/candidate_pack.py`, `src/tradingbotsuite/research_discovery/**`

### Problem

Provider capability metadata is now emitted and partially validated, but
candidate-readiness logic still primarily relies on older latest-window,
free-sample, diagnostic, and fixture-evidence flags. The new durability class,
health policy, and candidate-ready-default fields are not yet first-class gate
inputs.

### Evidence

Static scans found `candidate_ready_default` and `provider_capability` usage in
the data/fixture layers, but not as decision inputs in historical-cycle gates,
discovery validation floors, or candidate-pack eligibility.

### Required resolution

Promote provider capability metadata into data-source evidence, public-archive
readiness, historical-cycle rankings, discovery validation floors, and
candidate-pack gate reasons so diagnostic/default-false capabilities cannot be
treated as candidate-ready by omission.

### Resolution notes

Resolved by WPR102-01. Provider capability and durable public archive readiness
are now carried into research-cycle data-source evidence, candidate gate
reports, discovery validation floors, and candidate-pack source evidence so
diagnostic/default-false sources block candidate readiness unless durable
archive readiness proves the source is usable.

## ISSUE-R101-006: Distribution name still points at the legacy package identity

Severity: P3
Stage discovered: Stage R101 - Branch completion review and orchestrator plan
Owner: Codex Research Agent
Status: resolved
Paths affected: `pyproject.toml`, `README.md`, packaging/install documentation, CI or release metadata if added later

### Problem

R98 added the canonical `tradingbotsuite` console script, but the project
distribution name remains `tradingbot-framework`. This is not a runtime safety
blocker, but it is a handoff and packaging weak point for a branch that now
orients users around the active `tradingbotsuite` package.

### Evidence

`pyproject.toml` still declares `name = "tradingbot-framework"` while docs and
the new console entrypoint use `tradingbotsuite`.

### Required resolution

Open a packaging-only packet before any release or external handoff. Decide
whether to rename the distribution, preserve an alias/compatibility story, and
update docs/tests without breaking editable local installs.

### Resolution notes

Resolved by WPR102-01. The active distribution name is now `tradingbotsuite`;
the legacy `tradingbot` console/package compatibility path is retained for
existing local workflows.

## ISSUE-R98-001: Legacy replay metrics could report promotion readiness

Severity: P0
Stage discovered: Stage R98 - Research boundary validation hardening
Owner: Codex Research Agent
Status: resolved
Paths affected: `src/tradingbotsuite/research/dataset.py`, `src/tradingbotsuite/research/modeling.py`, `src/tradingbotsuite/research/evaluation.py`, `src/tradingbotsuite/research/live_readiness.py`, `tests/tradingbotsuite/test_research.py`

### Problem

The legacy BTC research dataset/model/replay path did not consistently emit the
full research boundary metadata, and `replay_eval()` could set
`promotion_ready: true` when local metric thresholds passed. That contradicted
the branch invariant that research outputs are observe-only and not promotion
artifacts.

### Evidence

Subagent boundary review found dataset manifests carrying only
`research_only: true`, train/artifact manifests omitting the full trio, and
`src/tradingbotsuite/research/evaluation.py` deriving promotion readiness from
local replay failures.

### Required resolution

Normalize the legacy research artifacts to emit `research_only: true`,
`observe_only: true`, `promotion_ready: false`, and non-live boundary metadata;
make replay metrics include an explicit research-only non-promotable failure.

### Resolution notes

Resolved by WPR98-01. The shared `research_artifact_boundary_metadata()` helper
is used by legacy dataset/model/replay outputs, and replay metrics now remain
non-promotable even when local diagnostic thresholds pass.

## ISSUE-R1-001: Research branch still contains live execution surfaces

Severity: P1
Stage discovered: Stage 1 - Repo cartography
Owner: Orchestrator Agent / Live Safety Agent
Status: resolved
Paths affected: `run_manual.py`, `run_live_smoke.py`, `src/tradingbotsuite/adapters/execution.py`, `src/tradingbotsuite/core/engine.py`, `src/tradingbotsuite/runtime.py`, `src/tradingbotsuite/web/operator.py`, `src/tradingbot/live.py`, `src/tradingbot/data/hyperliquid.py`

### Problem

The research branch carries live-adjacent launchers and execution adapters. This does not prove research modules are placing orders, but it increases branch-boundary risk and must be isolated or guarded before any later research artifact can be interpreted as live-ready.

### Evidence

Stage 1 cartography identified Hyperliquid execution adapters, manual runtime launchers, operator commands, and legacy `tradingbot` live paths on `research/v3-experimental-engine`.

### Required resolution

Stage 2 must formalize import and artifact contracts. Stage 10/11 must keep live execution on the live branch and require promotion/shadow validation before any research output reaches live runtime behavior.

### Resolution notes

Stage 2 added `docs/contracts/boundary_contract.md` and `tests/contracts/test_import_boundaries.py` to prevent research modules from importing order-placement paths. Stage 10/11 added live preflight and promotion/shadow validation so research outputs cannot become live execution inputs without explicit later approval.

## ISSUE-R1-002: Research CLI and live/operator CLI are coupled in one entry module

Severity: P1
Stage discovered: Stage 1 - Repo cartography
Owner: Orchestrator Agent / Documentation Agent
Status: resolved
Paths affected: `src/tradingbotsuite/main.py`, `src/tradingbotsuite/operator_console.py`, `src/tradingbotsuite/web/operator.py`

### Problem

`src/tradingbotsuite/main.py` exposes live/operator commands and research commands in the same module, and the operator UI can queue research jobs. This needs explicit contract documentation and later enforcement so live mode cannot run research jobs.

### Evidence

Stage 1 command inventory found `serve`, `manual`, `smoke-live`, `build-dataset`, `train-model`, `calibrate-model`, `replay-eval`, HMM/KNN commands, provider fetch commands, and experiment commands in the same CLI module.

### Required resolution

Stage 2 should document command ownership and boundary rules. Stage 10 should enforce live-mode rejection of research jobs.

### Resolution notes

Stage 2 documented command ownership in `docs/contracts/boundary_contract.md`. Stage 10 added `src/tradingbotsuite/live/preflight.py`, CLI guards in `src/tradingbotsuite/main.py`, and tests in `tests/live/test_preflight.py` so live mode rejects research commands before execution. Stage 12.1 added the new `plan-feature-ablation` research command to the same live rejection set.

## ISSUE-R44-001: Final crosscheck found research evidence hygiene blockers

Severity: P1
Stage discovered: Stage R44 - Final crosscheck hardening
Owner: Codex Research Agent
Status: resolved
Paths affected: `src/tradingbotsuite/research_cycle/benchmark.py`, `src/tradingbotsuite/research_cycle/runner.py`, `src/tradingbotsuite/backtesting/splits.py`, `src/tradingbotsuite/optimization/stability.py`, `src/tradingbotsuite/research/market_data.py`, `src/tradingbotsuite/research/feature_ablation.py`, `.gitignore`, `data/research/fixtures/btcusdt_context_provider_latest_month_v1/**`

### Problem

The final crosscheck found several issues that could weaken reproducibility or evidence truthfulness before push: relative benchmark output paths could recurse under generated spec locations, provider benchmark evidence depended on an ignored fixture, non-contiguous holdout splits could include unrelated rows, stability and ablation grouping omitted exit-policy identity, fixed-interval context manifests did not detect gaps, and generic feature-ablation runs could be labeled validation-incomplete when all configured evidence was executable.

### Evidence

Independent agent review and full-suite validation identified the benchmark path risk, ignored provider fixture risk, split/evidence grouping issues, context gap reporting issue, and failing tests in benchmark artifact accounting, removed-source boundaries, and feature-ablation execution scope.

### Required resolution

Before commit/push, make provider fixture evidence durable, resolve benchmark paths to absolute directories, use short generated backtest run directory names, preserve exact holdout membership, include exit-policy identity in stability/ablation grouping, make context gap checks interval-aware, and rerun focused plus full validation.

### Resolution notes

Stage R44 fixes implemented all required changes and added regression coverage. The provider latest-month fixture pack is unignored for commit. Focused validation passed, WPR42 provider benchmark was rerun without filename-length warnings, and full validation is recorded in the R44 stage report.

## ISSUE-R58-001: OI contraction exit accepted non-finite context

Severity: P1
Stage discovered: Stage R58 - OI contraction exit policy
Owner: Codex Research Agent
Status: resolved
Paths affected: `src/tradingbotsuite/backtesting/exits.py`, `tests/backtesting/test_exit_policy_expansion.py`

### Problem

The new `oi_contraction_exit_v1` policy initially treated infinite OI values as valid row-level context. A row with infinite OI notional and negative-infinite OI delta/z-score could trigger an exit instead of failing closed to the normal time exit.

### Evidence

Final review of the WPR58 diff reproduced an `oi_contraction_exit_v1` trigger on non-finite OI context, contradicting the stage report's row-level missing or non-finite context behavior.

### Required resolution

Reject non-finite values in optional numeric context conversion and add regression coverage for `inf` and `-inf` OI rows.

### Resolution notes

Stage R58 updated `_optional_numeric` to return no context for non-finite numbers and added `test_oi_contraction_exit_skips_non_finite_oi_context`. Focused validation passed after the fix.

## ISSUE-R95-001: CUDA backtest backend absent for NVIDIA acceleration path

Severity: P1
Stage discovered: Stage R95 - Performance candidate-selection engine crosscheck
Owner: Codex Research Agent
Status: resolved
Paths affected: `src/tradingbotsuite/research_cycle/runner.py`, `src/tradingbotsuite/backtesting/**`, `src/tradingbotsuite/optimization/**`

### Problem

The research-cycle candidate-selection path can now record NVIDIA/CUDA preference and run aggregate candidate backtests with bounded CPU workers, but no concrete CUDA/GPU backtest backend is registered. GPU acceleration therefore cannot truthfully be claimed for candidate search or stability-region evaluation yet.

### Evidence

WPR95 crosscheck found only reference and fixed-holding vector CPU backtest backends. The performance plan reports `blocked_no_cuda_backtest_backend_registered` whenever GPU acceleration is requested.

### Required resolution

Add a validated CUDA-capable research backtest or feature-evaluation backend with backend evidence, parity checks against the reference engine, deterministic artifact identity, and fallback behavior before any NVIDIA speedup claim is allowed.

### Resolution notes

Resolved by WPR96. The branch now has an optional `cuda_fixed_holding`
research backend with lazy CuPy import, runtime smoke evidence, support reason
codes, CPU fallback behavior, fake-CuPy parity tests, local CUDA parity tests
when hardware is available, benchmark evidence, and stability-region
acceleration counters. The backend remains diagnostic and `speed_claimed: false`;
split/cost-stress validation is forced back to CPU/reference when GPU routing is
requested. Rich exits, lower-timeframe paths, KNN overlays, candidate-pack
promotion, live readiness, sizing, and order placement remain out of scope.

## Issue template

```markdown
## ISSUE-ID: Short title

Severity: P0/P1/P2/P3
Stage discovered:
Owner:
Status: open | in_progress | resolved | accepted_debt
Paths affected:

### Problem

### Evidence

### Required resolution

### Resolution notes
```
