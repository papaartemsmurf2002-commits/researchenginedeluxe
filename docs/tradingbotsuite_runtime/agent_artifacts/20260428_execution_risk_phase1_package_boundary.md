# Execution Risk Phase 1 Package Boundary

## Agent name

Execution and Risk Agent

## Task received

Produce the final include/exclude list for the HMM/KNN PR. Confirm no live-boundary files changed. Confirm all outputs remain research-only. Write this artifact.

## Files read

- `git status --short` output.
- `git diff --name-only` output.
- Explicit live-boundary diff output for:
  - `src/tradingbotsuite/adapters/execution.py`
  - `src/tradingbotsuite/core/engine.py`
  - `src/tradingbotsuite/config.py`
  - `src/tradingbotsuite/runtime.py`
  - `src/tradingbotsuite/web/operator.py`
  - `src/tradingbotsuite/web/templates/control.html`
  - `src/tradingbotsuite/operator_commands.py`
- Research-only / observe-only markers in:
  - `configs/v2_btc_hmm_multi_knn_research.json`
  - `src/tradingbotsuite/research/hmm_knn.py`
  - `src/tradingbotsuite/research/hmm_knn_monitoring.py`
  - `docs/tradingbotsuite_runtime/agent_artifacts/`

## Files changed

- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_execution_risk_phase1_package_boundary.md`

## Commands/tests run

```powershell
git status --short
git diff --name-only
git diff -- src/tradingbotsuite/adapters/execution.py src/tradingbotsuite/core/engine.py src/tradingbotsuite/config.py src/tradingbotsuite/runtime.py src/tradingbotsuite/web/operator.py src/tradingbotsuite/web/templates/control.html src/tradingbotsuite/operator_commands.py
rg -n "research_only|promotion_ready|observe_only|live|execute|Hyperliquid|order" configs\v2_btc_hmm_multi_knn_research.json src\tradingbotsuite\research\hmm_knn.py src\tradingbotsuite\research\hmm_knn_monitoring.py docs\tradingbotsuite_runtime\agent_artifacts
```

`git diff --name-only` output:

```text
pyproject.toml
src/tradingbotsuite/main.py
src/tradingbotsuite/operator_console.py
src/tradingbotsuite/research/dataset.py
src/tradingbotsuite/web/templates/research.html
tests/tradingbotsuite/test_operator_ui.py
tests/tradingbotsuite/test_research.py
```

Explicit live-boundary diff result:

```text
<no diff output>
```

Note: the `rg` command also attempted a Windows wildcard path form for `docs\tradingbotsuite_runtime\HMM_MULTI_KNN_*.md`, which PowerShell passed literally and produced an invalid-path warning. The searched concrete paths still showed the key code/config/artifact markers listed below.

## Final HMM/KNN PR include list

Include these for a focused Phase 1 HMM/KNN research PR:

- `pyproject.toml`
  - optional `research` dependency extra
  - pytest import-mode config
- `configs/v2_btc_hmm_multi_knn_research.json`
  - Phase 1 BTC-only HMM/KNN config
- `src/tradingbotsuite/main.py`
  - research-only CLI commands: `research-hmm-knn`, `replay-hmm-knn`, `monitor-hmm-knn`
- `src/tradingbotsuite/operator_console.py`
  - read-only HMM/KNN artifact summary in operator research artifacts
- `src/tradingbotsuite/research/dataset.py`
  - research dataset hardening, point-in-time context preservation, label outcome fields
- `src/tradingbotsuite/research/hmm_knn.py`
  - HMM/KNN research artifact generator and replay guard
- `src/tradingbotsuite/research/hmm_knn_monitoring.py`
  - observe-only monitoring report generator
- `src/tradingbotsuite/web/templates/research.html`
  - Research page observe-only HMM/KNN monitoring display
- `tests/tradingbotsuite/test_hmm_knn.py`
  - targeted HMM/KNN research and monitoring suite
- `tests/tradingbotsuite/test_operator_ui.py`
  - observe-only HMM/KNN research UI/artifact summary coverage
- `tests/tradingbotsuite/test_research.py`
  - research dataset / HMM-KNN integration coverage
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_PROMPTS.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_RUNBOOK.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_EXECUTION_RISK_REVIEW.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_INPUT_LOOKUP.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_MODEL_SPEC.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_REALIZATION_PLAN.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_SOURCE_LOG.md`
- Selected `docs/tradingbotsuite_runtime/agent_artifacts/*.md` files required for the audit trail.

## Final exclude list

Exclude these from a focused HMM/KNN PR unless a separate supervisor decision expands scope:

