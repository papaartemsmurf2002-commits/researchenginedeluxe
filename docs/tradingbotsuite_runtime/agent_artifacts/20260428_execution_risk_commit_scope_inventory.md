# Execution Risk Commit Scope Inventory

## Agent name

Execution and Risk Agent

## Task received

Prepare a commit-scope and live-boundary inventory. Run:

```powershell
git status --short
git diff --name-only
git diff -- src/tradingbotsuite/adapters/execution.py src/tradingbotsuite/core/engine.py src/tradingbotsuite/config.py src/tradingbotsuite/runtime.py src/tradingbotsuite/web/operator.py src/tradingbotsuite/web/templates/control.html src/tradingbotsuite/operator_commands.py
git diff --check
```

Classify changed and untracked files into HMM/KNN required, unrelated existing docs/scripts, tests, runtime-adjacent observe-only, and live-boundary. Confirm live-boundary files are untouched. Identify files that should be excluded from an HMM/KNN commit/PR.

## Files read

- `git status --short` output.
- `git diff --name-only` output.
- Explicit live-boundary `git diff -- ...` output.
- `git diff --check` output.
- Directory listing for `docs/tradingbotsuite_runtime/agent_artifacts/`.
- Top-level listing for untracked `tradingbot/`.

## Files changed

- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_execution_risk_commit_scope_inventory.md`

## Commands/tests run

```powershell
git status --short
git diff --name-only
git diff -- src/tradingbotsuite/adapters/execution.py src/tradingbotsuite/core/engine.py src/tradingbotsuite/config.py src/tradingbotsuite/runtime.py src/tradingbotsuite/web/operator.py src/tradingbotsuite/web/templates/control.html src/tradingbotsuite/operator_commands.py
git diff --check
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

`git diff --check` result:

```text
<no whitespace errors>
```

Git printed CRLF conversion warnings for changed tracked files, but `git diff --check` exited successfully.

## Classification

### HMM/KNN required

Include these in an HMM/KNN commit/PR if the PR is intended to deliver the full HMM/KNN research package:

