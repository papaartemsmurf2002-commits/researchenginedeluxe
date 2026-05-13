# WPR101-01 Branch Completion Review And Orchestrator Plan

Status: closed
Owner: Codex Research Agent
Stage: R101 branch completion review and orchestrator plan

## Goal

Perform a broad branch review after R100, record material issues and weak
points, and curate the orchestrator ledger with a concrete path to bring the
research branch to completion without weakening research-only or live-boundary
rules.

## Allowed Paths

- `docs/KNOWN_ISSUES.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/stage_reports/**`
- `docs/work_packets/**`

## Scope

1. Review branch governance, stage reports, known issues, contracts, package
   boundaries, research-cycle/discovery surfaces, candidate-pack gates, and
   live/promotion guards.
2. Run focused static scans and validation commands appropriate for a
   documentation-only review packet.
3. Register discovered blocking or material follow-up issues in
   `docs/KNOWN_ISSUES.md`.
4. Write a stage report summarizing review evidence, branch weak points,
   undeveloped areas, and research recommendations.
5. Curate `docs/ORCHESTRATOR_STAGE_LEDGER.md` with the next completion stages
   and packet instructions.

## Non-Goals

- No source-code behavior changes.
- No generated research artifact mutation.
- No provider downloads, fixture regeneration, candidate batches, candidate
  pack writing, promotion authorization, live execution, live config mutation,
  order placement, runtime-mode changes, or sizing behavior changes.
- No profitability, performance, data-readiness, promotion-readiness, or
  live-readiness claims.

## Validation Plan

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
git diff --check
```

## Exit Evidence

Completed on 2026-05-13.

Implemented:

- Reviewed governance, contracts, current diff, high-risk packages, configs,
  fixture manifests, CLI/operator paths, live/promotion guards, and candidate
  gates without changing implementation files.
- Registered material follow-up issues in `docs/KNOWN_ISSUES.md`.
- Added the R101 review report at
  `docs/stage_reports/STAGE_R101_BRANCH_COMPLETION_REVIEW_ORCHESTRATOR_PLAN.md`.
- Curated `docs/ORCHESTRATOR_STAGE_LEDGER.md` with the completion roadmap and
  next-stage packet sequence.

Material issues recorded:

- `ISSUE-R101-001`: fixture source provider capability mismatch is not
  validated.
- `ISSUE-R101-002`: direct research CLI output-directory allowlist is
  incomplete.
- `ISSUE-R101-003`: candidate-ready empirical evidence is still blocked by
  durable multi-window data gaps.
- `ISSUE-R101-004`: import-boundary tests omit several live-adjacent research
  packages.
- `ISSUE-R101-005`: provider capabilities are not yet consumed by readiness
  and pack gates.
- `ISSUE-R101-006`: distribution name still points at the legacy package
  identity.

Validation passed:

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