- `btc_eth_hybrid_framework_verified_blueprint.txt`
- broad root docs outside the HMM/KNN runtime-doc scope:
  - `docs/BTC_RUNTIME_RELIABILITY_GUIDE.md`
  - `docs/DATASET_BUILDING_GUIDE.md`
  - `docs/DEVELOPMENT_ROADMAP.md`
  - `docs/ENTRY_GATE_RESEARCH.md`
  - `docs/GOLDILOCKS_FILTER_RESEARCH.md`
  - `docs/MICROSTRUCTURE_RELIABILITY.md`
  - `docs/MICROSTRUCTURE_SQUARE_ROOT_IMPACT_FINDINGS.md`
  - `docs/OPERATOR_CONSOLE.md`
  - `docs/OPERATOR_GUIDE.md`
  - `docs/PRE_V2_READINESS.md`
  - `docs/PROJECT_PRESERVATION_HANDOFF.md`
  - `docs/TESTNET_FULL_STACK_CHECKLIST.md`
  - `docs/TRADINGVIEW_V2_DATA_FRAMEWORK.md`
  - `docs/V1_FINDINGS.md`
  - `docs/V1_REMEDIATION_PLAN.md`
  - `docs/V1_SCORECARD.md`
  - `docs/V2_RESEARCH_GUIDE.md`
  - `docs/V2_STABILITY_AUDIT.md`
- top-level runner scripts:
  - `run_live_smoke.py`
  - `run_manual.py`
  - `run_server.py`
- top-level duplicate-looking tests unless a test-layout migration is explicitly in scope:
  - `tests/conftest.py`
  - `tests/fixtures/btc_15m_fixture.json`
  - `tests/test_binance.py`
  - `tests/test_config.py`
  - `tests/test_engine.py`
  - `tests/test_entry_gate.py`
  - `tests/test_math.py`
  - `tests/test_microstructure_prediction.py`
  - `tests/test_operator_ui.py`
  - `tests/test_research.py`
  - `tests/test_tradingview_import.py`
- entire nested untracked legacy tree:
  - `tradingbot/`

Do not use `git add .` for this PR because the working tree contains broad untracked docs, scripts, duplicate-looking tests, and a nested legacy tree outside focused HMM/KNN scope.

## Live-boundary confirmation

The explicit live-boundary diff returned no output for:

- `src/tradingbotsuite/adapters/execution.py`
- `src/tradingbotsuite/core/engine.py`
- `src/tradingbotsuite/config.py`
- `src/tradingbotsuite/runtime.py`
- `src/tradingbotsuite/web/operator.py`
- `src/tradingbotsuite/web/templates/control.html`
- `src/tradingbotsuite/operator_commands.py`

Confirmed unchanged:

- live execution
- position sizing
- live accept/reject gates
- Hyperliquid adapter behavior
- runtime bootstrap
- operator web routes
- Control page
- operator command helpers

## Research-only output confirmation

Research-only markers found:

- `configs/v2_btc_hmm_multi_knn_research.json` has `acceptance.research_only: true`.
- `src/tradingbotsuite/research/hmm_knn.py` writes `research_only: True` in the manifest and metrics.
- `src/tradingbotsuite/research/hmm_knn.py` keeps `promotion_ready: False` and always includes `research_only_not_live_promotable` in promotion failures.
- `src/tradingbotsuite/research/hmm_knn.py::replay_hmm_knn_artifact` rejects non-`research_only` manifests and rewrites metrics with `research_only: True` and `promotion_ready: False`.
- `src/tradingbotsuite/research/hmm_knn_monitoring.py` rejects non-`research_only` manifests.
- `src/tradingbotsuite/research/hmm_knn_monitoring.py` writes monitoring reports with `research_only: True`, `promotion_ready: False`, and `observe_only: True`.
- Monitoring alerts are emitted with `observe_only: True`.
- Research UI changes are on `research.html`, not the live Control page.

Outputs remain research-only. No HMM/KNN output is wired to live gates, live sizing, Hyperliquid execution, runtime safe-mode behavior, or operator live controls.

## Decisions made

- Treat this Phase 1 package as a BTC-only HMM/KNN research package.
- Include runtime-adjacent files only where they add research commands or observe-only Research page/artifact display.
- Exclude broad root docs/scripts and legacy/untracked trees from the focused PR.
- Do not make live-readiness or positive-expectancy claims from this package boundary.

## Assumptions

- The public PR should be narrowly scoped to Phase 1 HMM/KNN research, not broad repo preservation.
- Agent artifacts are internal handoff/audit records; include selected artifacts if the PR needs traceability, otherwise keep them out of public scope per reviewer preference.
- ETH remains Phase 2 and is not part of the Phase 1 implementation scope.

## Open issues or blockers

No open issues or blockers for the boundary review.

## Handoff notes for other agents

Stage files intentionally. The safe default is to stage the final include list file-by-file and avoid any broad add command. Live-boundary files remain untouched and should stay untouched unless a separate live-runtime approval task is created.
