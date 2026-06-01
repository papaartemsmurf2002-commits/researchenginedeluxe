# Work Packet: WPR106-51 complete review hardening and publish

## Goal

Perform a broad repository review after the WPR106-48 through WPR106-50
hardening work, fix concrete bugs or inconsistencies found by code review and
validation, and publish the resulting branch to GitHub.

This packet is a hardening and publication packet. It does not attempt to
advance the stage, create candidate-ready claims, emit candidate packs, or
change live/paper execution behavior.

## Current Repo Facts

- Current implementation branch:
  `codex/wpr106-47-full-replay-exit-lab-controls`.
- The checkout already contains uncommitted WPR106-48, WPR106-49, and
  WPR106-50 source, test, and documentation changes.
- `.pytest_cache` files are dirty from local validation and are not source
  artifacts for this packet.
- `ISSUE-R104-001` remains the only open P1 issue in
  `docs/KNOWN_ISSUES.md`; no P0 issues are open.

## Allowed Edit Paths

This is a broad audit packet. Edits are allowed only when review or validation
finds a concrete issue:

- `docs/ACTIVE_INDEX.md`
- `docs/KNOWN_ISSUES.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/stage_reports/STAGE_R106_*.md`
- `docs/work_packets/WPR106-*.md`
- `docs/work_packets/WPR106-*-progress.jsonl`
- `src/tradingbot/**`
- `src/tradingbotsuite/**`
- `tests/**`
- `.github/workflows/**`
- `configs/**`
- `README.md`
- `pyproject.toml`

Generated empirical and performance artifacts under
`data/research/operator_runs/` remain local research evidence outputs and
should stay out of git unless a specific later packet approves them.

## Research Boundary

- Research outputs are not live signals.
- Artifacts must remain `research_only: true`, `observe_only: true`, and
  `promotion_ready: false`.
- This packet must not add live signals, paper signals, order placement, sizing
  behavior, runtime-mode changes, live configuration writes, promotion-ready
  claims, candidate-ready claims, or candidate-pack writes.
- Performance measurements are diagnostic unless a later scoped packet
  explicitly approves a speed claim with parity evidence.

## Review Plan

1. Inventory inherited dirty changes and avoid reverting unrelated user work.
2. Run independent subagent review tracks for live-boundary safety,
   research/data/backtest contracts, and documentation/stage consistency.
3. Run local static scans for risky TODOs, unsafe path handling, promotion/live
   boundary terms, and common Python failure patterns.
4. Run compile, contract, focused high-risk, and full-suite validation.
5. Fix concrete defects found by review or validation and add focused tests.
6. Update packet progress and stage-report documentation with validation
   evidence.
7. Stage only intended source/docs/test changes, commit, push, and open a draft
   PR.

## Acceptance Criteria

- Work packet and progress ledger are present.
- No open P0 issues are introduced.
- The open P1 count remains below the stage stop threshold unless a blocking
  issue is discovered and documented.
- Compile and contract validation pass.
- Full-suite or materially equivalent broad validation passes, or any
  environment limitation is recorded.
- `git diff --check` passes, ignoring expected line-ending notices.
- The pushed branch and draft PR contain only intended source/docs/test changes.

## Implementation Summary

- Re-ran a broad review after the inherited WPR106-48, WPR106-49, and
  WPR106-50 changes.
- Used subagents for independent live-boundary, research-contract, and
  docs/stage consistency review tracks. Two remote review tracks failed due
  transport/403 errors, so the same areas were covered by focused local scans,
  focused tests, and narrower retry-agent prompts. The completed docs/stage
  review found no stage-count mismatch, but confirmed that `.pytest_cache` and
  root-level handoff prompt files should remain unstaged.
- Tightened the fenced issue template in `docs/KNOWN_ISSUES.md` so naive
  issue-count tooling does not mistake the placeholder for a real open issue.
- Fixed retry-agent review findings:
  - Replay-scoped bridge requirements now verify referenced provenance files
    exist and match recorded SHA-256 values.
  - WPR106-48 negative-control artifacts now verify the control-row Parquet
    hash and row-level research boundary flags before a control family can be
    marked available.
  - Candidate-pack evidence filters now reject `runtime_mode_changed: true`
    in cycle evidence and required JSON artifacts.
  - Research-experiment benchmark effective pipeline specs now resolve nested
    source-relative dataset/config/provider input paths before copying specs
    into benchmark output directories.
  - The remaining Lorentzian persistence shift path uses the stable boolean
    shift helper and has a warning-as-error regression.
- Candidate packs remain blocked and no live/paper/order/sizing/runtime/
  promotion behavior was introduced.

## Validation Completed

```powershell
python -m compileall -q src\tradingbot src\tradingbotsuite tests
python -m pip check
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q --durations=20
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_replay_evidence_controls.py tests\research_discovery\test_candidate_pack_bridge.py tests\research_artifacts\test_candidate_pack.py tests\tradingbotsuite\test_experiment_runner.py tests\test_strategy_flow.py -q --durations=20
$env:PYTHONPATH='src'; python -m pytest -q --durations=30
git diff --check
```

Results:

- Compile: passed.
- `python -m pip check`: no broken requirements found.
- Contracts: 441 passed.
- Focused touched-path suite: 103 passed, 2 environment warnings.
- Full suite: 1544 passed, 1 skipped, 1 XGBoost environment warning in
  846.35 seconds.
- `git diff --check`: passed with line-ending warnings only.

## Staging Notes

- Do not stage `.pytest_cache/v/cache/lastfailed` or
  `.pytest_cache/v/cache/nodeids`; they are tracked local validation cache
  files but are not source artifacts for this packet.
- Do not stage `docs/NEXT_AGENT_HANDOFF_WPR106_47_LONG_RUN_PROMPT.md` or
  `docs/NEXT_AGENT_HANDOFF_WPR106_48_LONG_RUN_PROMPT.md` under WPR106-51.
  They are root-level handoff prompts outside this packet's allowed paths.