- `pyproject.toml` - optional `research` extra and pytest import-mode setting.
- `configs/v2_btc_hmm_multi_knn_research.json` - primary HMM/KNN research config.
- `src/tradingbotsuite/research/hmm_knn.py` - HMM/KNN research artifact generator.
- `src/tradingbotsuite/research/hmm_knn_monitoring.py` - observe-only monitoring report generator.
- `src/tradingbotsuite/research/dataset.py` - BTC research dataset hardening, label outcomes, context preservation.
- `src/tradingbotsuite/main.py` - research-only CLI commands: `research-hmm-knn`, `replay-hmm-knn`, `monitor-hmm-knn`.
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_PROMPTS.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_RUNBOOK.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_INPUT_LOOKUP.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_MODEL_SPEC.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_REALIZATION_PLAN.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_SOURCE_LOG.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_EXECUTION_RISK_REVIEW.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/` - HMM/KNN handoff artifacts, if the PR should include the agent audit trail.

### Runtime-adjacent observe-only

These touch runtime-adjacent surfaces but do not change live execution behavior:

- `src/tradingbotsuite/main.py` - adds research CLI branches only; no change to existing `serve`, `manual`, or `smoke-live` behavior was shown in the reviewed diff.
- `src/tradingbotsuite/operator_console.py` - adds read-only HMM/KNN artifact summaries; no diff in operator command helpers or live control routes.
- `src/tradingbotsuite/web/templates/research.html` - adds observe-only HMM/KNN monitoring UI on the Research page; Control page is unchanged.

These may be included in the HMM/KNN PR, but reviewers should treat them as observe-only and keep them separate from live controls.

### Tests

Likely include:

- `tests/tradingbotsuite/test_hmm_knn.py` - targeted HMM/KNN suite.
- `tests/tradingbotsuite/test_operator_ui.py` - HMM/KNN artifact summary coverage.
- `tests/tradingbotsuite/test_research.py` - dataset and HMM/KNN integration coverage.

Review before including:

- `tests/conftest.py`
- `tests/fixtures/btc_15m_fixture.json`
- top-level `tests/test_*.py`

Those top-level untracked tests may be duplicate or repo-reorganization artifacts. Do not include them in an HMM/KNN PR unless they are intentionally part of the same test layout change.

### Live-boundary

Confirmed untouched by explicit empty diff:

- `src/tradingbotsuite/adapters/execution.py`
- `src/tradingbotsuite/core/engine.py`
- `src/tradingbotsuite/config.py`
- `src/tradingbotsuite/runtime.py`
- `src/tradingbotsuite/web/operator.py`
- `src/tradingbotsuite/web/templates/control.html`
- `src/tradingbotsuite/operator_commands.py`

Live-boundary confirmation:

- Live execution remains untouched.
- Position sizing remains untouched.
- Live accept/reject gates remain untouched.
- Hyperliquid adapter behavior remains untouched.
- Runtime bootstrap remains untouched.
- Control page remains untouched.
- Operator command helpers remain untouched.

### Unrelated existing docs/scripts

Exclude from an HMM/KNN commit/PR unless a separate PR intentionally preserves or migrates these files:

- `btc_eth_hybrid_framework_verified_blueprint.txt`
- root-level broad docs:
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
- top-level scripts:
  - `run_live_smoke.py`
  - `run_manual.py`
  - `run_server.py`
- entire nested legacy/untracked tree:
  - `tradingbot/`

These files look broad, legacy, duplicated, or outside the HMM/KNN research deliverable. Do not sweep them into a focused HMM/KNN PR without explicit scope approval.

## Suggested HMM/KNN PR Include Set

For a focused HMM/KNN PR, include:

- `pyproject.toml`
- `configs/v2_btc_hmm_multi_knn_research.json`
- `src/tradingbotsuite/main.py`
- `src/tradingbotsuite/operator_console.py`
- `src/tradingbotsuite/research/dataset.py`
- `src/tradingbotsuite/research/hmm_knn.py`
- `src/tradingbotsuite/research/hmm_knn_monitoring.py`
- `src/tradingbotsuite/web/templates/research.html`
- `tests/tradingbotsuite/test_hmm_knn.py`
- `tests/tradingbotsuite/test_operator_ui.py`
- `tests/tradingbotsuite/test_research.py`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_*.md`
- selected `docs/tradingbotsuite_runtime/agent_artifacts/*.md` if audit artifacts are required in the PR.

## Suggested Exclude Set

Exclude from the focused HMM/KNN PR unless separately approved:

- root-level broad docs under `docs/*.md` that are not `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_*.md`
- `btc_eth_hybrid_framework_verified_blueprint.txt`
- `run_live_smoke.py`
- `run_manual.py`
- `run_server.py`
- top-level duplicate `tests/test_*.py` and `tests/conftest.py` unless a test layout migration is intentional
- `tests/fixtures/btc_15m_fixture.json` unless required by included tests
- entire `tradingbot/` directory

## Decisions made

- Classified current live-boundary files as untouched because the explicit diff command returned no output.
- Classified changed runtime-adjacent files as research-only or observe-only.
- Separated broad untracked docs/scripts and nested legacy tree from focused HMM/KNN scope.

## Assumptions

- The focused PR target is the HMM/KNN research package, not a whole-repo preservation or legacy migration PR.
- Agent artifacts are required by the prompt pack for internal handoff; whether to include all of them in the public PR is a reviewer/supervisor decision.
- Root `docs/*.md` files are not automatically part of HMM/KNN scope unless explicitly referenced by the HMM/KNN runtime docs.

## Open issues or blockers

No open issues or blockers.

## Handoff notes for other agents

Before opening a PR, stage intentionally. Avoid `git add .` because the working tree contains a large untracked legacy tree, broad root docs, top-level scripts, and duplicate-looking tests that should not be swept into a focused HMM/KNN PR.
